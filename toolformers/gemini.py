import datetime
import os
from typing import List

from toolformers.base import Conversation, Tool, Toolformer, send_usage_to_db

import google.generativeai as genai
from google.generativeai.generative_models import ChatSession

genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

class GeminiConversation(Conversation):
    def __init__(self, model_name, chat_agent : ChatSession, category=None):
        self.model_name = model_name
        self.chat_agent = chat_agent
        self.category = category

    def chat(self, message, role='user', print_output=True):
        agent_id = os.environ.get('AGENT_ID', None)
        time_start = datetime.datetime.now()

        response = self.chat_agent.send_message({
            'role': role,
            'parts': [
                message
            ]
        })

        time_end = datetime.datetime.now()

        usage_info = {
            'prompt_tokens': response.usage_metadata.prompt_token_count,
            'completion_tokens': response.usage_metadata.candidates_token_count
        }

        send_usage_to_db(
            usage_info,
            time_start,
            time_end,
            agent_id,
            self.category,
            self.model_name
        )

        reply = response.text

        if print_output:
            print(reply)
        
        return reply

class GeminiToolformer(Toolformer):
    def __init__(self, model_name, system_prompt, tools):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.tools = tools

    def new_conversation(self, category=None) -> Conversation:
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_prompt,
            tools=[tool.as_gemini_tool() for tool in self.tools]
        )

        chat = model.start_chat(enable_automatic_function_calling=True)

        return GeminiConversation(self.model_name, chat, category)

def make_gemini_toolformer(model_name, system_prompt, tools : List[Tool]):
    if model_name not in ['gemini-1.5-flash', 'gemini-1.5-pro']:
        raise ValueError(f"Unknown model name: {model_name}")

    return GeminiToolformer(model_name, system_prompt, tools)