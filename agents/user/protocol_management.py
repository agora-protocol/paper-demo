import urllib

import os
from pathlib import Path
import requests as request_manager


from utils import load_protocol_document, save_protocol_document, compute_hash
from agents.user.config import TASK_SCHEMAS
from agents.user.memory import get_num_conversations, PROTOCOL_INFOS, save_memory

from specialized_toolformers.protocol_checker import check_protocol_for_task, filter_protocols_for_task
from specialized_toolformers.negotiator import negotiate_protocol_for_task
from agents.common.core import Suitability

from agents.user.config import get_protocol_db_url

def query_protocols(target_node):
    response = request_manager.get(f'{target_node}/wellknown')
    response = response.json()

    if response['status'] == 'success':
        return response['protocols']
    else:
        return []

def has_implementation(task_type, protocol_id):
    if protocol_id not in PROTOCOL_INFOS:
        return False

    if task_type not in PROTOCOL_INFOS[protocol_id]['has_implementation']:
        return False
    
    return PROTOCOL_INFOS[protocol_id]['has_implementation'][task_type]

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
    protocols_with_implementations = [ protocol_id for protocol_id in eligible_protocols if is_adequate(task_type, protocol_id) and has_implementation(task_type, protocol_id) ]

    if len(protocols_with_implementations) > 0:
        print('Found protocol with implementation:', protocols_with_implementations[0])
        return protocols_with_implementations[0]

    # If there is no matching implementation, try with protocols that have been categorized and have been deemed adequate
    adequate_protocols = [ protocol_id for protocol_id in eligible_protocols if is_adequate(task_type, protocol_id) ]

    if len(adequate_protocols) > 0:
        return adequate_protocols[0]
    
    # If there are still none, try with protocols that haven't been categorized yet (but are already in memory), categorize them and check again
    uncategorized_protocols = [protocol_id for protocol_id in eligible_protocols if protocol_id in PROTOCOL_INFOS and not is_categorized(task_type, protocol_id)]

    uncategorized_protocols = prefilter_protocols(uncategorized_protocols, task_type)

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

def prefilter_protocols(protocol_ids, task_type):
    print('Prefiltering protocols:', protocol_ids, 'for task type:', task_type)

    if len(protocol_ids) <= 1:
        # No point in prefiltering if there's only one protocol
        return protocol_ids

    protocol_metadatas = []

    for protocol_id in protocol_ids:
        print('Checking suitability for protocol:', protocol_id)
        if task_type not in PROTOCOL_INFOS[protocol_id]['suitability_info'] or \
          PROTOCOL_INFOS[protocol_id]['suitability_info'][task_type] == Suitability.UNKNOWN:
            protocol_metadatas.append({ 'id' : protocol_id, **PROTOCOL_INFOS[protocol_id]['metadata']})

    filtered_protocols = filter_protocols_for_task(protocol_metadatas, TASK_SCHEMAS[task_type])

    probably_inadequate = [protocol['id'] for protocol in protocol_metadatas if protocol not in filtered_protocols]
    for protocol_id in probably_inadequate:
        PROTOCOL_INFOS[protocol_id]['suitability_info'][task_type] = Suitability.PROBABLY_INADEQUATE
    
    save_memory()

    filtered_ids = [protocol['id'] for protocol in filtered_protocols]

    print('Filtered protocols:', filtered_ids)

    return filtered_ids

def register_new_protocol(protocol_id, source, protocol_data):
    PROTOCOL_INFOS[protocol_id] = {
        'suitability_info': {},
        'source': source,
        'has_implementation': {},
        'num_uses' : 0,
        'metadata' : {
            'name' : protocol_data['name'],
            'description' : protocol_data['description']
        }
    }
    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
    save_protocol_document(base_folder, protocol_id, protocol_data['protocol'])
    save_memory()

def submit_protocol_to_public_db(protocol_id, protocol_data):
    response = request_manager.post(get_protocol_db_url(), json={
        'name': protocol_data['name'],
        'description': protocol_data['description'],
        'protocol': protocol_data['protocol']
    })

    source_url = f'{get_protocol_db_url()}/protocol?' + urllib.parse.urlencode({
            'id': protocol_id
        })
    print('Submitted protocol to public database. URL:', source_url)

    return source_url if response.status_code == 200 else None

