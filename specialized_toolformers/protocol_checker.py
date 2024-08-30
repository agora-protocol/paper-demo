# The protocol checker is a toolformer that checks if a protocol is suitable for a given task

import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import json
import os

from toolformers.openai_toolformer import OpenAIToolformer

CHECKER_TASK_PROMPT = 'You are ProtocolCheckerGPT. Your task is to look at the provided protocol and determine if it is expressive ' \
    'enough to fullfill the required task (of which you\'ll receive a JSON schema). A protocol is sufficiently expressive if you could write code that, given the input data, sends ' \
    'the query according to the protocol\'s specification and parses the reply. Think about it and at the end of the reply write "YES" if the' \
    'protocol is adequate or "NO"'

def check_protocol_for_task(protocol_document, task_schema):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), CHECKER_TASK_PROMPT, [])

    conversation = toolformer.new_conversation()

    message = 'The protocol is the following:\n\n' + protocol_document + '\n\nThe task is the following:\n\n' + json.dumps(task_schema)

    reply = conversation.chat(message, print_output=False)

    return 'yes' in reply.lower().strip()[-10:]

CHECKER_TOOL_PROMPT = 'You are ProtocolCheckerGPT. Your task is to look at the provided protocol and determine if you have access ' \
    'to the tools required to implement it. A protocol is sufficiently expressive if you could write code that, given a query formatted according to the protocol and the tools ' \
    'at your disposal, can parse the query according to the protocol\'s specification and send a reply. Think about it and at the end of the reply write "YES" if the' \
    'protocol is adequate or "NO"'

def check_protocol_for_tools(protocol_document, tools):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), CHECKER_TOOL_PROMPT, [])

    message = 'Protocol document:\n\n' + protocol_document + '\n\n' + 'Additional functions:\n\n'

    if len(tools) == 0:
        message += 'No additional functions provided'
    else:
        for tool in tools:
            message += tool.as_documented_python() + '\n\n'

    conversation = toolformer.new_conversation()

    reply = conversation.chat(message, print_output=True)

    print('Reply:', reply)
    print(reply.lower().strip()[-10:])
    print('Parsed decision:', 'yes' in reply.lower().strip()[-10:])

    return 'yes' in reply.lower().strip()[-10:]

