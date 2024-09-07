import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

from flask import Flask, request

import json

from utils import compute_hash

app = Flask(__name__)

PROTOCOLS = {}

@app.route('/', methods=['GET'])
def main():
    return json.dumps({
        'status': 'success',
        'protocols' : list(PROTOCOLS.keys())
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

    PROTOCOLS[hashed_protocol] = protocol

    print('Added protocol:', hashed_protocol)

    return json.dumps({
        'status': 'success'
    })

# route for each protocol
@app.route('/protocol', methods=['GET'])
def get_protocol():
    protocol_id = request.args.get('id')
    if protocol_id not in PROTOCOLS:
        return json.dumps({
            'status': 'error',
            'message': 'Protocol not found.'
        })
    
    # No JSON
    return PROTOCOLS[protocol_id]