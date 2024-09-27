"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

Models listed here are for configuration demonstration purposes only.  They are not useable by default.
Developers should configure, enable and/or provide their own model configurations as required.
"""
# spell-checker:ignore huggingface, PPLX, thenlper, mxbai, nomic, minilm
# spell-checker:ignore langchain, openai, ollama, testset, pypdf, giskard

import os
import re
import modules.logging_config as logging_config

# Embedding
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings

logger = logging_config.logging.getLogger("modules.metadata")


##########################################
# Language Model Parameters
##########################################
def lm_parameters():
    """Define example Language Model Parameters"""
    lm_parameters_dict = {
        "temperature": {
            "api": ["OpenAI"],
            "label": "Temperature",
            "desc_en": """
                Controls how creative the responses are.
                A higher temperature results in more creative and varied answers, while a lower
                temperature produces more focused and predictable ones.  It is generally
                recommended altering this or Top P but not both.
                """,
        },
        "top_p": {
            "api": ["OpenAI"],
            "label": "Top P",
            "desc_en": """
                Limits the choice of words to the most likely ones.
                Setting a lower Top P uses only the most probable words, creating safer and more
                straightforward responses.  Higher Top P allows for more diverse and creative
                word choices in the response.  It is generally recommended altering this or
                Temperature but not both.
                """,
        },
        "max_tokens": {
            "api": ["OpenAI"],
            "label": "Maximum Tokens",
            "desc_en": """
                Sets the maximum length of the response.
                The higher the number, the longer the potential response, but it won't exceed this
                limit.
                """,
        },
        "frequency_penalty": {
            "api": ["OpenAI"],
            "label": "Frequency penalty",
            "desc_en": """
                Discourages repeating the same words or phrases in the response.
                A higher frequency penalty makes repetition less likely, promoting more varied
                language in the response.
                """,
        },
        "presence_penalty": {
            "api": ["OpenAI"],
            "label": "Presence penalty",
            "desc_en": """
                Encourages the introduction of new topics or ideas in the response.
                A higher presence penalty makes bringing up new subjects more likely rather than
                sticking to what has already been mentioned.
                """,
        },
    }
    return lm_parameters_dict


##########################################
# Large Language Models
##########################################
def ll_models():
    """Define example Language Model Support"""
    # Lists are in [user, default, min, max] format
    ll_models_dict = {
        "gpt-3.5-turbo": {
            "enabled": os.getenv("OPENAI_API_KEY") is not None,
            "api": "OpenAI",
            "url": "https://api.openai.com",
            "api_key": os.environ.get("OPENAI_API_KEY", default=""),
            "openai_compat": True,
            "context_length": 4191,
            "temperature": [1.0, 1.0, 0.0, 2.0],
            "top_p": [0.9, 0.9, 0.0, 1.0],
            "max_tokens": [256, 256, 1, 4096],
            "frequency_penalty": [0.0, 0.0, -1.0, 1.0],
            "presence_penalty": [0.0, 0.0, -2.0, 2.0],
        },
        "gpt-4o-mini": {
            "enabled": os.getenv("OPENAI_API_KEY") is not None,
            "api": "OpenAI",
            "url": "https://api.openai.com",
            "api_key": os.environ.get("OPENAI_API_KEY", default=""),
            "openai_compat": True,
            "context_length": 127072,
            "temperature": [1.0, 1.0, 0.0, 2.0],
            "top_p": [0.9, 0.9, 0.0, 1.0],
            "max_tokens": [256, 256, 1, 4096],
            "frequency_penalty": [0.0, 0.0, -1.0, 1.0],
            "presence_penalty": [0.0, 0.0, -2.0, 2.0],
        },
        "gpt-4": {
            "enabled": os.getenv("OPENAI_API_KEY") is not None,
            "api": "OpenAI",
            "url": "https://api.openai.com",
            "api_key": os.environ.get("OPENAI_API_KEY", default=""),
            "openai_compat": True,
            "context_length": 127072,
            "temperature": [1.0, 1.0, 0.0, 2.0],
            "top_p": [0.9, 0.9, 0.0, 1.0],
            "max_tokens": [256, 256, 1, 8191],
            "frequency_penalty": [0.0, 0.0, -1.0, 1.0],
            "presence_penalty": [0.0, 0.0, -2.0, 2.0],
        },
        "gpt-4o": {
            "enabled": os.getenv("OPENAI_API_KEY") is not None,
            "api": "OpenAI",
            "url": "https://api.openai.com",
            "api_key": os.environ.get("OPENAI_API_KEY", default=""),
            "openai_compat": True,
            "context_length": 127072,
            "temperature": [1.0, 1.0, 0.0, 2.0],
            "top_p": [0.9, 0.9, 0.0, 1.0],
            "max_tokens": [256, 256, 1, 4095],
            "frequency_penalty": [0.0, 0.0, -1.0, 1.0],
            "presence_penalty": [0.0, 0.0, -2.0, 2.0],
        },
        "llama-3-sonar-small-32k-chat": {
            "enabled": os.getenv("PPLX_API_KEY") is not None,
            "api": "ChatPerplexity",
            "url": "https://api.perplexity.ai",
            "api_key": os.environ.get("PPLX_API_KEY", default=""),
            "openai_compat": False,
            "context_length": 127072,
            "temperature": [0.2, 0.2, 0.0, 2.0],
            "top_p": [0.9, 0.9, 0.0, 1.0],
            "max_tokens": [256, 256, 1, 28000],
            "frequency_penalty": [0.0, 0.0, -1.0, 1.0],
            "presence_penalty": [0.0, 0.0, -2.0, 2.0],
        },
        "llama-3-sonar-small-32k-online": {
            "enabled": os.getenv("PPLX_API_KEY") is not None,
            "api": "ChatPerplexity",
            "url": "https://api.perplexity.ai",
            "api_key": os.environ.get("PPLX_API_KEY", default=""),
            "openai_compat": False,
            "context_length": 127072,
            "temperature": [0.2, 0.2, 0.0, 2.0],
            "top_p": [0.9, 0.9, 0.0, 1.0],
            "max_tokens": [256, 256, 1, 28000],
            "frequency_penalty": [0.0, 0.0, -1.0, 1.0],
            "presence_penalty": [0.0, 0.0, -2.0, 2.0],
        },
        # llama3.1-8b
        "llama3.1": {
            "enabled": os.getenv("ON_PREM_OLLAMA_URL") is not None,
            "api": "ChatOllama",
            "url": os.environ.get("ON_PREM_OLLAMA_URL", default="http://127.0.0.1:11434"),
            "api_key": "",
            "openai_compat": True,
            "context_length": 131072,
            "temperature": [1.0, 1.0, 0.0, 2.0],
            "top_p": [1.0, 1.0, 0.0, 1.0],
            "max_tokens": [256, 256, 1, 2048],
            "frequency_penalty": [0.0, 0.0, -2.0, 2.0],
            "presence_penalty": [0.0, 0.0, -2.0, 2.0],
        },
    }
    return ll_models_dict


##########################################
# Embedding Model
##########################################
def embedding_models():
    """Define packaged Embedding Model Support"""
    logger.debug("Loading state with Embedding Models")
    embedding_models_dict = {
        # Model: [API, Chunk Size, API Server, API Key]
        "thenlper/gte-base": {
            "enabled": os.getenv("ON_PREM_HF_URL") is not None,
            "api": HuggingFaceEndpointEmbeddings,
            "url": os.environ.get("ON_PREM_HF_URL", default="http://127.0.0.1:8080"),
            "api_key": "",
            "openai_compat": True,
            "chunk_max": 512,
        },
        "text-embedding-3-small": {
            "enabled": os.getenv("OPENAI_API_KEY") is not None,
            "api": OpenAIEmbeddings,
            "url": "https://api.openai.com",
            "api_key": os.environ.get("OPENAI_API_KEY", default=""),
            "openai_compat": True,
            "chunk_max": 8191,
        },
        "text-embedding-3-large": {
            "enabled": os.getenv("OPENAI_API_KEY") is not None,
            "api": OpenAIEmbeddings,
            "url": "https://api.openai.com",
            "api_key": os.environ.get("OPENAI_API_KEY", default=""),
            "openai_compat": True,
            "chunk_max": 8191,
        },
        "mxbai-embed-large": {
            "enabled": os.getenv("ON_PREM_OLLAMA_URL") is not None,
            "api": OllamaEmbeddings,
            "url": os.environ.get("ON_PREM_OLLAMA_URL", default="http://127.0.0.1:11434"),
            "api_key": "",
            "openai_compat": True,
            "chunk_max": 512,
        },
        "nomic-embed-text": {
            "enabled": os.getenv("ON_PREM_OLLAMA_URL") is not None,
            "api": OllamaEmbeddings,
            "url": os.environ.get("ON_PREM_OLLAMA_URL", default="http://127.0.0.1:11434"),
            "api_key": "",
            "openai_compat": True,
            "chunk_max": 8192,
        },
        "all-minilm": {
            "enabled": os.getenv("ON_PREM_OLLAMA_URL") is not None,
            "api": OllamaEmbeddings,
            "url": os.environ.get("ON_PREM_OLLAMA_URL", default="http://127.0.0.1:11434"),
            "api_key": "",
            "openai_compat": True,
            "chunk_max": 256,
        },
    }
    return embedding_models_dict


##########################################
# LM Prompt Engineering
##########################################
def prompt_engineering():
    """Define packaged Embedding Model Support"""
    prompt_engineering_dict = {
        "Basic Example": {
            "prompt": """
                You are a friendly, helpful assistant.
                """
        },
        "RAG Example": {
            "prompt": """
                You are an assistant for question-answering tasks.
                Use the retrieved Documents and history to answer the question as accurately and
                comprehensively as possible.  Keep your answer grounded in the facts of the
                Documents, be concise, and reference the Documents where possible.
                If you don't know the answer, just say that you are sorry as you don't haven't
                enough information.
                """
        },
        "Custom": {
            "prompt": """
                You are an assistant for question-answering tasks.
                Use the retrieved Documents and history to answer the question.
                If the documents do not contain the specific information, do your best to still answer.
                """
        },
    }
    # Format the prompts (remove leading/trailing/new space chars)
    pattern = r"\s+"
    for key, value in prompt_engineering_dict.items():
        prompt_engineering_dict[key]["prompt"] = " ".join(re.split(pattern, value["prompt"], flags=re.UNICODE))
    return prompt_engineering_dict
