import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

from pathlib import Path
import os

if os.environ.get('STORAGE_PATH') is None:
    os.environ['STORAGE_PATH'] = str(Path().parent / 'storage' / 'server')

import requests as request_manager
from flask import Flask, request

from utils import compute_hash

from agents.common.core import Suitability
from utils import save_protocol_document, load_protocol_document
from specialized_toolformers.responder import reply_to_query
from specialized_toolformers.protocol_checker import check_protocol_for_tools

app = Flask(__name__)



KNOWN_PROTOCOLS = {}

def download_and_verify_protocol(protocol_hash, protocol_source):
    response = request_manager.get(protocol_source)
    # It's just a simple txt file
    if response.status_code == 200:
        protocol = response.text
        print('Protocol:', protocol)

        print('Found hash:', compute_hash(protocol))
        print('Target hash:', protocol_hash)
        # Check if the hash matches
        if compute_hash(protocol) == protocol_hash:
            print('Hashes match!')
            # Save the protocol in the known protocols
            KNOWN_PROTOCOLS[protocol_hash] = {
                'protocol': protocol,
                'source': protocol_source,
                'suitability': Suitability.UNKNOWN
            }
            # Store it in protocol_documents for future reference
            base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
            save_protocol_document(base_folder, protocol_hash, protocol)

            return True
    print('Failed to download protocol:', protocol_source)
    return False

def handle_query(protocol_hash, protocol_sources, query):
    if protocol_hash is None:
        return reply_to_query(query, None)

    if protocol_hash in KNOWN_PROTOCOLS:
        if KNOWN_PROTOCOLS[protocol_hash]['suitability'] == Suitability.UNKNOWN:
            # Determine if we can support this protocol
            base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
            protocol_document = load_protocol_document(base_folder, protocol_hash)
            if check_protocol_for_tools(protocol_document, query):
                KNOWN_PROTOCOLS[protocol_hash]['suitability'] = Suitability.ADEQUATE
            else:
                KNOWN_PROTOCOLS[protocol_hash]['suitability'] = Suitability.INADEQUATE

        if KNOWN_PROTOCOLS[protocol_hash]['suitability'] == Suitability.ADEQUATE:
            return reply_to_query(query, protocol_hash)
        else:
            return {
                'status': 'error',
                'message': 'Protocol not suitable.'
            }
    else:
        print('Protocol sources:', protocol_sources)
        for protocol_source in protocol_sources:
            if download_and_verify_protocol(protocol_hash, protocol_source):
                return handle_query(protocol_hash, [], query)
        return {
            'status': 'error',
            'message': 'No valid protocol source provided.'
        }

@app.route("/", methods=['POST'])
def main():
    data = request.get_json()

    protocol_hash = data.get('protocolHash', None)
    protocol_sources = data.get('protocolSources', [])

    return handle_query(protocol_hash, protocol_sources, data['body'])

@app.route("/wellknown", methods=['GET'])
def wellknown():
    return {
        'status': 'success',
        'protocols': { protocol_hash: [KNOWN_PROTOCOLS[protocol_hash]['source']] for protocol_hash in KNOWN_PROTOCOLS }
    }