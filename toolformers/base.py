from abc import ABC, abstractmethod

class Parameter:
    def __init__(self, name, description, required):
        self.name = name
        self.description = description
        self.required = required

    def as_openai_info(self):
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

class Tool:
    def __init__(self, name, description, parameters, function):
         self.name = name
         self.description = description
         self.parameters = parameters
         self.function = function
    
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


class Conversation(ABC):
    @abstractmethod
    def chat(self, message, role='user'):
        pass

class Toolformer(ABC):
    @abstractmethod
    def new_conversation(self, starting_messages=None, print_output=True) -> Conversation:
        pass