def negotiate_protocol(task_type, target_node):
    task_schema = TASK_SCHEMAS[task_type]
    protocol_data = negotiate_protocol_for_task(task_schema, target_node)

    protocol_id = compute_hash(protocol_data['protocol'])

    source_url = submit_protocol_to_public_db(protocol_id, protocol_data)

    if source_url is not None:
        register_new_protocol(protocol_id, source_url, protocol_data)
    else:
        raise Exception('Failed to submit protocol to public database')

    # Share the protocol with the target
    response = request_manager.post(f'{target_node}/registerNegotiatedProtocol', json={
        'protocolHash': protocol_id,
        'protocolSources': [source_url]
    })

    if response.status_code != 200:
        raise Exception('Failed to share the protocol with the target:', response.text)

    return protocol_id

def decide_protocol(task_type, target_node, num_conversations_for_protocol, num_conversations_for_negotiated_protocol):
    target_protocols = query_protocols(target_node)
    print('Target protocols:', target_protocols)

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

                metadata = request_manager.get(source.replace('protocol', 'metadata')).json()

                if metadata['status'] != 'success':
                    print('Failed to retrieve metadata:', metadata)
                    continue

                metadata = metadata['metadata']


                protocol_data = {
                    'name': metadata['name'],
                    'description': metadata['description'],
                    'protocol': protocol_document
                }

                register_new_protocol(protocol_id, source, protocol_data)

    for protocol_id in prefilter_protocols(list(target_protocols.keys()), task_type):
        # Categorize the protocol
        suitable = categorize_protocol(protocol_id, task_type)

        if suitable:
            return protocol_id

    if get_num_conversations(task_type, target_node) < num_conversations_for_protocol:
        # No point in exploring potential protocols (outside of the explicitly supported ones) if we haven't talked enough times with the target
        return None

    # If there are still none, check if we have in our memory a suitable protocol

    protocol_id = get_an_adequate_protocol(task_type, PROTOCOL_INFOS.keys())

    if protocol_id is not None:
        return protocol_id
    
    # If there are still none, check the public protocol database and categorize them
    # Note: in a real system, we wouldn't get all protocols from the database, but rather
    # only the ones likely to be suitable for the task

    public_protocols_response = request_manager.get(get_protocol_db_url()).json()

    if public_protocols_response['status'] == 'success':
        public_protocols = [x for x in public_protocols_response['protocols']]
    else:
        public_protocols = []

    print('Stored protocols:', PROTOCOL_INFOS.keys())
    print('Public protocols:', public_protocols)

    for protocol_metadata in public_protocols:
        protocol_id = protocol_metadata['id']
        # Retrieve the protocol
        
        print('Protocol ID:', urllib.parse.quote_plus(protocol_id))

        uri = f'{get_protocol_db_url()}/protocol?' + urllib.parse.urlencode({
            'id': protocol_id
        })
        print('URI:', uri)

        protocol_document_response = request_manager.get(uri)

        if protocol_document_response.status_code == 200:
            protocol_document = protocol_document_response.text
            protocol_data = {
                'name': protocol_metadata['name'],
                'description': protocol_metadata['description'],
                'protocol': protocol_document
            }
            register_new_protocol(protocol_id, uri, protocol_data)

    public_protocol_ids = prefilter_protocols([x['id'] for x in public_protocols], task_type)

    for protocol_id in public_protocol_ids:
        # Categorize the protocol
        suitable = categorize_protocol(protocol_id, task_type)

        if suitable:
            return protocol_id

    
    # If there are still none, check if we have talked enough times with the target to warrant a new protocol
    requires_negotiation_response = request_manager.get(f'{target_node}/requiresNegotiation')

    requires_negotiation = requires_negotiation_response.json()['requiresNegotiation']

    if get_num_conversations(task_type, target_node) >= num_conversations_for_negotiated_protocol or requires_negotiation:
        protocol_id = negotiate_protocol(task_type, target_node)
        # Negotiated protocols are always suitable
        PROTOCOL_INFOS[protocol_id]['suitability_info'][task_type] = Suitability.ADEQUATE

        return protocol_id
    
    # If there are still none, use the querier without any protocol
    return None
