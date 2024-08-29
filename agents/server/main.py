import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

from pathlib import Path
import os

if os.environ.get('STORAGE_PATH') is None:
    os.environ['STORAGE_PATH'] = str(Path().parent / 'storage' / 'server')

from flask import Flask, request


from agents.common.core import Suitability
from agents.server.memory import PROTOCOL_INFOS, register_new_protocol, has_implementation, get_num_conversations, increment_num_conversations, has_implementation, add_routine
from utils import load_protocol_document, execute_routine, download_and_verify_protocol
from specialized_toolformers.responder import reply_to_query
from specialized_toolformers.protocol_checker import check_protocol_for_tools
from specialized_toolformers.programmer import write_routine_for_tools

app = Flask(__name__)

NUM_CONVERSATIONS_FOR_ROUTINE = -1

def call_implementation(protocol_hash, query):
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'routines'

    try:
        output = execute_routine(base_folder, protocol_hash, query)
        return {
            'status': 'success',
            'message': output
        }
    except:
        # TODO: In case of failure, you should fall back to the responder
        return {
            'status': 'error',
            'message': 'Failed to execute routine.'
        }

def handle_query_suitable(protocol_hash, query):
    increment_num_conversations(protocol_hash)

    if has_implementation(protocol_hash):
        return call_implementation(protocol_hash, query)
    elif get_num_conversations(protocol_hash) >= NUM_CONVERSATIONS_FOR_ROUTINE:
        # We've used this protocol enough times to justify writing a routine
        # TODO: Tools should be passed in here
        base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
        protocol_document = load_protocol_document(base_folder, protocol_hash)
        implementation = write_routine_for_tools([], protocol_document)
        add_routine(protocol_hash, implementation)
        return call_implementation(protocol_hash, query)
    else:
        return reply_to_query(query, protocol_hash)
        

def handle_query(protocol_hash, protocol_sources, query):
    if protocol_hash is None:
        return reply_to_query(query, None)

    if has_implementation(protocol_hash):
        return call_implementation(protocol_hash, query)

    if protocol_hash in PROTOCOL_INFOS:
        if PROTOCOL_INFOS[protocol_hash]['suitability'] == Suitability.UNKNOWN:
            # Determine if we can support this protocol
            base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
            protocol_document = load_protocol_document(base_folder, protocol_hash)
            if check_protocol_for_tools(protocol_document, query):
                PROTOCOL_INFOS[protocol_hash]['suitability'] = Suitability.ADEQUATE
            else:
                PROTOCOL_INFOS[protocol_hash]['suitability'] = Suitability.INADEQUATE

        if PROTOCOL_INFOS[protocol_hash]['suitability'] == Suitability.ADEQUATE:
            return handle_query_suitable(protocol_hash, query)
        else:
            return {
                'status': 'error',
                'message': 'Protocol not suitable.'
            }
    else:
        print('Protocol sources:', protocol_sources)
        for protocol_source in protocol_sources:
            protocol_document = download_and_verify_protocol(protocol_hash, protocol_source)
            if protocol_document is not None:
                register_new_protocol(protocol_hash, protocol_source, protocol_document)
                return handle_query_suitable(protocol_hash, query)
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
        'protocols': { protocol_hash: [PROTOCOL_INFOS[protocol_hash]['source']] for protocol_hash in PROTOCOL_INFOS }
    }