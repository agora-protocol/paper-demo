import json
import random

TASK_CONFIGS = []
TASK_SCHEMAS = {}
NODE_URLS = {}

# Workaround for the fact that once a constant is imported, it cannot be updated
_PROTOCOL_DB_URL = None
def get_protocol_db_url():
    return _PROTOCOL_DB_URL

def load_config(user_name):
    with open('config.json') as f:
        config = json.load(f)
    
    for task_name, task_schema in config['taskSchemas'].items():
        TASK_SCHEMAS[task_name] = task_schema

    user_config = config['users'][user_name]

    for task_config in user_config['tasks']:
        TASK_CONFIGS.append(task_config)

    with open('node_urls.json') as f:
        node_urls = json.load(f)
    
    for node_id, node_url in node_urls.items():
        NODE_URLS[node_id] = node_url

    global _PROTOCOL_DB_URL
    _PROTOCOL_DB_URL = NODE_URLS[user_config['protocolDb']]

def get_task():
    # Pick a random task
    task_config = random.choice(TASK_CONFIGS)
    task_type = task_config['schema']
    task_data = random.choice(task_config['choices'])
    target_server = random.choice(task_config['servers'])

    return task_type, task_data, target_server