# The querier is a special toolformer that queries a service based on a protocol document.
# It receives the protocol document and writes the query that must be performed to the system.

import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import json
import os
from pathlib import Path

from toolformers.base import Tool, StringParameter
from toolformers.unified import make_default_toolformer

import requests as request_manager

from utils import load_protocol_document, send_raw_query

PROTOCOL_QUERIER_PROMPT = 'You are QuerierGPT. You will receive a protocol document detailing how to query a service. Reply with a structured query which can be sent to the service.' \
    'Only reply with the query itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting.'

def construct_query_description(protocol_document, task_schema, task_data):
    query_description = ''
    if protocol_document is not None:
        query_description += 'Protocol document:\n\n'
        query_description += protocol_document + '\n\n'
    query_description += 'JSON schema of the task:\n\n'
    query_description += 'Input (i.e. what the machine will provide you):\n'
    query_description += json.dumps(task_schema['input'], indent=4) + '\n\n'
    query_description += 'Output (i.e. what you have to provide to the machine):\n'
    query_description += json.dumps(task_schema['output'], indent=4) + '\n\n'
    query_description += 'JSON data of the task:\n\n'
    query_description += json.dumps(task_data, indent=4) + '\n\n'

    return query_description

NL_QUERIER_PROMPT = 'You are NaturalLanguageQuerierGPT. You act as an intermediary between a machine (who has a very specific input and output schema) and an agent (who uses natural language).' \
    'You will receive a task description (including a schema of the input and output) that the machine uses and the corresponding data. Call the \"sendQuery\" tool with a natural language message where you ask to perform the task according to the data.' \
    'Do not worry about managing communication, everything is already set up for you. Just focus on asking the right question.' \
    'The sendQuery tool will return the reply of the service.\n' \
    'Once you receive the reply, call the \"deliverStructuredOutput\" tool with a JSON-formatted message according to the machine\'s output schema.\n' \
    'Note: you cannot call sendQuery multiple times, so make sure to ask the right question the first time. Similarly, you cannot call deliverStructuredOutput multiple times, so make sure to deliver the right output the first time.'

def parse_and_handle_query(query, target_node, protocol_id, source):
    response = send_raw_query(query, protocol_id, target_node, source)
    if response.status_code == 200:
        parsed_response = json.loads(response.text)

        if parsed_response['status'] == 'success':
            return parsed_response['body']

    return 'Error calling the tool: ' + response.text

def handle_conversation(prompt, message, target_node, protocol_id, source):
    has_sent_query = False
    
    def send_query_internal(query):
        print('Sending query:', query)
        nonlocal has_sent_query
        if has_sent_query:
            return 'You have already sent a query. You cannot send another one.'
        has_sent_query = True
        return parse_and_handle_query(query, target_node, protocol_id, source)

    send_query_tool = Tool('sendQuery', 'Send a query to the other service based on a protocol document.', [
        StringParameter('query', 'The query to send to the service', True)
    ], send_query_internal)

    found_output = None

    def register_output(**kwargs):
        print('Registering output:', kwargs)

        nonlocal found_output

        if 'output' in kwargs:
            output = kwargs['output']
        else:
            # The tool was called incorrectly. Treat the kwargs as the field of the output
            output = json.dumps(kwargs)

        if found_output is not None:
            return 'You have already registered an output. You cannot register another one.'

        found_output = output
        return 'Done'

    register_output_tool = Tool('deliverStructuredOutput', 'Deliver the structured output to the machine.', [
        StringParameter('output', 'The structured output to deliver to the machine, as a JSON string formatted according to the output schema', True)
    ], register_output)

    toolformer = make_default_toolformer(prompt, [send_query_tool, register_output_tool])

    conversation = toolformer.new_conversation(category='conversation')

    while True:
        conversation.chat(message, print_output=True)

        if found_output is not None:
            break

        # If we haven't sent a query yet, we can't proceed
        if not has_sent_query:
            message = 'You must send a query before delivering the structured output.'
        elif found_output is None:
            message = 'You must deliver the structured output.'
        # TODO: Anti-infinite loop mechanism

    return found_output

def send_query_with_protocol(task_schema, task_data, target_node, protocol_id, source):
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
    protocol_document = load_protocol_document(base_folder, protocol_id)
    query_description = construct_query_description(protocol_document, task_schema, task_data)

    return handle_conversation(PROTOCOL_QUERIER_PROMPT, query_description, target_node, protocol_id, source)

def send_query_without_protocol(task_schema, task_data, target_node):
    query_description = construct_query_description(None, task_schema, task_data)

    return handle_conversation(NL_QUERIER_PROMPT, query_description, target_node, None, None)
