# The responder is a special toolformer that replies to a service based on a protocol document.
# It receives the protocol document and writes the response that must be sent to the system.

import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import json
import os
from pathlib import Path

from toolformers.unified import make_default_toolformer

import requests as request_manager

from utils import load_protocol_document

# TODO: A tool to declare an error?


PROTOCOL_RESPONDER_PROMPT = 'You are ResponderGPT. You will receive a protocol document detailing how to respond to a query. '\
    'Use the provided functions to execute what is requested and provide the response according to the protocol\'s specification. ' \
    'Only reply with the response itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting.' \
    'If you do not have enough information to reply, or if you cannot execute the request, reply with "ERROR" (without quotes).'

def reply_with_protocol_document(query, protocol_document, tools, additional_info):
    print('===NL RESPONDER (WITH PROTOCOL)===')
    toolformer = make_default_toolformer(PROTOCOL_RESPONDER_PROMPT + additional_info, tools)

    conversation = toolformer.new_conversation(category='conversation')

    prompt = 'The protocol is the following:\n\n' + protocol_document + '\n\nThe query is the following:' + query

    reply = conversation.chat(prompt, print_output=True)

    print('======')

    if 'error' in reply.lower().strip()[-10:]:
        return json.dumps({
            'status': 'error',
        })

    return json.dumps({
        'status': 'success',
        'body': reply
    })

NL_RESPONDER_PROMPT = 'You are NaturalLanguageResponderGPT. You will receive a query from a user. ' \
    'Use the provided functions to execute what is requested and reply with a response (in natural language). ' \
    'If you do not have enough information to reply, if you cannot execute the request, or if the request is invalid, reply with "ERROR" (without quotes).' \
    'Important: the user does not have the capacity to respond to follow-up questions, so if you think you have enough information to reply/execute the actions, do so.'

def reply_to_nl_query(query, tools, additional_info):
    print('===NL RESPONDER (NO PROTOCOL)===')
    print(NL_RESPONDER_PROMPT + additional_info)
    toolformer = make_default_toolformer(NL_RESPONDER_PROMPT + additional_info, tools)

    conversation = toolformer.new_conversation(category='conversation')

    reply = conversation.chat(query, print_output=True)
    print('======')

    if 'error' in reply.lower().strip()[-10:]:
        return json.dumps({
            'status': 'error',
        })

    return json.dumps({
        'status': 'success',
        'body': reply
    })


def reply_to_query(query, protocol_id, tools, additional_info):
    print('Additional info:', additional_info)
    if protocol_id is None:
        return reply_to_nl_query(query, tools, additional_info)
    else:
        base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
        protocol_document = load_protocol_document(base_folder, protocol_id)
        return reply_with_protocol_document(query, protocol_document, tools, additional_info)