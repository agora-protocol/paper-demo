import datetime
import os
from typing import List

from toolformers.base import Conversation, Toolformer, Tool, send_usage_to_db
from toolformers.llama.function_calling import FunctionCallingLlm

class LlamaConversation(Conversation):
    def __init__(self, model_name, function_calling_llm : FunctionCallingLlm, category=None):
        self.model_name = model_name
        self.function_calling_llm = function_calling_llm
        self.category = category
    
    def chat(self, message, role='user', print_output=True):
        if role != 'user':
            raise ValueError('Role must be "user"')

        agent_id = os.environ.get('AGENT_ID', None)
        
        start_time = datetime.datetime.now()

        response, usage_data = self.function_calling_llm.function_call_llm(message)

        end_time = datetime.datetime.now()

        print('Usage data:', usage_data)
        if print_output:
            print(response)
        
        send_usage_to_db(usage_data, start_time, end_time, agent_id, self.category, self.model_name)
        
        return response

class LlamaToolformer(Toolformer):
    def __init__(self, model_name: str, system_prompt: str, tools: List[Tool]):
        self.function_calling_llm = FunctionCallingLlm(system_prompt=system_prompt, tools=tools, select_expert=model_name)
        self.model_name = model_name

    def new_conversation(self, category=None) -> LlamaConversation:
        return LlamaConversation(self.model_name, self.function_calling_llm, category)

def make_llama_toolformer(model_name, system_prompt: str, tools: List[Tool]):
    if model_name not in ['llama3-8b', 'llama3-70b', 'llama3-405b']:
        raise ValueError(f"Unknown model name: {model_name}")

    return LlamaToolformer(model_name, system_prompt, tools)