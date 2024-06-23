import json

import requests

def run(body):
    body = json.loads(body)

    request_object = {
        'body' : body['body'],
        'stateful' : True,
    }

    if 'conversationId' in body:
        request_object['conversationId'] = body['conversationId']

    return json.dumps(requests.post('http://localhost:5001', json=request_object).json())
