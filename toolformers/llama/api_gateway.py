import logging
import os
import sys
from typing import Optional

from langchain_community.llms.sambanova import SambaStudio
from langchain_core.language_models.llms import LLM

current_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.abspath(os.path.join(current_dir, '..'))
repo_dir = os.path.abspath(os.path.join(utils_dir, '..'))
sys.path.append(utils_dir)
sys.path.append(repo_dir)

from toolformers.llama.sambanova_langchain import SambaNovaCloud

EMBEDDING_MODEL = 'intfloat/e5-large-v2'
NORMALIZE_EMBEDDINGS = True

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class APIGateway:
    @staticmethod
    def load_llm(
        type: str,
        streaming: bool = False,
        coe: bool = False,
        do_sample: Optional[bool] = None,
        max_tokens_to_generate: Optional[int] = None,
        temperature: Optional[float] = None,
        select_expert: Optional[str] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        stop_sequences: Optional[str] = None,
        process_prompt: Optional[bool] = False,
        sambastudio_base_url: Optional[str] = None,
        sambastudio_base_uri: Optional[str] = None,
        sambastudio_project_id: Optional[str] = None,
        sambastudio_endpoint_id: Optional[str] = None,
        sambastudio_api_key: Optional[str] = None,
        sambanova_url: Optional[str] = None,
        sambanova_api_key: Optional[str] = None,
    ) -> LLM:
        """Loads a langchain Sambanova llm model given a type and parameters
        Args:
            type (str): wether to use sambastudio, or SambaNova Cloud model "sncloud"
            streaming (bool): wether to use streaming method. Defaults to False.
            coe (bool): whether to use coe model. Defaults to False.

            do_sample (bool) : Optional wether to do sample.
            max_tokens_to_generate (int) : Optional max number of tokens to generate.
            temperature (float) : Optional model temperature.
            select_expert (str) : Optional expert to use when using CoE models.
            top_p (float) : Optional model top_p.
            top_k (int) : Optional model top_k.
            repetition_penalty (float) : Optional model repetition penalty.
            stop_sequences (str) : Optional model stop sequences.
            process_prompt (bool) : Optional default to false.

            sambastudio_base_url (str): Optional SambaStudio environment URL".
            sambastudio_base_uri (str): Optional SambaStudio-base-URI".
            sambastudio_project_id (str): Optional SambaStudio project ID.
            sambastudio_endpoint_id (str): Optional SambaStudio endpoint ID.
            sambastudio_api_token (str): Optional SambaStudio endpoint API key.

            sambanova_url (str): Optional SambaNova Cloud URL",
            sambanova_api_key (str): Optional SambaNovaCloud API key.

        Returns:
            langchain llm model
        """

        if type == 'sambastudio':
            envs = {
                'sambastudio_base_url': sambastudio_base_url,
                'sambastudio_base_uri': sambastudio_base_uri,
                'sambastudio_project_id': sambastudio_project_id,
                'sambastudio_endpoint_id': sambastudio_endpoint_id,
                'sambastudio_api_key': sambastudio_api_key,
            }
            envs = {k: v for k, v in envs.items() if v is not None}
            if coe:
                model_kwargs = {
                    'do_sample': do_sample,
                    'max_tokens_to_generate': max_tokens_to_generate,
                    'temperature': temperature,
                    'select_expert': select_expert,
                    'top_p': top_p,
                    'top_k': top_k,
                    'repetition_penalty': repetition_penalty,
                    'stop_sequences': stop_sequences,
                    'process_prompt': process_prompt,
                }
                model_kwargs = {k: v for k, v in model_kwargs.items() if v is not None}

                llm = SambaStudio(
                    **envs,
                    streaming=streaming,
                    model_kwargs=model_kwargs,
                )
            else:
                model_kwargs = {
                    'do_sample': do_sample,
                    'max_tokens_to_generate': max_tokens_to_generate,
                    'temperature': temperature,
                    'top_p': top_p,
                    'top_k': top_k,
                    'repetition_penalty': repetition_penalty,
                    'stop_sequences': stop_sequences,
                }
                model_kwargs = {k: v for k, v in model_kwargs.items() if v is not None}
                llm = SambaStudio(
                    **envs,
                    streaming=streaming,
                    model_kwargs=model_kwargs,
                )

        elif type == 'sncloud':
            envs = {
                'sambanova_url': sambanova_url,
                'sambanova_api_key': sambanova_api_key,
            }
            envs = {k: v for k, v in envs.items() if v is not None}
            llm = SambaNovaCloud(
                **envs,
                max_tokens=max_tokens_to_generate,
                model=select_expert,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
            )

        else:
            raise ValueError(f"Invalid LLM API: {type}, only 'sncloud' and 'sambastudio' are supported.")

        return llm