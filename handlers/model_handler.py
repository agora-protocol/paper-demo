import sys
sys.path.append('.')

import os

from flask import Flask, request
import requests as request_manager

from toolformers.base import Tool, StringParameter, EnumParameter
from toolformers.openai_toolformer import OpenAIToolformer

TOOL_MANAGER_URL = 'http://localhost:' + os.environ.get('TOOL_MANAGER_PORT', '5000')

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

toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), "You are a weather bot. Use the provided functions to answer questions.", get_tools())

print('Started model handler. Available tools:', ', '.join([tool.name for tool in toolformer.tools]))

app = Flask(__name__)

@app.route("/", methods=['POST'])
def main():
    message = request.json["body"]

    return {
        'status': 200,
        'body': toolformer.new_conversation().chat(message, role='user', print_output=True)
    }
