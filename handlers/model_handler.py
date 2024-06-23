import sys
sys.path.append('.')

from pathlib import Path
import os

from flask import Flask, request
import requests as request_manager

from toolformers.base import Tool, StringParameter, EnumParameter
from toolformers.openai_toolformer import OpenAIToolformer

TOOL_MANAGER_URL = 'http://localhost:' + os.environ.get('TOOL_MANAGER_PORT', '5000')

DEFAULT_PROMPT = 'You are an AI assistant. Use the provided functions to answer questions and perform actions.'

ROUTINE_FALLBACK_PROMPT = 'You are ProtocolGPT. You will receive a protocol document detailing how to reply to a query provided by the user. Use the provided functions to answer questions and perform actions.' \
    'When replying, only reply with the string required by the protocol, with no additional information or escaping.'

def call_tool(tool_name, arguments):
    response = request_manager.post(TOOL_MANAGER_URL + '/call', json={
        'tool': tool_name,
        'arguments': arguments
    })

    response = response.json()

    return response['body']

def get_tools():
    response = request_manager.get(TOOL_MANAGER_URL + '/tools')

    # Convert from JSON
    response = response.json()

    tools = []
    for tool in response['body']:
        tool = Tool.from_standard_api(tool)
        tool.function = lambda **data: call_tool(tool.name, data)
        tools.append(tool)

    return tools

TOOLS = get_tools()
print('Started model handler. Available tools:', ', '.join([tool.name for tool in TOOLS]))

app = Flask(__name__)


def load_protocol_document(protocol_hash):
    if Path(f'protocol_documents/{protocol_hash}.txt').exists():
        with open(f'protocol_documents/{protocol_hash}.txt', 'r') as f:
            return f.read()
    else:
        return None

@app.route("/", methods=['POST'])
def main():
    message = request.json["body"]
    protocol_hash = request.json.get('protocolHash', None)
    protocol_document = None

    if protocol_hash is not None:
        protocol_document = load_protocol_document(protocol_hash)
        protocol_uris = request.json.get('protocolURIs', [])

        while protocol_document is None and len(protocol_uris) > 0:
            uri = protocol_uris.pop(0)

            print('Fetching protocol document from:', uri)

            response = request_manager.get(uri)

            if response.status_code == 200:
                # TODO: Check if the document is the correct one
                protocol_document = response.text

                # Save the protocol document
                with open(f'protocol_documents/{protocol_hash}.txt', 'w') as f:
                    f.write(protocol_document)


    if protocol_document is None:
        # Note: Here you should also fetch the protocol document from the relevant URL
        toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), DEFAULT_PROMPT, get_tools())
        conversation = toolformer.new_conversation()
    else:
        toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), ROUTINE_FALLBACK_PROMPT + '\n\n' + protocol_document, get_tools())
        conversation = toolformer.new_conversation()

    return {
        'status': 200,
        'body': conversation.chat(message, role='user', print_output=True)
    }
