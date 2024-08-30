import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import os
from pathlib import Path
import random


if os.environ.get('STORAGE_PATH') is None:
    os.environ['STORAGE_PATH'] = str(Path().parent / 'storage' / 'user')


from agents.user.memory import load_memory, increment_num_conversations, get_num_protocol_uses, increment_num_protocol_uses, PROTOCOL_INFOS, save_memory, add_routine


from specialized_toolformers.querier import send_query_with_protocol, send_query_without_protocol
from specialized_toolformers.programmer import write_routine_for_task

from agents.user.protocol_management import decide_protocol, has_implementation
from agents.user.tasks import TASK_SCHEMAS, get_task

from utils import load_protocol_document, execute_routine, send_raw_query
    
NUM_CONVERSATIONS_FOR_PROTOCOL = -1
NUM_CONVERSATIONS_FOR_ROUTINE = -1
TARGET_NODES = ['http://localhost:5003']

load_memory()

def get_target_node():
    return random.choice(TARGET_NODES)

def call_using_implementation(protocol_id, task_data, target_node):
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'routines'
    formatted_query = execute_routine(base_folder, protocol_id, task_data, [])
    print('Sending query:', formatted_query)
    response = send_raw_query(formatted_query, protocol_id, target_node, PROTOCOL_INFOS[protocol_id]['source'])

    return response.text

def main():
    # Generate task info (with structured data) and pick a target node
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

    

    task_type, task_data = get_task()
    target_node = get_target_node()

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
        if has_implementation(protocol_id):
            return call_using_implementation(protocol_id, task_data, target_node)
        # If we've talked enough times using a certain protocol, write an implementation
        elif get_num_protocol_uses(protocol_id) > NUM_CONVERSATIONS_FOR_ROUTINE:
            protocol_document = load_protocol_document(Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents', protocol_id)
            routine = write_routine_for_task(TASK_SCHEMAS[task_type], protocol_document)

            add_routine(protocol_id, routine)
            return call_using_implementation(protocol_id, task_data, target_node)
        else:
            # Use the querier with the protocol
            response = send_query_with_protocol(TASK_SCHEMAS[task_type], task_data, target_node, protocol_id, source)
            return response.text
    else:
        # Use the querier without any protocol
        print('Using the querier without any protocol')
        response = send_query_without_protocol(TASK_SCHEMAS[task_type], task_data, target_node)
        return response.text
    
    # TODO: Should I save the memory here?
    save_memory()

print(main())