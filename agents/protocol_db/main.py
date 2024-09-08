import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import os
from pathlib import Path

if os.environ.get('STORAGE_PATH') is None:
    os.environ['STORAGE_PATH'] = str(Path().parent / 'storage' / 'protocol_db')

from flask import Flask, request

import json

from utils import compute_hash

app = Flask(__name__)

PROTOCOLS = {}

@app.route('/', methods=['GET'])
def main():
    return json.dumps({
        'status': 'success',
        'protocols' : [
            {
                'id': protocol_id,
                'name': protocol_data['name'],
                'description': protocol_data['description'],
            }
            for protocol_id, protocol_data in PROTOCOLS.items()
        ]
    })

@app.route('/', methods=['POST'])
def add_protocol():
    data = request.get_json()

    if 'protocol' not in data:
        return json.dumps({
            'status': 'error',
            'message': 'No protocol provided.'
        })

    protocol = data['protocol']
    hashed_protocol = compute_hash(protocol)

    PROTOCOLS[hashed_protocol] = data

    print('Added protocol:', hashed_protocol)
    save_memory()

    return json.dumps({
        'status': 'success'
    })

# route for each protocol
@app.route('/protocol', methods=['GET'])
def get_protocol():
    protocol_id = request.args.get('id')

    print('Received request for protocol:', protocol_id)
    print('Current keys:', PROTOCOLS.keys())
    print('Do I have the protocol?', protocol_id in PROTOCOLS)
    if protocol_id not in PROTOCOLS:
        return json.dumps({
            'status': 'error',
            'message': 'Protocol not found.'
        })
    
    # No JSON
    return PROTOCOLS[protocol_id]['protocol']

@app.route('/metadata', methods=['GET'])
def get_metadata():
    protocol_id = request.args.get('id')

    print('Received request for metadata:', protocol_id)
    print('Current keys:', PROTOCOLS.keys())
    print('Do I have the protocol?', protocol_id in PROTOCOLS)
    if protocol_id not in PROTOCOLS:
        return json.dumps({
            'status': 'error',
            'message': 'Protocol not found.'
        })
    
    return json.dumps({
        'status': 'success',
        'metadata': {
            'name': PROTOCOLS[protocol_id]['name'],
            'description': PROTOCOLS[protocol_id]['description']
        }
    })

def load_memory():
    PROTOCOLS.clear()

    storage_path = Path(os.environ.get('STORAGE_PATH'))

    if not storage_path.exists():
        print('No storage path found, using empty memory')
        return
    
    memory_file = storage_path / 'memory.json'

    with open(memory_file, 'r') as f:
        memory = json.load(f)
    for protocol_id, protocol_data in memory.items():
        PROTOCOLS[protocol_id] = protocol_data

    print('Loaded memory:', PROTOCOLS)

def save_memory():
    storage_path = Path(os.environ.get('STORAGE_PATH'))

    if not storage_path.exists():
        storage_path.mkdir(parents=True)

    memory_file = storage_path / 'memory.json'

    with open(memory_file, 'w') as f:
        json.dump(PROTOCOLS, f)

def init():
    load_memory()


init()