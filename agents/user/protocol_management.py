import urllib

import os
from pathlib import Path
import requests as request_manager


from utils import load_protocol_document, save_protocol_document, compute_hash
from agents.user.tasks import TASK_SCHEMAS
from agents.user.memory import get_num_conversations, PROTOCOL_INFOS, save_memory

from specialized_toolformers.protocol_checker import check_protocol_for_task
from specialized_toolformers.negotiator import negotiate_protocol_for_task
from agents.common.core import Suitability


PUBLIC_PROTOCOL_DB_URL = 'http://localhost:5006'

def query_protocols(target_node):
    response = request_manager.get(f'{target_node}/wellknown')
    response = response.json()

    if response['status'] == 'success':
        return response['protocols']
    else:
        return []

def has_implementation(protocol_id):
    if protocol_id not in PROTOCOL_INFOS:
        return False
    
    return PROTOCOL_INFOS[protocol_id]['has_implementation']

def is_adequate(task_type, protocol_id):
    if protocol_id not in PROTOCOL_INFOS:
        return False
    
    if task_type not in PROTOCOL_INFOS[protocol_id]['suitability_info']:
        return False

    return PROTOCOL_INFOS[protocol_id]['suitability_info'][task_type] == Suitability.ADEQUATE

def is_categorized(task_type, protocol_id):
    if protocol_id not in PROTOCOL_INFOS:
        return False
    
    if task_type not in PROTOCOL_INFOS[protocol_id]['suitability_info']:
        return False
    
    return PROTOCOL_INFOS[protocol_id]['suitability_info'][task_type] != Suitability.UNKNOWN

def get_an_adequate_protocol(task_type, eligible_protocols):
    # Will ignore protocols that haven't been downloaded yet

    # First, try with protocols having an implementation
    protocols_with_implementations = [ protocol_id for protocol_id in eligible_protocols if is_adequate(task_type, protocol_id) and has_implementation(protocol_id) ]

    if len(protocols_with_implementations) > 0:
        print('Found protocol with implementation:', protocols_with_implementations[0])
        return protocols_with_implementations[0]

    # If there is no matching implementation, try with protocols that have been categorized and have been deemed adequate
    adequate_protocols = [ protocol_id for protocol_id in eligible_protocols if is_adequate(task_type, protocol_id) ]

    if len(adequate_protocols) > 0:
        return adequate_protocols[0]
    
    # If there are still none, try with protocols that haven't been categorized yet, categorize them and check again
    uncategorized_protocols = [protocol_id for protocol_id in eligible_protocols if not is_categorized(task_type, protocol_id)]

    for protocol_id in uncategorized_protocols:
        suitable = categorize_protocol(protocol_id, task_type)

        if suitable:
            return protocol_id

    # We're out of luck, return None
    return None

def categorize_protocol(protocol_id, task_type):
    print('Categorizing protocol:', protocol_id)
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
    protocol_document = load_protocol_document(base_folder, protocol_id)

    suitable = check_protocol_for_task(protocol_document, TASK_SCHEMAS[task_type])

    if suitable:
        PROTOCOL_INFOS[protocol_id]['suitability_info'][task_type] = Suitability.ADEQUATE
    else:
        PROTOCOL_INFOS[protocol_id]['suitability_info'][task_type] = Suitability.INADEQUATE

    save_memory()
    
    return suitable

def register_new_protocol(protocol_id, source, protocol_document):
    PROTOCOL_INFOS[protocol_id] = {
        'suitability_info': {},
        'source': source,
        'has_implementation': False,
        'num_uses' : 0
    }
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
    save_protocol_document(base_folder, protocol_id, protocol_document)
    save_memory()

def submit_protocol_to_public_db(protocol_id, protocol_document):
    response = request_manager.post(f'{PUBLIC_PROTOCOL_DB_URL}', json={
        'id': protocol_id,
        'protocol': protocol_document
    })

    source_url = f'{PUBLIC_PROTOCOL_DB_URL}/protocol?' + urllib.parse.urlencode({
            'id': protocol_id
        })
    print('Submitted protocol to public database. URL:', source_url)

    return source_url if response.status_code == 200 else None

def negotiate_protocol(task_type, target_node):
    task_schema = TASK_SCHEMAS[task_type]
    protocol = negotiate_protocol_for_task(task_schema, target_node)

    protocol_id = compute_hash(protocol)

    source_url = submit_protocol_to_public_db(protocol_id, protocol)

    if source_url is not None:
        register_new_protocol(protocol_id, source_url, protocol)
    else:
        raise Exception('Failed to submit protocol to public database')

    return protocol_id

def decide_protocol(task_type, target_node, num_conversations_for_protocol):
    target_protocols = query_protocols(target_node)

    protocol_id = get_an_adequate_protocol(task_type, list(target_protocols.keys()))

    if protocol_id is not None:
        print('Found adequate protocol from storage:', protocol_id)
        return protocol_id

    # If there are none, categorize the remaining target protocols, and try again
    for protocol_id, sources in target_protocols.items():
        if protocol_id not in PROTOCOL_INFOS:
            for source in sources:
                response = request_manager.get(source)
                protocol_document = response.text

                register_new_protocol(protocol_id, source, protocol_document)

                # Categorize the protocol
                suitable = categorize_protocol(protocol_id, task_type)

                if suitable:
                    return protocol_id
    
    # protocol = get_an_adequate_protocol(task_info, target_protocols)

    # if protocol is not None:
    #     return protocol
    
    # If there are still none, check if we have in our memory a suitable protocol

    protocol_id = get_an_adequate_protocol(task_type, PROTOCOL_INFOS.keys())

    if protocol_id is not None:
        return protocol_id
    
    # If there are still none, check the public protocol database and categorize them
    # Note: in a real system, we wouldn't get all protocols from the database, but rather
    # only the ones likely to be suitable for the task

    public_protocols_response = request_manager.get(PUBLIC_PROTOCOL_DB_URL).json()

    if public_protocols_response['status'] == 'success':
        public_protocols = public_protocols_response['protocols']
    else:
        public_protocols = []

    public_protocols = [ protocol_id for protocol_id in public_protocols if protocol_id not in PROTOCOL_INFOS ]

    print('Stored protocols:', PROTOCOL_INFOS.keys())
    print('Public protocols:', public_protocols)

    for protocol_id in public_protocols:
        # Retrieve the protocol
        
        print('Protocol ID:', urllib.parse.quote_plus(protocol_id))

        uri = f'{PUBLIC_PROTOCOL_DB_URL}/protocol?' + urllib.parse.urlencode({
            'id': protocol_id
        })
        print('URI:', uri)

        protocol_document_response = request_manager.get(uri)

        if protocol_document_response.status_code == 200:
            protocol_document = protocol_document_response.text
            register_new_protocol(protocol_id, uri, protocol_document)

    for protocol_id in public_protocols:
        # Categorize the protocol
        suitable = categorize_protocol(protocol_id, task_type)

        if suitable:
            return protocol_id

    
    # If there are still none, check if we have talked enough times with the target to warrant a new protocol

    if get_num_conversations(task_type, target_node) > num_conversations_for_protocol:
        # TODO: Negotiate a new protocol
        protocol_id = negotiate_protocol(task_type, target_node)

        return protocol_id
    
    # If there are still none, use the querier without any protocol
    return None
