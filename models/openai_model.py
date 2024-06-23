import os
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

class OpenAIModel():
    def __init__(self, api_key, model="gpt-3.5-turbo"):
        self.client = OpenAI(api_key=api_key)
        self.model=model

    def chat(self, messages):
        reply = self.client.chat.completions.create(messages=messages, model=self.model)
        new_message = {
            "role": reply.choices[0].message.role,
            "content": reply.choices[0].message.content
        }

        updated_conversation = list(messages)
        updated_conversation.append(new_message)

        return new_message["content"], updated_conversation
    
client = OpenAIModel(api_key=os.environ.get("OPENAI_API_KEY"))

"""print(client.chat([
    {
        "role": "system",
        "content": "You are a helpful assistant."
    },
    {
        "role": "user",
        "content": "What is the meaning of life?"
    }
]))"""