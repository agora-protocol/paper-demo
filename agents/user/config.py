import json
import random

TASK_CONFIGS = []
TASK_SCHEMAS = {}

def load_config(user_name):
    global TASK_CONFIGS
    with open('config.json') as f:
        config = json.load(f)
    
    for task_name, task_schema in config['taskSchemas'].items():
        TASK_SCHEMAS[task_name] = task_schema

    user_config = config['users'][user_name]

    for task_config in user_config['tasks']:
        TASK_CONFIGS.append(task_config)

def get_task():
    # Pick a random task
    task_config = random.choice(TASK_CONFIGS)
    task_type = task_config['schema']
    task_data = random.choice(task_config['choices'])
    target_server = random.choice(task_config['servers'])

    return task_type, task_data, target_server
