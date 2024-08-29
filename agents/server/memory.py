import json
import os
from pathlib import Path

from agents.common.core import Suitability
from utils import save_protocol_document, save_routine

PROTOCOL_INFOS = {}

def load_memory():
    storage_path = Path(os.environ.get('STORAGE_PATH')) / 'memory.json'
    if not Path(storage_path).exists():
        print('No memory found. Using default blank memory.')
        PROTOCOL_INFOS.clear()
        return

    with open(storage_path, 'r') as f:
        data = json.load(f)

        PROTOCOL_INFOS.clear()
        PROTOCOL_INFOS.update(data['protocol_infos'])

        print('Loaded memory:', PROTOCOL_INFOS.keys())

def save_memory():
    storage_path = Path(os.environ.get('STORAGE_PATH')) / 'memory.json'
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(storage_path, 'w') as f:
        json.dump({
            'protocol_infos': PROTOCOL_INFOS
        }, f)

def register_new_protocol(protocol_hash, protocol_source, protocol_document):
    PROTOCOL_INFOS[protocol_hash] = {
        'source': protocol_source,
        'suitability': Suitability.UNKNOWN,
        'has_implementation': False,
        'num_conversations': 0
    }
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
    save_protocol_document(base_folder, protocol_hash, protocol_document)
    save_memory()

def has_implementation(protocol_hash):
    if protocol_hash not in PROTOCOL_INFOS:
        return False
    
    return PROTOCOL_INFOS[protocol_hash]['has_implementation']

def get_num_conversations(protocol_hash):
    if protocol_hash not in PROTOCOL_INFOS:
        return 0
    
    return PROTOCOL_INFOS[protocol_hash]['num_conversations']

def increment_num_conversations(protocol_hash):
    PROTOCOL_INFOS[protocol_hash]['num_conversations'] += 1
    save_memory()

def add_routine(protocol_id, implementation):
    PROTOCOL_INFOS[protocol_id]['has_implementation'] = True
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'routines'

    save_routine(base_folder, protocol_id, implementation)

    save_memory()
