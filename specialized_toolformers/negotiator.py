# The negotiator negotiates a protocol based on the task schema and data (for the user) and the tools available (for the server).

import json
import os
import uuid

import requests as request_manager

from toolformers.base import Tool, StringParameter
from toolformers.openai_toolformer import OpenAIToolformer

from utils import send_raw_query


NEGOTIATION_RULES = '''
Here are some rules (that should also be explained to the other GPT):
- You can assume that the protocol has a sender and a receiver. Do not worry about how the messages will be delivered, focus only on the content of the messages.
- Keep the protocol short and simple. It should be easy to understand and implement.
- The protocol must specify the exact format of what is sent and received. Do not leave it open to interpretation.
- The implementation will be written by a programmer that does not have access to the negotiation process, so make sure the protocol is clear and unambiguous.
- The implementation will receive a string and return a string, so structure your protocol accordingly.
- The other party might have a different internal data schema, so make sure that the protocol is flexible enough to accommodate that.
And remember: keep the protocol as simple and unequivocal as necessary. The programmer that will implement the protocol can code, but they are not a mind reader.
'''

TASK_NEGOTIATOR_PROMPT = f'''
You are ProtocolNegotiatorGPT. Your task is to negotiate a protocol that can be used to query a service.
You will receive a JSON schema of the task that the service must perform. Negotiate with the service to determine a protocol that can be used to query it.
To do so, you will chat with another GPT (role: user) that will negotiate on behalf of the service.
{NEGOTIATION_RULES}
Once you are ready to save the protocol, call the tool "registerProtocol" with the protocol as argument.
'''

TOOLS_NEGOTIATOR_PROMPT = f'''
You are ProtocolNegotiatorGPT. You are negotiating a protocol on behalf of a web service that can perform a task.
The other party is a GPT that is negotiating on behalf of the user. Your goal is to negotiate a protocol that is simple and clear, \
but also expressive enough to allow the service to perform the task. A protocol is sufficiently expressive if you could write code \
that, given the query formatted according to the protocol and the tools at the service's disposal, can parse the query according to \
the protocol's specification, perform the task (if any) and send a reply.
{NEGOTIATION_RULES}
You will receive a list of tools that are available to the programmer that will implement the protocol.
'''

def chat(message, conversation_id, target_node):
    data = {
        'body': message,
    }
    if conversation_id is not None:
        data['conversationId'] = conversation_id

    raw_reply = send_raw_query(json.dumps(data), 'negotiation', target_node, None).json()

    print('Raw reply:', raw_reply)

    wrapped_reply = json.loads(raw_reply['body'])

    return wrapped_reply['body'], wrapped_reply['conversationId']

def negotiate_protocol_for_task(task_schema, target_node):
    found_protocol = None

    def register_protocol(protocol):
        nonlocal found_protocol
        found_protocol = protocol
        return 'done'

    registerTool = Tool(
        'registerProtocol', 'Register a protocol document. Returns "done" if done.', [
        StringParameter('protocol', 'The protocol document to register', True
                    )], register_protocol)

    prompt = TASK_NEGOTIATOR_PROMPT + '\nThe JSON schema of the task is the following:\n\n' + json.dumps(task_schema, indent=4)

    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), prompt, [registerTool])

    conversation = toolformer.new_conversation()

    other_message = 'Hello! How may I help you?'
    conversation_id = None

    while found_protocol is None:
        print('===NegotiatorGPT===')
        message = conversation.chat(other_message, print_output=True)

        other_message, conversation_id = chat(message, conversation_id, target_node)
        print()
        print('===Other GPT===')
        print(other_message)
        print()

    return found_protocol


# Poor man's state management
ACTIVE_CONVERSATIONS = {}

def create_negotiation_conversation(tools):
    prompt = TOOLS_NEGOTIATOR_PROMPT
    prompt += '\n\nThe tools available are:\n\n'

    if len(tools) == 0:
        prompt += 'No additional tools provided'
    else:
        for tool in tools:
            prompt += tool.as_documented_python() + '\n\n'

    print('Prompt:', prompt)

    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), prompt, tools)

    return toolformer.new_conversation()

def handle_negotiation_for_tools(message, conversation_id, tools):
    if conversation_id is None:
        # Generate a new conversation ID
        conversation_id = str(uuid.uuid4())
    
    if conversation_id not in ACTIVE_CONVERSATIONS:
        ACTIVE_CONVERSATIONS[conversation_id] = create_negotiation_conversation(tools)
    
    conversation = ACTIVE_CONVERSATIONS[conversation_id]

    print('Message:', message)

    reply = conversation.chat(message, print_output=True)

    return reply, conversation_id