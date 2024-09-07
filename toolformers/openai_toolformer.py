from openai import AssistantEventHandler, OpenAI

import datetime
import json
import os
from typing_extensions import override

from toolformers.base import Toolformer, Conversation

from databases.mongo import insert_one

class EventHandler(AssistantEventHandler):
    def __init__(self, conversation, print_output=True):
        super().__init__()
        self.conversation = conversation
        self.print_output = print_output

    @override
    def on_event(self, event):
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id  # Retrieve the run ID from the event data
            self.handle_requires_action(event.data, run_id)
        elif event.event == 'thread.message.delta':
            delta = ''.join([delta.text.value for delta in event.data.delta.content])
            if self.print_output:
                print(delta, end="", flush=True)
            self.conversation.current_message += delta
        elif event.event == 'thread.message.completed' and self.print_output:
            print()
        
        if event.event == 'thread.run.completed':
            dump = event.model_dump()['data']
            if dump.get('usage', None) is not None:
                assert self.conversation.current_usage is None
                self.conversation.current_usage = dump['usage']
 
    def handle_requires_action(self, data, run_id):
        tool_outputs = []
        
        for tool_call in data.required_action.submit_tool_outputs.tool_calls:
            # Find the matching tool for the tool_call
            tool = next((tool for tool in self.conversation.toolformer.tools if tool.name == tool_call.function.name), None)

            if tool is not None:
                # Call the tool function with the tool_call data
                arguments = json.loads(tool_call.function.arguments)
                output = tool.function(**arguments)
                tool_outputs.append({"tool_call_id": tool_call.id, "output": output})

        # Submit all tool_outputs at the same time
        self.submit_tool_outputs(tool_outputs, run_id)
 
    def submit_tool_outputs(self, tool_outputs, run_id):
        # Use the submit_tool_outputs_stream helper
        with self.conversation.toolformer.client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(self.conversation, print_output=self.print_output),
        ) as stream:
            for text in stream.text_deltas:
                #print(text, end="", flush=True)
                #self.conversation.current_message += text
                pass
            #print()
 


class OpenAIToolformer(Toolformer):
    def __init__(self, api_key, system_instructions : str, tools, model="gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.tools = tools
        self.model = model

        self.assistant = self.client.beta.assistants.create(
            instructions=system_instructions,
            model=model,
            tools=[tool.as_openai_info() for tool in tools]
        )

    def new_conversation(self, starting_messages=None, category=None):
        if starting_messages is None:
            starting_messages = []
        thread = self.client.beta.threads.create(messages=starting_messages)

        return OpenAIConversation(self, thread.id, self.assistant.id, category=category)

def send_usage_to_db(usage, time_start, time_end, agent, category):
    usage = {
        'timeStart': {
            '$date': time_start.isoformat()
        },
        'timeEnd': {
            '$date': time_end.isoformat()
        },
        'prompt_tokens': usage['prompt_tokens'],
        'completion_tokens': usage['completion_tokens'],
        'agent': agent,
        'category': category
    }
    insert_one('usageLogs', 'main', usage)

class OpenAIConversation(Conversation):
    def __init__(self, toolformer, thread_id, assistant_id, category=None):
        self.toolformer = toolformer
        self.thread_id = thread_id
        self.assistant_id = assistant_id
        self.current_message = ''
        self.current_usage = None
        self.category = category

    def chat(self, message, role='user', print_output=True):
        message = self.toolformer.client.beta.threads.messages.create(
            thread_id=self.thread_id,
            role=role,
            content=message
        )

        self.current_message = ''
        self.current_usage = None

        agent_id = os.environ.get('AGENT_ID', None)

        start_time = datetime.datetime.now()

        with self.toolformer.client.beta.threads.runs.stream(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
            event_handler=EventHandler(self, print_output=print_output)
            ) as stream:
                stream.until_done()

        end_time = datetime.datetime.now()

        reply = self.current_message
        self.current_message = ''

        if self.current_usage is not None:
            send_usage_to_db(self.current_usage, start_time, end_time, agent_id, self.category)

        self.current_usage = None

        return reply
