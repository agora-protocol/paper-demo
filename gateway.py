import os

from flask import Flask, request
import requests as request_manager

app = Flask(__name__)


MODEL_HANDLER_URL = 'http://localhost:' + os.environ.get('MODEL_HANDLER_PORT', '5001')
ROUTINE_MANAGER_URL = 'http://localhost:' + os.environ.get('ROUTINE_MANAGER_PORT', '5002')


@app.route("/", methods=['POST'])
def main():
    data = request.get_json()

    protocol_hash = data.get('protocolHash', None)

    if protocol_hash is None:
        return request_manager.post(MODEL_HANDLER_URL, json=data).json()
    else:
        known_hashes = request_manager.get(ROUTINE_MANAGER_URL + '/routines').json()['body']

        if protocol_hash in known_hashes:
            return request_manager.post(ROUTINE_MANAGER_URL + '/call', json=data).json()
        else:
            print('Unknown hash, forwarding to the model handler.')
            return request_manager.post(MODEL_HANDLER_URL, json=data).json()
