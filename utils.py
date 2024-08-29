import base64
import hashlib
import importlib
from pathlib import Path
import urllib


import requests as request_manager

def compute_hash(s):
    # Hash a string using SHA-1 and return the base64 encoded result

    m = hashlib.sha1()
    m.update(s.encode())

    b = m.digest()

    return base64.b64encode(b).decode('ascii')

def save_protocol_document(base_folder, protocol_id, protocol_document):
    if isinstance(base_folder, str):
        base_folder = Path(base_folder)

    protocol_id = urllib.parse.quote_plus(protocol_id)
    
    path = base_folder / (protocol_id + '.txt')
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(str(path), 'w') as f:
        f.write(protocol_document)

def load_protocol_document(base_folder, protocol_id):
    if isinstance(base_folder, str):
        base_folder = Path(base_folder)

    protocol_id = urllib.parse.quote_plus(protocol_id)

    path = base_folder / (protocol_id + '.txt')

    with open(str(path), 'r') as f:
        return f.read()

def execute_routine(base_folder, protocol_id, task_data):
    if isinstance(base_folder, str):
        base_folder = Path(base_folder)

    protocol_id = urllib.parse.quote_plus(protocol_id)
    protocol_id = protocol_id.replace('%', '_')
    path = base_folder / f'{protocol_id}.py'

    print('Loading module from:', path)

    # TODO: This should be done in a safe, containerized environment
    spec = importlib.util.spec_from_file_location(protocol_id, path)
    loaded_module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(loaded_module)

    return loaded_module.run(task_data)

def save_routine(base_folder, protocol_id, routine):
    if isinstance(base_folder, str):
        base_folder = Path(base_folder)

    protocol_id = urllib.parse.quote_plus(protocol_id)
    protocol_id = protocol_id.replace('%', '_')
    path = base_folder / f'{protocol_id}.py'

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(str(path), 'w') as f:
        f.write(routine)

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
            # PROTOCOL_INFOS[protocol_hash] = {
            #     'protocol': protocol,
            #     'source': protocol_source,
            #     'suitability': Suitability.UNKNOWN
            # }
            # # Store it in protocol_documents for future reference
            # base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
            # save_protocol_document(base_folder, protocol_hash, protocol)

            return protocol
    print('Failed to download protocol from', protocol_source)
    return None

def send_raw_query(text, protocol_id, target_node, source):
    return request_manager.post(target_node, json={
        'protocolHash': protocol_id,
        'body': text,
        'protocolSources' : [source]
    })
