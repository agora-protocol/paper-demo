import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import concurrent.futures
import json
from pathlib import Path
import queue
import time

import libtmux
import requests as request_manager

import databases.mongo as mongo
import databases.sql as sql

NUM_WORKERS = 20


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

        external_tools_config = config['servers'][server_id].get('externalTools', {})
        if len(external_tools_config) > 0:
            # Build a helper user agent
            helper_user_id = server_id + '_helper'
            mapping[helper_user_id] = f'http://localhost:{user_agent_port}'
            user_agent_port += 1
    
    protocol_db_port = config['orchestration']['startingPorts']['protocolDb']

    for protocol_db_id in config['protocolDbs']:
        mapping[protocol_db_id] = f'http://localhost:{protocol_db_port}'
        protocol_db_port += 1

    return mapping

def launch_instance(tmux_server, instance_type, model_type, agent_id, base_log_path, base_storage_path, id_to_url_mappings):
    session = tmux_server.new_session(session_name=agent_id, kill_session=True)
    pane = session.active_window.active_pane
    port = id_to_url_mappings[agent_id].split(':')[-1]

    storage_instance_type = 'helper' if 'helper' in agent_id else instance_type

    storage_path = base_storage_path / storage_instance_type / agent_id
    log_path = base_log_path / storage_instance_type / (agent_id + '.log')
    log_path.parent.mkdir(parents=True, exist_ok=True)

    model_type_info = f'MODEL_TYPE={model_type}' if model_type is not None else ''

    pane.send_keys(f'PYTHONUNBUFFERED=1 STORAGE_PATH={storage_path} {model_type_info} AGENT_ID={agent_id} flask --app agents/{instance_type}/main.py run --port {port} 2>&1 | tee {log_path}')

def run_query(query_id, user_id, user_url, target, task, data):
    if task == 'synchronization':
        print('Synchronizing', user_id)
        response = request_manager.post(user_url + '/synchronize')
    else:
        print(f'{query_id}: Sending task {task} to {target} for user {user_id} with data {data}')
        response = request_manager.post(user_url +'/customRun', json={
            'queryId': query_id,
            'targetServer': target,
            'type': task,
            'data': data
        })
    print('Response from', user_id, ':', response.text)
    return response.text

def process_task(worker_id, task):
    result = run_query(*task)
    return result

def worker(worker_id, task_queue, result_list):
    while not task_queue.empty():
        try:
            index, task = task_queue.get_nowait()
            result = process_task(worker_id, task)
            result_list[index] = result  # Store the result at the original index
            task_queue.task_done()
        except queue.Empty:
            break

def fifo_task_processor(task_list, num_workers):
    # Create a queue and add tasks with their indices to it
    task_queue = queue.Queue()
    result_list = [None] * len(task_list)  # Placeholder for results in original order

    for index, task in enumerate(task_list):
        task_queue.put((index, task))

    # Create a thread pool with the specified number of workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Start the worker threads
        futures = [executor.submit(worker, i, task_queue, result_list) for i in range(num_workers)]
        
        # Wait for all tasks to be processed
        for future in concurrent.futures.as_completed(futures):
            future.result()

    return result_list

def run_asynchronous(actions):
    return fifo_task_processor(actions, NUM_WORKERS)

def main():
    # 1. Reset the databases and the memory (optional)
    mongo.reset_databases()

    sql.wait_for_sql_server()

    sql.reset_database()
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
        launch_instance(tmux_server, 'protocol_db', None, protocol_db_id, base_log_path, base_storage_path, id_to_url_mappings)

    time.sleep(1)

    print('Launching server agents...')

    # 4. Launch the server agents
    for server_id, server_config in config['servers'].items():
        launch_instance(tmux_server, 'server', server_config['modelType'], server_id, base_log_path, base_storage_path, id_to_url_mappings)

        external_tools_config = server_config.get('externalTools', {})

        if len(external_tools_config) > 0:
            # Build a helper user agent
            helper_user_id = server_id + '_helper'
            launch_instance(tmux_server, 'user', server_config['modelType'], helper_user_id, base_log_path, base_storage_path, id_to_url_mappings)

    time.sleep(2)

    print('Launching user agents...')

    # 5. Launch the user agents
    for user_id, user_config in config['users'].items():
        launch_instance(tmux_server, 'user', user_config['modelType'], user_id, base_log_path, base_storage_path, id_to_url_mappings)

    # 6. Wait for the agents to be ready
    
    print('Waiting for the agents to be ready...', end='', flush=True)
    for i in range(3):
        time.sleep(1)
        print('.', end='', flush=True)
    print('')

    print('Sending sample ping.')

    # 7. Execute the screenplay

    with open('actions.json', 'r') as f:
        actions = json.load(f)

    query_id_prefix = 'geminitest_'

    parsed_actions = []
    
    query_id_counter = 0
    for user_id, (target, task), data in list(actions):
        user_url = id_to_url_mappings[user_id]
        query_id = query_id_prefix + str(query_id_counter) + ('_synchronization' if task == 'synchronization' else '')
        parsed_actions.append(
            (query_id, user_id, user_url, target, task, data)
        )
        if task != 'synchronization':
            query_id_counter += 1

    results = run_asynchronous(parsed_actions)

    with open('results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    main()