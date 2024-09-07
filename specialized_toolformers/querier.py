# The querier is a special toolformer that queries a service based on a protocol document.
# It receives the protocol document and writes the query that must be performed to the system.

import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import json
import os
from pathlib import Path

from toolformers.openai_toolformer import OpenAIToolformer

import requests as request_manager

from utils import load_protocol_document, send_raw_query

PROTOCOL_QUERIER_PROMPT = 'You are QuerierGPT. You will receive a protocol document detailing how to query a service. Reply with a structured query which can be sent to the service.' \
    'Only reply with the query itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting.'

def construct_query(protocol_document, task_schema, task_data):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), PROTOCOL_QUERIER_PROMPT, [])

    conversation = toolformer.new_conversation()

    query_description = 'Protocol document:\n\n'
    query_description += protocol_document + '\n\n'
    query_description += 'JSON schema of the task:\n\n'
    query_description += json.dumps(task_schema, indent=4) + '\n\n'
    query_description += 'JSON data of the task:\n\n'
    query_description += json.dumps(task_data, indent=4) + '\n\n'

    reply = conversation.chat(query_description, print_output=False)

    return reply

NL_QUERIER_PROMPT = 'You are NaturalLanguageQuerierGPT. You will receive a task description and data. Reply with a natural language message where you ask to perform the task according to the data.' \
    'Note: The person sending the query won\'t have the possibility to ask follow-up questions, so make sure to ask exactly what is provided. Do not ask anything more than is provided in the task.'

def construct_nl_query(task_schema, task_data):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), NL_QUERIER_PROMPT, [])

    conversation = toolformer.new_conversation()

    return conversation.chat('Task schema:\n' + json.dumps(task_schema) + '\n\nTask data:' + json.dumps(task_data), print_output=False)

def send_query_with_protocol(task_schema, task_data, target_node, protocol_id, source):
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
    protocol_document = load_protocol_document(base_folder, protocol_id)

    query = construct_query(protocol_document, task_schema, task_data)
    return send_raw_query(query, protocol_id, target_node, source)

def send_query_without_protocol(task_schema, task_data, target_node):
    query = construct_nl_query(task_schema, task_data)
    print('Query:', query)
    return send_raw_query(query, None, target_node, None)

def send_query(task_schema, task_data, target_node, protocol_id, source):
    if protocol_id is None:
        return send_query_without_protocol(task_schema, task_data, target_node)
    else:
        return send_query_with_protocol(task_schema, task_data, target_node, protocol_id, source)