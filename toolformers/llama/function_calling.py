import json
import os
import re
from pprint import pprint
from typing import List, Optional, Union

from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.tool import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from toolformers.base import Tool, StringParameter
from toolformers.llama.api_gateway import APIGateway

from toolformers.llama.utils import get_total_usage, usage_tracker


FUNCTION_CALLING_SYSTEM_PROMPT = """You have access to the following tools:

{tools}

You can call one or more tools by adding a <ToolCalls> section to your message. For example:
<ToolCalls>
```json
[{{
  "tool": <name of the selected tool>,
  "tool_input": <parameters for the selected tool, matching the tool's JSON schema>
}}]
```
</ToolCalls>

Note that you can select multiple tools at once by adding more objects to the list. Do not add \
multiple <ToolCalls> sections to the same message.
You will see the invocation of the tools in the response.


Think step by step
Do not call a tool if the input depends on another tool output that you do not have yet.
Do not try to answer until you get all the tools output, if you do not have an answer yet, you can continue calling tools until you do.
Your answer should be in the same language as the initial query.

"""  # noqa E501


conversational_response = Tool(
    name='ConversationalResponse',
    description='Respond conversationally only if no other tools should be called for a given query, or if you have a final answer. Response must be in the same language as the user query.',
    parameters=[StringParameter(name='response', description='Conversational response to the user. Must be in the same language as the user query.', required=True)],
    function=None
)


