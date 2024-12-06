"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore ollama, pplx

from typing import Optional

from langchain_community.chat_models import ChatPerplexity
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_cohere import ChatCohere
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

import common.logging_config as logging_config
import common.schema as schema

logger = logging_config.logging.getLogger("server.models")


#####################################################
# Functions
#####################################################
async def filter_models(
    models_all: list[schema.ModelModel],
    model_name: Optional[schema.ModelNameType] = None,
    model_type: Optional[schema.ModelTypeType] = None,
    enabled: Optional[schema.ModelEnabledType] = None,
) -> list[schema.ModelModel]:
    """Used in direct call from list_models and agents.models"""
    logger.info("%i models are defined", len(models_all))
    models_all = [
        model
        for model in models_all
        if (model_name is None or model.name == model_name)
        and (model_type is None or model.type == model_type)
        and (enabled is None or model.enabled == enabled)
    ]
    logger.info("%i models after filtering", len(models_all))
    return models_all


async def get_model_key_value(
    model_objects: list[schema.ModelModel], model_name: schema.ModelNameType, model_key: str
) -> str:
    for model in model_objects:
        if model.name == model_name:
            return getattr(model, model_key, None)
    return None


async def get_model_client(
    model_objects: list[schema.ModelModel],
    model_type: schema.ModelTypeType,
    model_config: schema.LanguageParametersModel,
) -> BaseChatModel:
    # Retrieve model configuration

    model_api = await get_model_key_value(model_objects, model_config.model, "api")
    model_api_key = await get_model_key_value(model_objects, model_config.model, "api_key")

    if model_type == "ll":
        common_params = {
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_completion_tokens,
            "top_p": model_config.top_p,
            "frequency_penalty": model_config.frequency_penalty,
            "presence_penalty": model_config.presence_penalty,
        }
        if model_api == "OpenAI":
            return ChatOpenAI(
                api_key=model_api_key,
                **common_params,
            )

        if model_api == "Cohere":
            return ChatCohere(
                cohere_api_key=model_api_key,
                **common_params,
            )

        if model_api == "ChatOllama":
            return ChatOllama(
                model=model_config.model,
                base_url=model_config.url,
                model_kwargs=common_params,
            )

        if model_api == "ChatPerplexity":
            return ChatPerplexity(
                pplx_api_key=model_api_key,
                model_kwargs=common_params,
            )

    return None
