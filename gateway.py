import os

from flask import Flask, request
import requests as request_manager

from programmer import create_and_save_routine

app = Flask(__name__)


MODEL_HANDLER_URL = 'http://localhost:' + os.environ.get('MODEL_HANDLER_PORT', '5001')
ROUTINE_MANAGER_URL = 'http://localhost:' + os.environ.get('ROUTINE_MANAGER_PORT', '5002')

HASH_COUNTER = {}
TRIGGER_NUM_CALLS = 2

@app.route("/", methods=['POST'])
def main():
    data = request.get_json()

    protocol_hash = data.get('protocolHash', None)

    if protocol_hash is None:
        print('No protocol hash, forwarding to the model handler.')
        return request_manager.post(MODEL_HANDLER_URL, json=data).json()
    else:

        known_hashes = request_manager.get(ROUTINE_MANAGER_URL + '/routines').json()['body']

        if protocol_hash in known_hashes:
            print(f'Received known hash {protocol_hash}, forwarding to the routine manager.')
            return request_manager.post(ROUTINE_MANAGER_URL + '/call', json=data).json()
        else:
            print(f'Unknown hash {protocol_hash}, forwarding to the model handler.')
            if protocol_hash != 'chat': # Do not count regular stateful chats
                HASH_COUNTER[protocol_hash] = HASH_COUNTER.get(protocol_hash, 0) + 1

            if HASH_COUNTER[protocol_hash] >= TRIGGER_NUM_CALLS:
                print('Reached query count for hash, writing a routine.')
                create_and_save_routine(protocol_hash)

            return request_manager.post(MODEL_HANDLER_URL, json=data).json()
