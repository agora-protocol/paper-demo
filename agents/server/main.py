import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

from pathlib import Path
import os

if os.environ.get('STORAGE_PATH') is None:
    os.environ['STORAGE_PATH'] = str(Path().parent / 'storage' / 'server')

import json
import traceback

from flask import Flask, request


from agents.common.core import Suitability
from agents.server.memory import PROTOCOL_INFOS, register_new_protocol, has_implementation, get_num_conversations, increment_num_conversations, has_implementation, add_routine, load_memory, save_memory
from utils import load_protocol_document, execute_routine, download_and_verify_protocol
from specialized_toolformers.responder import reply_to_query
from specialized_toolformers.protocol_checker import check_protocol_for_tools
from specialized_toolformers.programmer import write_routine_for_tools
from specialized_toolformers.negotiator import handle_negotiation_for_tools

from agents.server.config import TOOLS, get_additional_info, load_config


app = Flask(__name__)

NUM_CONVERSATIONS_FOR_ROUTINE = -1

def call_implementation(protocol_hash, query):
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'routines'

    try:
        output = execute_routine(base_folder, protocol_hash, query, TOOLS)
        return {
            'status': 'success',
            'body': output
        }
    except Exception as e:
        print(traceback.print_exception(type(e), e, e.__traceback__))
        print('Error executing routine:', e)
        print('Falling back to responder')
        return reply_to_query(query, protocol_hash, TOOLS, get_additional_info())

def handle_query_suitable(protocol_hash, query):
    increment_num_conversations(protocol_hash)

    if has_implementation(protocol_hash):
        return call_implementation(protocol_hash, query)
    elif get_num_conversations(protocol_hash) >= NUM_CONVERSATIONS_FOR_ROUTINE:
        # We've used this protocol enough times to justify writing a routine
        base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
        protocol_document = load_protocol_document(base_folder, protocol_hash)
        implementation = write_routine_for_tools(TOOLS, protocol_document, get_additional_info())
        add_routine(protocol_hash, implementation)
        return call_implementation(protocol_hash, query)
    else:
        print('Calling with protocol_hash. Using tools:', TOOLS)
        return reply_to_query(query, protocol_hash, TOOLS, get_additional_info())

def handle_negotiation(raw_query):
    raw_query = json.loads(raw_query)
    conversation_id = raw_query.get('conversationId', None)
    query = raw_query['body']

    reply, conversation_id = handle_negotiation_for_tools(query, conversation_id, TOOLS, get_additional_info())

    raw_reply = {
        'conversationId': conversation_id,
        'body': reply
    }

    return {
        'status': 'success',
        'body': json.dumps(raw_reply)
    }


def handle_query(protocol_hash, protocol_sources, query):
    if protocol_hash is None:
        print('No protocol hash provided. Using TOOLS:', TOOLS)
        return reply_to_query(query, None, TOOLS, get_additional_info())
    
    if protocol_hash == 'negotiation':
        # Special protocol, default to human-written routine
        return handle_negotiation(query)

    if has_implementation(protocol_hash):
        return call_implementation(protocol_hash, query)

    if protocol_hash in PROTOCOL_INFOS:
        if PROTOCOL_INFOS[protocol_hash]['suitability'] == Suitability.UNKNOWN:
            # Determine if we can support this protocol
            base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
            protocol_document = load_protocol_document(base_folder, protocol_hash)
            if check_protocol_for_tools(protocol_document, TOOLS):
                PROTOCOL_INFOS[protocol_hash]['suitability'] = Suitability.ADEQUATE
            else:
                PROTOCOL_INFOS[protocol_hash]['suitability'] = Suitability.INADEQUATE
            save_memory()

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
                is_suitable = check_protocol_for_tools(protocol_document, TOOLS)

                if is_suitable:
                    PROTOCOL_INFOS[protocol_hash]['suitability'] = Suitability.ADEQUATE
                else:
                    PROTOCOL_INFOS[protocol_hash]['suitability'] = Suitability.INADEQUATE
                save_memory()

                if is_suitable:
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

    response = handle_query(protocol_hash, protocol_sources, data['body'])
    print('Final response:', response)
    return response

@app.route("/wellknown", methods=['GET'])
def wellknown():
    return {
        'status': 'success',
        'protocols': { protocol_hash: [PROTOCOL_INFOS[protocol_hash]['source']] for protocol_hash in PROTOCOL_INFOS if PROTOCOL_INFOS[protocol_hash]['suitability'] == Suitability.ADEQUATE }
    }


def init():
    load_config(os.environ.get('AGENT_ID'))
    load_memory()

init()
