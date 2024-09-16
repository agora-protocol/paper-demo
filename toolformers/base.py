from abc import ABC, abstractmethod

import json

from google.generativeai.types import CallableFunctionDeclaration
import google.generativeai.types.content_types as content_types

from databases.mongo import insert_one

from utils import get_query_id

class Parameter:
    def __init__(self, name, description, required):
        self.name = name
        self.description = description
        self.required = required

    def as_openai_info(self):
        pass

    def as_standard_api(self):
        pass

class StringParameter(Parameter):
    def __init__(self, name, description, required):
        super().__init__(name, description, required)

    def as_openai_info(self):
        return {
            "type": "string",
            "name": self.name,
            "description": self.description
        }

    def as_standard_api(self):
        return {
            "type": "string",
            "name": self.name,
            "description": self.description,
            "required": self.required
        }

    def as_natural_language(self):
        return f'{self.name} (string{", required" if self.required else ""}): {self.description}.'

    def as_documented_python(self):
        return f'{self.name} (str{", required" if self.required else ""}): {self.description}.'
    
    def as_gemini_tool(self):
        return {
            'type': 'string',
            'description': self.description
        }

    @staticmethod
    def from_standard_api(api_info):
        return StringParameter(api_info["name"], api_info["description"], api_info["required"])

class EnumParameter(Parameter):
    def __init__(self, name, description, values, required):
        super().__init__(name, description, required)
        self.values = values

    def as_openai_info(self):
        return {
            "type": "string",
            "description": self.description,
            "values": self.values
        }

    def as_standard_api(self):
        return {
            "type": "enum",
            "name": self.name,
            "description": self.description,
            "values": self.values,
            "required": self.required
        }
    
    def as_natural_language(self):
        return f'{self.name} (enum{", required" if self.required else ""}): {self.description}. Possible values: {", ".join(self.values)}'
    
    def as_documented_python(self):
        return f'{self.name} (str{", required" if self.required else ""}): {self.description}. Possible values: {", ".join(self.values)}'

    def as_gemini_tool(self):
        return {
            'description': self.description,
            'type': 'string',
            'enum': self.values
        }
    
    @staticmethod
    def from_standard_api(api_info):
        return EnumParameter(api_info["name"], api_info["description"], api_info["values"], api_info["required"])

class Tool:
    def __init__(self, name, description, parameters, function, output_schema=None):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.function = function
        self.output_schema = output_schema
    
    def call_tool_for_toolformer(self, *args, **kwargs):
        print(f'Toolformer called tool {self.name} with args {args} and kwargs {kwargs}')
        # Unlike a call from a routine, this call catches exceptions and returns them as strings
        try:
            tool_reply = self.function(*args, **kwargs)
            print(f'Tool {self.name} returned: {tool_reply}')
            return tool_reply
        except Exception as e:
            print(f'Tool {self.name} failed with exception: {e}')
            return 'Tool call failed: ' + str(e)
    
    def as_openai_info(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type" : "object",
                    "properties": {parameter.name : parameter.as_openai_info() for parameter in self.parameters},
                    "required": [parameter.name for parameter in self.parameters if parameter.required]
                }
            }
        }
    
    def as_gemini_tool(self) -> CallableFunctionDeclaration:
        return content_types.Tool([CallableFunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters={
                'type': 'object',
                'properties': {parameter.name: parameter.as_gemini_tool() for parameter in self.parameters},
                'required': [parameter.name for parameter in self.parameters if parameter.required]
            },
            function=self.call_tool_for_toolformer
        )])

    def as_llama_schema(self):
        schema = {
            'name': self.name,
            'description': self.description,
            'parameters': {parameter.name : parameter.as_openai_info() for parameter in self.parameters},
            'required': [parameter.name for parameter in self.parameters if parameter.required]
        }

        if self.output_schema is not None:
            schema['output_schema'] = self.output_schema
        
        return schema

    def as_natural_language(self):
        print('Converting to natural language')
        print('Number of parameters:', len(self.parameters))
        nl = f'Function {self.name}: {self.description}. Parameters:\n' + '\n'.join([parameter.as_natural_language() for parameter in self.parameters])

        if self.output_schema is not None:
            nl += f'\nOutput schema: {json.dumps(self.output_schema, indent=2)}'
        
        return nl

    def as_standard_api(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [parameter.as_standard_api() for parameter in self.parameters]
        }
    
    def as_documented_python(self):
        documented_python = f'Tool {self.name}:\n\n{self.description}\nParameters:\n' + \
            '\n'.join([parameter.as_documented_python() for parameter in self.parameters])
        
        if self.output_schema is not None:
            documented_python += f'\nOutput schema: {json.dumps(self.output_schema, indent=2)}'
            documented_python += '\nKeep in mind that the output is a JSON formatted string, so you might need to parse it.'

        return documented_python

    def as_executable_function(self):
        # Create an actual function that can be called
        def f(*args, **kwargs):
            return self.function(*args, **kwargs)
        
        return f

    @staticmethod
    def from_standard_api(api_info): # TODO: Drop?
        parameters = []
        for parameter in api_info["parameters"]:
            if parameter["type"] == "string":
                parameters.append(StringParameter.from_standard_api(parameter))
            elif parameter["type"] == "enum":
                parameters.append(EnumParameter.from_standard_api(parameter))
            else:
                raise ValueError(f"Unknown parameter type: {parameter['type']}")

        return Tool(api_info["name"], api_info["description"], parameters, None)

def send_usage_to_db(usage, time_start, time_end, agent, category, model):
    usage = {
        'timeStart': {
            '$date': time_start.isoformat()
        },
        'timeEnd': {
            '$date': time_end.isoformat()
        },
        'prompt_tokens': usage['prompt_tokens'],
        'completion_tokens': usage['completion_tokens'],
        'agent': agent,
        'category': category,
        'model': model,
        'queryId': get_query_id()
    }
    insert_one('usageLogs', 'main', usage)

class Conversation(ABC):
    @abstractmethod
    def chat(self, message, role='user', print_output=True):
        pass

class Toolformer(ABC):
    @abstractmethod
    def new_conversation(self, category=None) -> Conversation:
        pass

