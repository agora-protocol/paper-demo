import os

from toolformers.camel import make_openai_toolformer
from toolformers.gemini import make_gemini_toolformer
from toolformers.llama import make_llama_toolformer


def make_toolformer(model_type_internal, system_prompt, tools):
    if model_type_internal in ['gpt-4o', 'gpt-4o-mini']:
        return make_openai_toolformer(model_type_internal, system_prompt, tools)
    elif model_type_internal in ['gemini-1.5-flash', 'gemini-1.5-pro']:
        return make_gemini_toolformer(model_type_internal, system_prompt, tools)
    elif model_type_internal in ['llama3-8b', 'llama3-70b', 'llama3-405b']:
        return make_llama_toolformer(model_type_internal, system_prompt, tools)
    else:
        raise ValueError(f'Unsupported model type: {model_type_internal}')

def make_default_toolformer(system_prompt, tools):
    model_type_internal = os.environ.get('MODEL_TYPE', 'gpt-4o-mini')
    return make_toolformer(model_type_internal, system_prompt, tools)