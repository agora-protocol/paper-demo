# The Programmer is a special Toolformer that takes a protocol
# document and writes a routine to be added to the system

import dotenv
dotenv.load_dotenv()

import os

from toolformers.openai_toolformer import OpenAIToolformer

PROGRAMMER_PROMPT = 'You are ProgrammerGPT. You will receive a protocol document detailing how to write a routine to be added to the system. Use the provided functions to write the routine.' \
    'When writing the routine, only write the code required by the protocol, with no additional information or escaping.' \
    'The routine is a Python file that contains a function "run". run takes a single argument, "body", which is a string, and must return a string.'

from tools import TOOLS

EXAMPLE_CODE = '''
call_tool(tool_name, argument_1=value_1, argument_2=value_2)
'''

PROGRAMMER_PROMPT += '\nYou also have access to the following tools:\n' + '\n'.join([tool.as_documented_python() for tool in TOOLS]) + '\n\n' + \
    'You can use these tools in your routine, e.g.:\n\n' + \
    '```python\n{EXAMPLE_CODE}\n```\n\n' + \
    'Where argument_1 is the name of the first argument, value_1 is the value of the first argument, and so on. When calling call_tool, always use a positional argument for tool_name and keyword arguments for the other parameters.\n' + \
    'Note: call_tool is a function, not a module! It will be already available to you in the routine scope.\n' + \
    'Keep in mind that you\'re not forced to use these tools, but they are available if you need them.' + \
    'Do not import any module that is not one of the standard Python libraries'

def write_routine(protocol_document):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), PROGRAMMER_PROMPT, [])

    conversation = toolformer.new_conversation()

    reply = conversation.chat('The protocol is the following:\n\n' + protocol_document, print_output=False)

    # Match ```python\n{code}\n``` and extract {code}

    code = reply.split('```python\n')[1].split('\n```')[0]

    return code

BOILERPLATE = """import sys
sys.path.append('.')
from tools import call_tool

"""

def create_and_save_routine(protocol_hash):
    with open(f'protocol_documents/{protocol_hash}.txt', 'r') as f:
        protocol_document = f.read()

    routine = write_routine(protocol_document)
    routine = BOILERPLATE + routine
    print('Obtained routine:\n' + routine)

    with open(f'routines/{protocol_hash}.py', 'w') as f:
        f.write(routine)
