from abc import ABC, abstractmethod

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
    
    @staticmethod
    def from_standard_api(api_info):
        return EnumParameter(api_info["name"], api_info["description"], api_info["values"], api_info["required"])

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

    def as_standard_api(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [parameter.as_standard_api() for parameter in self.parameters]
        }

    @staticmethod
    def from_standard_api(api_info):
        parameters = []
        for parameter in api_info["parameters"]:
            if parameter["type"] == "string":
                parameters.append(StringParameter.from_standard_api(parameter))
            elif parameter["type"] == "enum":
                parameters.append(EnumParameter.from_standard_api(parameter))
            else:
                raise ValueError(f"Unknown parameter type: {parameter['type']}")

        return Tool(api_info["name"], api_info["description"], parameters, None)


class Conversation(ABC):
    @abstractmethod
    def chat(self, message, role='user'):
        pass

class Toolformer(ABC):
    @abstractmethod
    def new_conversation(self, starting_messages=None, print_output=True) -> Conversation:
        pass

