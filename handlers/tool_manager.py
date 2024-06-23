import sys
sys.path.append('.')

from flask import Flask, request

from toolformers.openai_toolformer import OpenAIToolformer

from tools import TOOLS

app = Flask(__name__)

@app.route("/", methods=['GET'])
def main():
    return {
        'status': 200,
        'body': 'Hello, world!'
    }


@app.route("/tools", methods=['GET'])
def get_tools():
    return {
        'status': 200,
        'body': [tool.as_standard_api() for tool in TOOLS]
    }

@app.route("/call", methods=['POST'])
def call():
    tool_name = request.json['tool']
    arguments = request.json['arguments']

    tool = next((tool for tool in TOOLS if tool.name == tool_name), None)

    if tool is not None:
        output = tool.function(**arguments)
        return {
            'status': 200,
            'body': output
        }
    else:
        return {
            'status': 404,
            'body': 'Tool not found'
        }