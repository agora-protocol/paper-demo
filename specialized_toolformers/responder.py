# The responder is a special toolformer that replies to a service based on a protocol document.
# It receives the protocol document and writes the response that must be sent to the system.

import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import os
from pathlib import Path

from toolformers.openai_toolformer import OpenAIToolformer

import requests as request_manager

from utils import load_protocol_document

# TODO: A tool to declare an error?


PROTOCOL_RESPONDER_PROMPT = 'You are ResponderGPT. You will receive a protocol document detailing how to respond to a query. '\
    'Use the provided functions to execute what is requested and provide the response according to the protocol\'s specification. ' \
    'Only reply with the response itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting.' \
    'If you do not have enough information to reply, or if you cannot execute the request, reply with "ERROR" (without quotes).'

def reply_with_protocol_document(query, protocol_document):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), PROTOCOL_RESPONDER_PROMPT, [])

    conversation = toolformer.new_conversation()

    reply = conversation.chat('The protocol is the following:\n\n' + protocol_document + '\n\nThe query is the following:' + query , print_output=False)

    return reply

NL_RESPONDER_PROMPT = 'You are NaturalLanguageResponderGPT. You will receive a query from a user. ' \
    'Use the provided functions to execute what is requested and reply with a response (in natural language). ' \
    'If you do not have enough information to reply, if you cannot execute the request, or if the request is invalid, reply with "ERROR" (without quotes).'

def reply_to_nl_query(query):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), NL_RESPONDER_PROMPT, [])

    conversation = toolformer.new_conversation()

    return conversation.chat(query, print_output=False)


def reply_to_query(query, protocol_id):
    if protocol_id is None:
        return reply_to_nl_query(query)
    else:
        base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
        protocol_document = load_protocol_document(base_folder, protocol_id)
        return reply_with_protocol_document(query, protocol_document)