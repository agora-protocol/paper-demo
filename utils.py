import base64
import hashlib
from pathlib import Path
import urllib

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
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(str(path), 'r') as f:
        return f.read()
