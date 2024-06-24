# The Negotiator is a special Toolformer that negotiates a protocol document

import dotenv
dotenv.load_dotenv()

import base64
import hashlib
import json
import os

import requests

from toolformers.base import StringParameter, Tool
from toolformers.openai_toolformer import OpenAIToolformer

NEGOTIATOR_PROMPT = 'You are NegotiatorGPT. You are about to chat with another GPT in order to reach an agreement on the protocol that will be provided.' + \
    'Once you have reached an agreement, call the registerProtocol tool with the agreed protocol document as the argument.' + \
    'You should explain the following rules to the other party:\n' + \
    '- You can assume that the protocol has a sender and a receiver. Do not worry about how the messages will be delivered, focus only on the content of the messages.\n' + \
    '- Keep the protocol short and simple. It should be easy to understand and implement.\n' + \
    '- Do not specify how the protocol should be implemented internally. That will be up to the implementer.\n' + \
    '- The implementation will receive a string and return a string, so structure your protocol accordingly.'

def chat(message, conversation_id):
    data = {
        'body': message,
    }
    if conversation_id is not None:
        data['conversationId'] = conversation_id

    raw_reply = requests.post('http://localhost:5003', json={
        'protocolHash' : 'chat',
        'body' : json.dumps(data)
    }).json()

    wrapped_reply = json.loads(raw_reply['body'])

    return wrapped_reply['body'], wrapped_reply['conversationId']

def negotiate_protocol(protocol_description):
    found_protocol = None

    def register_protocol(protocol):
        nonlocal found_protocol
        found_protocol = protocol
        return 'done'

    registerTool = Tool(
        'registerProtocol', 'Register a protocol document. Returns "done" if done.', [
        StringParameter('protocol', 'The protocol document to register', True
                    )], register_protocol)
    
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), NEGOTIATOR_PROMPT + '\nThe protocol should fulfill the following task:\n\n' + protocol_description, [registerTool])

    conversation = toolformer.new_conversation()

    other_message = 'Hello! How may I help you?'
    conversation_id = None

    while found_protocol is None:
        print('===NegotiatorGPT===')
        message = conversation.chat(other_message, print_output=True)

        other_message, conversation_id = chat(message, conversation_id)
        print()
        print('===Other GPT===')
        print(other_message)
        print()

    return found_protocol

def compute_hash(s):
    # Hash a string using SHA-1 and return the base64 encoded result

    m = hashlib.sha1()
    m.update(s.encode())

    b = m.digest()

    return base64.b64encode(b).decode('ascii')