class FunctionCallingLlm:
    """
    function calling llm class
    """

    def __init__(
        self,
        tools: Optional[Union[Tool, List[Tool]]] = None,
        default_tool: Optional[Tool] = None,
        system_prompt: Optional[str] = None,
        prod_mode: bool = False,
        api: str = 'sncloud',
        coe: bool = False,
        do_sample: bool = False,
        max_tokens_to_generate: Optional[int] = None,
        temperature: float = 0.2,
        select_expert: Optional[str] = None,
    ) -> None:
        """
        Args:
            tools (Optional[Union[Tool, List[Tool]]]): The tools to use.
            default_tool (Optional[Tool]): The default tool to use.
                defaults to ConversationalResponse
            system_prompt (Optional[str]): The system prompt to use. defaults to FUNCTION_CALLING_SYSTEM_PROMPT
            prod_mode (bool): Whether to use production mode. Defaults to False.
            api (str): The api to use. Defaults to 'sncloud'.
            coe (bool): Whether to use coe. Defaults to False.
            do_sample (bool): Whether to do sample. Defaults to False.
            max_tokens_to_generate (Optional[int]): The max tokens to generate. If None, the model will attempt to use the maximum available tokens.
            temperature (float): The model temperature. Defaults to 0.2.
            select_expert (Optional[str]): The expert to use. Defaults to None.
        """
        self.prod_mode = prod_mode
        sambanova_api_key = os.environ.get('SAMBANOVA_API_KEY')
        self.api = api
        self.llm = APIGateway.load_llm(
            type=api,
            streaming=True,
            coe=coe,
            do_sample=do_sample,
            max_tokens_to_generate=max_tokens_to_generate,
            temperature=temperature,
            select_expert=select_expert,
            process_prompt=False,
            sambanova_api_key=sambanova_api_key,
        )

        if isinstance(tools, Tool):
            tools = [tools]
        self.tools = tools
        if system_prompt is None:
            system_prompt = ''
        else:
            system_prompt = system_prompt + '\n\n'
        self.system_prompt = system_prompt.replace('{','{{').replace('}', '}}') + FUNCTION_CALLING_SYSTEM_PROMPT
        if default_tool is None:
            default_tool = conversational_response

    def execute(self, invoked_tools: List[dict]) -> tuple[bool, List[str]]:
        """
        Given a list of tool executions the llm return as required
        execute them given the name with the mane in tools_map and the input arguments
        if there is only one tool call and it is default conversational one, the response is marked as final response

        Args:
            invoked_tools (List[dict]): The list of tool executions generated by the LLM.
        """
        if self.tools is not None:
            tools_map = {tool.name.lower(): tool for tool in self.tools}
        else:
            tools_map = {}
        tool_msg = "Tool '{name}'response: {response}"
        tools_msgs = []
        if len(invoked_tools) == 1 and invoked_tools[0]['tool'].lower() == 'conversationalresponse':
            final_answer = True
            return final_answer, [invoked_tools[0]['tool_input']['response']]
        for tool in invoked_tools:
            final_answer = False

            if tool['tool'].lower() == 'invocationerror':
                tools_msgs.append(f'Tool invocation error: {tool["tool_input"]}')
            elif tool['tool'].lower() != 'conversationalresponse':
                print(f"\n\n---\nTool {tool['tool'].lower()} invoked with input {tool['tool_input']}\n")
                
                if tool['tool'].lower() not in tools_map:
                    tools_msgs.append(f'Tool {tool["tool"]} not found')
                else:
                    response = tools_map[tool['tool'].lower()].call_tool_for_toolformer(**tool['tool_input'])
                    # print(f'Tool response: {str(response)}\n---\n\n')
                    tools_msgs.append(tool_msg.format(name=tool['tool'], response=str(response)))
        return final_answer, tools_msgs

    def json_finder(self, input_string: str) -> Optional[str]:
        """
        find json structures in an LLM string response, if bad formatted using LLM to correct it

        Args:
            input_string (str): The string to find the json structure in.
        """

        json_pattern = re.compile(r'<ToolCalls\>(.*)</ToolCalls\>', re.DOTALL + re.IGNORECASE)
        # Find the first JSON structure in the string
        json_match = json_pattern.search(input_string)
        if json_match:
            json_str = json_match.group(1)

            # Find the outermost list of JSON objects in the string. It is surrounded by square brackets
            json_match = re.search(r'\[.*\]', json_str, re.DOTALL)

            if json_match:
                json_str = json_match.group(0)
                try:
                    return json.loads(json_str)
                except Exception as e:
                    return [{'tool': 'InvocationError', 'tool_input' : str(e)}]
            else:
                return [{'tool': 'InvocationError', 'tool_input' : 'Could not find JSON object in the <ToolCalls> section'}]
        else:
            dummy_json_response = [{'tool': 'ConversationalResponse', 'tool_input': {'response': input_string}}]
            json_str = dummy_json_response
        return json_str

    def msgs_to_llama3_str(self, msgs: list) -> str:
        """
        convert a list of langchain messages with roles to expected LLmana 3 input

        Args:
            msgs (list): The list of langchain messages.
        """
        formatted_msgs = []
        for msg in msgs:
            if msg.type == 'system':
                sys_placeholder = (
                    '<|begin_of_text|><|start_header_id|>system<|end_header_id|>system<|end_header_id|> {msg}'
                )
                formatted_msgs.append(sys_placeholder.format(msg=msg.content))
            elif msg.type == 'human':
                human_placeholder = '<|eot_id|><|start_header_id|>user<|end_header_id|>\nUser: {msg} <|eot_id|><|start_header_id|>assistant<|end_header_id|>\nAssistant:'  # noqa E501
                formatted_msgs.append(human_placeholder.format(msg=msg.content))
            elif msg.type == 'ai':
                assistant_placeholder = '<|eot_id|><|start_header_id|>assistant<|end_header_id|>\nAssistant: {msg}'
                formatted_msgs.append(assistant_placeholder.format(msg=msg.content))
            elif msg.type == 'tool':
                tool_placeholder = '<|eot_id|><|start_header_id|>tools<|end_header_id|>\n{msg} <|eot_id|><|start_header_id|>assistant<|end_header_id|>\nAssistant:'  # noqa E501
                formatted_msgs.append(tool_placeholder.format(msg=msg.content))
            else:
                raise ValueError(f'Invalid message type: {msg.type}')
        return '\n'.join(formatted_msgs)

    def msgs_to_sncloud(self, msgs: list) -> list:
        """
        convert a list of langchain messages with roles to expected FastCoE input

        Args:
            msgs (list): The list of langchain messages.
        """
        formatted_msgs = []
        for msg in msgs:
            if msg.type == 'system':
                formatted_msgs.append({'role': 'system', 'content': msg.content})
            elif msg.type == 'human':
                formatted_msgs.append({'role': 'user', 'content': msg.content})
            elif msg.type == 'ai':
                formatted_msgs.append({'role': 'assistant', 'content': msg.content})
            elif msg.type == 'tool':
                formatted_msgs.append({'role': 'tools', 'content': msg.content})
            else:
                raise ValueError(f'Invalid message type: {msg.type}')
        return json.dumps(formatted_msgs)

    def function_call_llm(self, query: str, max_it: int = 5, debug: bool = False) -> str:
        """
        invocation method for function calling workflow

        Args:
            query (str): The query to execute.
            max_it (int, optional): The maximum number of iterations. Defaults to 5.
            debug (bool, optional): Whether to print debug information. Defaults to False.
        """
        function_calling_chat_template = ChatPromptTemplate.from_messages([('system', self.system_prompt)])
        tools_schemas = [tool.as_llama_schema() for tool in self.tools]

        history = function_calling_chat_template.format_prompt(tools=tools_schemas).to_messages()

        history.append(HumanMessage(query))
        tool_call_id = 0  # identification for each tool calling required to create ToolMessages
        with usage_tracker():

            for i in range(max_it):
                json_parsing_chain = RunnableLambda(self.json_finder)

                if self.api == 'sncloud':
                    prompt = self.msgs_to_sncloud(history)
                else:
                    prompt = self.msgs_to_llama3_str(history)
                # print(f'\n\n---\nCalling function calling LLM with prompt: \n{prompt}\n')
                
                llm_response = self.llm.invoke(prompt, stream_options={'include_usage': True})
                print('LLM response:', llm_response)

                # print(f'\nFunction calling LLM response: \n{llm_response}\n---\n')
                parsed_tools_llm_response = json_parsing_chain.invoke(llm_response)

                history.append(AIMessage(llm_response))
                final_answer, tools_msgs = self.execute(parsed_tools_llm_response)
                if final_answer:  # if response was marked as final response in execution
                    final_response = tools_msgs[0]
                    if debug:
                        print('\n\n---\nFinal function calling LLM history: \n')
                        pprint(f'{history}')
                    return final_response, get_total_usage()
                else:
                    history.append(ToolMessage('\n'.join(tools_msgs), tool_call_id=tool_call_id))
                    tool_call_id += 1


        raise Exception('Not a final response yet', history)