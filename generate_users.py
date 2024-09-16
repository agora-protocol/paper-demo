import json
import random

random.seed(42)

with open('names.json', 'r') as f:
    names = json.load(f)

models = ['gpt-4o', 'gemini-1.5-pro', 'llama3-405b']

model_map = {}

for i, name in enumerate(names):
    model_map[name] = models[i % len(models)]

with open('config.json', 'r') as f:
    config = json.load(f)

config['users'] = {}

for name, model in model_map.items():
    config['users'][name] = {
        'modelType': model,
        'tasks': [],
        'protocolDb': random.choice(['protocolDb1', 'protocolDb2', 'protocolDb3'])
    }

with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)