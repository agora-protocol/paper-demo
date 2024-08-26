# The querier is a special toolformer that queries a service based on a protocol document.
# It receives the protocol document and writes the query that must be performed to the system.

import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import os

from toolformers.openai_toolformer import OpenAIToolformer

QUERIER_PROMPT = 'You are QuerierGPT. You will receive a protocol document detailing how to query a service. Use the provided functions to write the query that must be performed to the system.' \
    'Only reply the query itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting.'

def construct_query(protocol_document, query_description):
    toolformer = OpenAIToolformer(os.environ.get("OPENAI_API_KEY"), QUERIER_PROMPT, [])

    conversation = toolformer.new_conversation()

    reply = conversation.chat('The protocol is the following:\n\n' + protocol_document + '\n\nYou should format the query such that it does the following thing:' + query_description , print_output=False)

    return reply