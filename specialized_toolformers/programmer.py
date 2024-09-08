# The programmer creates implementations depending on a protocol specification

import json
import os

from toolformers.openai_toolformer import OpenAIToolformer

TASK_PROGRAMMER_PROMPT = '''
You are ProtocolProgrammerGPT. Your task is to write a routine that takes some task data (which follows a JSON schema that will be provided later) \
and creates a query in a format defined by the protocol.
The routine is a Python file that contains a function "prepare_query". prepare_query takes a single argument, "task_data", which is a JSON object, and must return a string, \
which is the query formatted according to the protocol's specification.
Rules:
- The implementation must be written in Python.
- You can define any number of helper functions and import any libraries that are part of the Python standard library.
- Do not import libraries that are not part of the Python standard library.
- Your task is to prepare the query. Do not compute the response! That will be the service's job.
- Remember to import standard libraries if you need them.
- If there is an unexpected error that is not covered by the protocol, throw an exception.\
 If instead the protocol specifies how to handle the error, return the response according to the protocol's specification.
- Do not execute anything (aside from library imports) when the file itself is loaded. I will personally import the file and call the prepare_query function with the task data.
Begin by thinking about the implementation and how you would structure the code. \
Then, write your implementation by writing a code block that contains the tags <IMPLEMENTATION> and </IMPLEMENTATION>. For example:
```python
<IMPLEMENTATION>

def prepare_query(task_data):
  ...

</IMPLEMENTATION>
'''

TOOL_PROGRAMMER_PROMPT = '''
You are ProtocolProgrammerGPT. Your task is to write a routine that takes a query formatted according to the protocol and returns a response.
The routine is a Python file that contains a function "reply". reply takes a single argument, "query", which is a string, and must return a string.
Depending on the protocol, the routine might be need to perform some actions before returning the response. The user might provide you with a list of \
Python functions you can call to help you with this task. You don't need to worry about importing them, they are already available in the environment.
Rules:
- The implementation must be written in Python.
- You can define any number of helper functions and import any libraries that are part of the Python standard library.
- Do not import libraries that are not part of the Python standard library.
- Remember to import standard libraries if you need them.
- If there is an unexpected error that is not covered by the protocol, throw an exception.\
 If instead the protocol specifies how to handle the error, return the response according to the protocol's specification.
- Do not execute anything (aside from library imports) when the file itself is loaded. I will personally import the file and call the reply function with the task data.
Begin by thinking about the implementation and how you would structure the code. \
Then, write your implementation by writing a code block that contains the tags <IMPLEMENTATION> and </IMPLEMENTATION>. For example:
```python
<IMPLEMENTATION>

def reply(query):
  ...

</IMPLEMENTATION>
'''

def write_routine_for_task(task_schema, protocol_document):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), TASK_PROGRAMMER_PROMPT, [], model='gpt-4o')
    conversation = toolformer.new_conversation(category='programming')
    reply = conversation.chat('JSON schema:\n\n' + json.dumps(task_schema) + '\n\n' + 'Protocol document:\n\n' + protocol_document, print_output=True)

    if reply.find('<IMPLEMENTATION>') == -1 or reply.find('</IMPLEMENTATION>') == -1:
        raise Exception('No implementation found')
    
    implementation = reply[reply.find('<IMPLEMENTATION>') + len('<IMPLEMENTATION>'):reply.find('</IMPLEMENTATION>')].strip()

    implementation = implementation.replace('def prepare_query(', 'def run(')

    return implementation


def write_routine_for_tools(tools, protocol_document, additional_info):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), TOOL_PROGRAMMER_PROMPT + additional_info, [], model='gpt-4o')

    message = 'Protocol document:\n\n' + protocol_document + '\n\n' + 'Additional functions:\n\n'

    if len(tools) == 0:
        message += 'No additional functions provided'
    else:
        for tool in tools:
            message += tool.as_documented_python() + '\n\n'

    conversation = toolformer.new_conversation(category='programming')

    reply = conversation.chat(message, print_output=True)

    if reply.find('<IMPLEMENTATION>') == -1 or reply.find('</IMPLEMENTATION>') == -1:
        raise Exception('No implementation found')
    
    implementation = reply[reply.find('<IMPLEMENTATION>') + len('<IMPLEMENTATION>'):reply.find('</IMPLEMENTATION>')].strip()

    implementation = implementation.replace('def reply(', 'def run(')

    return implementation