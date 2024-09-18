import datetime
import os
from random import random
import time
import traceback
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

        exponential_backoff_lower = 30
        exponential_backoff_higher = 60
        for i in range(5):
            try:
                response = self.chat_agent.send_message({
                    'role': role,
                    'parts': [
                        message
                    ]
                })
                break
            except Exception as e:
                print(e)
                if '429' in str(e):
                    print('Rate limit exceeded. Waiting with random exponential backoff.')
                    if i < 4:
                        time.sleep(random() * (exponential_backoff_higher - exponential_backoff_lower) + exponential_backoff_lower)
                        exponential_backoff_lower *= 2
                        exponential_backoff_higher *= 2
                elif 'candidates[0]' in traceback.format_exc():
                    # When Gemini has nothing to say, it raises an error with this message
                    print('No response')
                    return 'No response'
                elif '500' in str(e):
                    # Sometimes Gemini just decides to return a 500 error for absolutely no reason. Retry.
                    print('500 error')
                    time.sleep(5)
                    traceback.print_exc()
                else:
                    raise e

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
        print('Tools:')
        print('\n'.join([str(tool.as_openai_info()) for tool in self.tools]))
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