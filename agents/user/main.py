import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import json
import os
from pathlib import Path
import traceback

if os.environ.get('STORAGE_PATH') is None:
    os.environ['STORAGE_PATH'] = str(Path().parent / 'storage' / 'user')


from agents.user.memory import load_memory, increment_num_conversations, get_num_protocol_uses, increment_num_protocol_uses, PROTOCOL_INFOS, save_memory, add_routine


from specialized_toolformers.querier import send_query_with_protocol, send_query_without_protocol
from specialized_toolformers.programmer import write_routine_for_task

from toolformers.base import Tool, StringParameter

from agents.user.protocol_management import decide_protocol, has_implementation
from agents.user.config import get_task, load_config, TASK_SCHEMAS, NODE_URLS

from utils import load_protocol_document, execute_routine, send_raw_query, use_query_id
    
NUM_CONVERSATIONS_FOR_PROTOCOL = -1
NUM_CONVERSATIONS_FOR_ROUTINE = -1

from flask import Flask, request

app = Flask(__name__)

def call_using_implementation(task_type, task_schema, protocol_id, task_data, target_node):
    def send_to_server(query):
        print('Sending query:', query)
        response = send_raw_query(query, protocol_id, target_node, PROTOCOL_INFOS[protocol_id]['source'])

        if response.status_code == 200:
            parsed_response = json.loads(response.text)

            if parsed_response['status'] == 'success':
                return parsed_response['body']
        
        raise Exception('Error calling the server:', response.text)

    send_to_server_tool = Tool(
        'send_to_server',
        'Sends a query to the server and returns the response as described in the protocol document.', [
            StringParameter('query', 'The query to send to the server.', True)
        ],
        send_to_server
    )

    try:
        base_folder = Path(os.environ.get('STORAGE_PATH')) / 'routines' / task_type
        parsed_response = execute_routine(base_folder, protocol_id, task_data, [send_to_server_tool])

        return parsed_response
    except Exception as e:
        print(traceback.print_exception(type(e), e, e.__traceback__))
        print('Error executing routine:', e)
        print('Falling back to querier')
        response = send_query_with_protocol(task_schema, task_data, target_node, protocol_id, PROTOCOL_INFOS[protocol_id]['source'])
        return response

@app.route("/", methods=['POST'])
def main():
    if os.environ.get('AGENT_ID').endswith('_helper'):
        return json.dumps({
            'status': 'error',
            'message': 'This agent is a helper agent and cannot be used for direct communication.'
        })
    data = request.get_json()

    query_id = data['queryId']

    if query_id is None:
        print('No query ID provided.')
    else:
        print('Query ID:', query_id)

    with use_query_id(query_id):
        response = run_random_task()

    print('Response:', response, flush=True)
    save_memory()
    return response

def run_task(task_type, task_data, target_server):
    # Query the node to know its preferred protocols
    # If you already support a protocol, use it and call the corresponding routine

    # If you might accept one of the target's protocols but don't have an implementation:
    # - If the communication is sufficiently rare, use the querier with the protocol
    # - Otherwise, call the programmer to implement the protocol

    # If you haven't categorized the target's protocols yet, use the categorizer to classify them and go back

    # If you've classified all the target's protocols and none are suitable, check on the public protocol database and repeat

    # If you've checked all the public protocols and none are suitable:
    # - If the communication is sufficiently rare, use the querier without any protocol
    # - Otherwise, use the negotiator to reach an agreement with the target on a new protocol

    task_schema = TASK_SCHEMAS[task_type]
    target_node = NODE_URLS[target_server]

    protocol_id = decide_protocol(task_type, target_node, NUM_CONVERSATIONS_FOR_PROTOCOL)
    if protocol_id is None:
        source = None
    else:
        source = PROTOCOL_INFOS[protocol_id]['source']

    increment_num_conversations(task_type, target_node)

    if protocol_id is not None:
        print('Using protocol:', protocol_id)
        increment_num_protocol_uses(protocol_id)

        # Check if we have an implementation
        if has_implementation(task_type, protocol_id):
            return call_using_implementation(task_type, task_schema, protocol_id, task_data, target_node)
        # If we've talked enough times using a certain protocol, write an implementation
        elif get_num_protocol_uses(protocol_id) > NUM_CONVERSATIONS_FOR_ROUTINE:
            protocol_document = load_protocol_document(Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents', protocol_id)
            routine = write_routine_for_task(task_schema, protocol_document)

            add_routine(task_type, protocol_id, routine)
            return call_using_implementation(task_type, task_schema, protocol_id, task_data, target_node)
        else:
            # Use the querier with the protocol
            response = send_query_with_protocol(task_schema, task_data, target_node, protocol_id, source)
            return response
    else:
        # Use the querier without any protocol
        print('Using the querier without any protocol')
        response = send_query_without_protocol(task_schema, task_data, target_node)
        return response

def run_random_task():
    # Generate task info (with structured data) and pick a target node
    task_type, task_data, target_server = get_task()
    return run_task(task_type, task_data, target_server)

@app.route('/customRun', methods=['POST'])
def custom_run():
    data = request.get_json()
    task_type = data['type']
    task_data = data['data']
    target_server = data['targetServer']
    query_id = data['queryId']

    if query_id is None:
        print('No query ID provided.')
    else:
        print('Query ID:', query_id)

    print('Custom run:', task_type, task_data, target_server)

    with use_query_id(query_id):
        return run_task(task_type, task_data, target_server)

def init():
    load_config(os.environ.get('AGENT_ID'))
    load_memory()
    print('Agent initialized')

init()