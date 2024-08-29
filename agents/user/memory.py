import json
import os
from pathlib import Path

from utils import save_routine

# Stores for each protocol
# - The id
# - Whether it is suitable for each task
# - The source of the protocol
# - Whether there is an implementation available
PROTOCOL_INFOS = {}

# Indexed by task type and target node
NUM_CONVERSATIONS = {}


def load_memory():
    storage_path = Path(os.environ.get('STORAGE_PATH')) / 'memory.json'
    if not Path(storage_path).exists():
        print('No memory found. Using default blank memory.')
        PROTOCOL_INFOS.clear()
        NUM_CONVERSATIONS.clear()
        return

    with open(storage_path, 'r') as f:
        data = json.load(f)

        PROTOCOL_INFOS.clear()
        PROTOCOL_INFOS.update(data['protocol_infos'])

        NUM_CONVERSATIONS.clear()
        NUM_CONVERSATIONS.update(data['num_conversations'])

        print('Loaded memory:', PROTOCOL_INFOS.keys())

def save_memory():
    storage_path = Path(os.environ.get('STORAGE_PATH')) / 'memory.json'
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(storage_path, 'w') as f:
        json.dump({
            'protocol_infos': PROTOCOL_INFOS,
            'num_conversations': NUM_CONVERSATIONS
        }, f)

def get_num_protocol_uses(protocol_id):
    if protocol_id not in PROTOCOL_INFOS:
        return 0
    
    return PROTOCOL_INFOS[protocol_id]['num_uses']

def increment_num_protocol_uses(protocol_id):
    PROTOCOL_INFOS[protocol_id]['num_uses'] += 1
    save_memory()


def get_num_conversations(task_type, target_node):
    if task_type not in NUM_CONVERSATIONS:
        return 0
    
    if target_node not in NUM_CONVERSATIONS[task_type]:
        return 0
    
    return NUM_CONVERSATIONS[task_type][target_node]

def increment_num_conversations(task_type, target_node):
    if task_type not in NUM_CONVERSATIONS:
        NUM_CONVERSATIONS[task_type] = {}
    
    if target_node not in NUM_CONVERSATIONS[task_type]:
        NUM_CONVERSATIONS[task_type][target_node] = 0
    
    NUM_CONVERSATIONS[task_type][target_node] += 1


def add_routine(protocol_id, implementation):
    PROTOCOL_INFOS[protocol_id]['has_implementation'] = True
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'routines'

    save_routine(base_folder, protocol_id, implementation)

    save_memory()
