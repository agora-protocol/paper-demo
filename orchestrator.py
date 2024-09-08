import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import json
from pathlib import Path
import time

import libtmux
import requests as request_manager

from databases.mongo import reset_databases


def create_id_to_url_mappings(config):
    mapping = {}
    # Create the id-to-url mappings
    user_agent_port = config['orchestration']['startingPorts']['user']

    for user_id in config['users'].keys():
        mapping[user_id] = f'http://localhost:{user_agent_port}'
        user_agent_port += 1
    
    server_agent_port = config['orchestration']['startingPorts']['server']

    for server_id in config['servers'].keys():
        mapping[server_id] = f'http://localhost:{server_agent_port}'
        server_agent_port += 1
    
    protocol_db_port = config['orchestration']['startingPorts']['protocolDb']

    for protocol_db_id in config['protocolDbs']:
        mapping[protocol_db_id] = f'http://localhost:{protocol_db_port}'
        protocol_db_port += 1

    return mapping

def main():
    # 1. Reset the databases and the memory (optional)
    reset_databases()
    # TODO: Reset the memory

    # 2. Create the id-to-url mappings
    with open('config.json') as f:
        config = json.load(f)
    
    id_to_url_mappings = create_id_to_url_mappings(config)

    with open('node_urls.json', 'w') as f:
        json.dump(id_to_url_mappings, f, indent=2)

    # 3. Launch the protocol DB servers

    base_storage_path = Path('storage')
    base_log_path = Path('logs')
    tmux_server = libtmux.Server()

    for protocol_db_id in config['protocolDbs']:
        session = tmux_server.new_session(session_name=protocol_db_id, kill_session=True)
        pane = session.active_window.active_pane
        port = id_to_url_mappings[protocol_db_id].split(':')[-1]
        storage_path = base_storage_path / 'protocol_db' / protocol_db_id
        log_path = base_log_path / 'protocol_db' / (protocol_db_id + '.log')
        log_path.parent.mkdir(parents=True, exist_ok=True)
        pane.send_keys(f'PYTHONUNBUFFERED=1 flask --app agents/protocol_db/main.py run --port {port} 2>&1 | tee {log_path}')

    # 4. Launch the server agents

    for server_id in config['servers'].keys():
        session = tmux_server.new_session(session_name=server_id, kill_session=True)
        pane = session.active_window.active_pane
        port = id_to_url_mappings[server_id].split(':')[-1]
        storage_path = base_storage_path / 'server' / server_id
        log_path = base_log_path / 'server' / (server_id + '.log')
        log_path.parent.mkdir(parents=True, exist_ok=True)
        pane.send_keys(f'PYTHONUNBUFFERED=1 STORAGE_PATH={storage_path} AGENT_ID={server_id} flask --app agents/server/main.py run --port {port} 2>&1 | tee {log_path}')

    # 5. Launch the user agents

    for user_id in config['users'].keys():
        session = tmux_server.new_session(session_name=user_id, kill_session=True)
        pane = session.active_window.active_pane
        port = id_to_url_mappings[user_id].split(':')[-1]
        storage_path = base_storage_path / 'user' / user_id
        log_path = base_log_path / 'user' / (user_id + '.log')
        log_path.parent.mkdir(parents=True, exist_ok=True)
        pane.send_keys(f'PYTHONUNBUFFERED=1 STORAGE_PATH={storage_path} AGENT_ID={user_id} flask --app agents/user/main.py run --port {port} 2>&1 | tee {log_path}')

    # 6. Wait for the agents to be ready
    
    print('Waiting for the agents to be ready...', end='', flush=True)
    for i in range(3):
        time.sleep(1)
        print('.', end='', flush=True)
    print('')

    # 6. Send a sample ping to a user agent
    response = request_manager.post(id_to_url_mappings['alice'])
    print('Response from Alice:', response.text)

if __name__ == '__main__':
    main()