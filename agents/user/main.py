import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import os
from pathlib import Path
import random
import requests as request_manager
import urllib


if os.environ.get('STORAGE_PATH') is None:
    os.environ['STORAGE_PATH'] = str(Path().parent / 'storage' / 'user')



from agents.user.memory import load_memory, get_num_conversations, increment_num_conversations, PROTOCOL_INFOS, save_memory

from specialized_toolformers.querier import send_query_with_protocol, send_query_without_protocol

from agents.user.protocol_management import decide_protocol, has_implementation
from agents.user.tasks import TASK_SCHEMAS, get_task
    
TARGET_NODES = ['http://localhost:5003']

load_memory()

def get_target_node():
    return random.choice(TARGET_NODES)




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

    protocol_id = decide_protocol(task_type, target_node)
    if protocol_id is None:
        source = None
    else:
        source = PROTOCOL_INFOS[protocol_id]['source']

    increment_num_conversations(task_type, target_node)

    if protocol_id is not None:
        print('Using protocol:', protocol_id)
        # Check if we have an implementation

        if has_implementation(protocol_id):
            # TODO: Call the routine
            pass
        # If we've talked enough times using a certain protocol, write an implementation
        elif get_num_conversations(task_type, target_node) > 100:
            # TODO: Call the programmer
            pass
        else:
            # Use the querier with the protocol
            response = send_query_with_protocol(TASK_SCHEMAS[task_type], task_data, target_node, protocol_id, source)
            print(response.text)
    else:
        # Use the querier without any protocol
        print('Using the querier without any protocol')
        response = send_query_without_protocol(TASK_SCHEMAS[task_type], task_data, target_node)
        print(response.text)
    
    save_memory()

main()