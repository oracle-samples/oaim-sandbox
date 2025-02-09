"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore ollama, pplx, huggingface, genai

from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_cohere import ChatCohere, CohereEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI
from langchain_community.embeddings.oci_generative_ai import OCIGenAIEmbeddings

from server.utils.oci import init_genai_client
from common.schema import ModelNameType, ModelTypeType, ModelEnabledType, Model, ModelAccess, OracleCloudSettings
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.models")


#####################################################
# Functions
#####################################################
async def apply_filter(
    models_all: list[Model],
    model_name: Optional[ModelNameType] = None,
    model_type: Optional[ModelTypeType] = None,
    only_enabled: Optional[ModelEnabledType] = False,
) -> list[Model]:
    """Used in direct call from list_models and agents.models"""
    logger.debug("%i models are defined", len(models_all))
    models_all = [
        model
        for model in models_all
        if (model_name is None or model.name == model_name)
        and (model_type is None or model.type == model_type)
        and (only_enabled is False or model.enabled == only_enabled)
    ]
    logger.debug("%i models after filtering", len(models_all))
    return models_all


async def get_key_value(
    model_objects: list[ModelAccess],
    model_name: ModelNameType,
    model_key: str,
) -> str:
    """Return a models key value of its configuration"""
    for model in model_objects:
        if model.name == model_name:
            return getattr(model, model_key, None)
    return None


async def get_client(
    model_objects: list[ModelAccess], model_config: dict, oci_config: OracleCloudSettings
) -> BaseChatModel:
    """Retrieve model configuration"""
    logger.debug("Model Config: %s", model_config)
    model_name = model_config["model"]
    model_api = await get_key_value(model_objects, model_name, "api")
    model_api_key = await get_key_value(model_objects, model_name, "api_key")
    model_url = await get_key_value(model_objects, model_name, "url")

    # Determine if configuring an embedding model
    try:
        embedding = model_config["rag_enabled"]
    except (AttributeError, KeyError):
        embedding = False

    # Model Classes
    model_classes = {}
    if not embedding:
        logger.debug("Configuring LL Model")
        ll_common_params = {}
        for key in [
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "max_completion_tokens",
            "streaming",
        ]:
            try:
                logger.debug("--> Setting: %s; was sent %s", key, model_config[key])
                ll_common_params[key] = model_config[key] or await get_key_value(model_objects, model_name, key)
            except KeyError:
                # Mainly for embeddings
                continue
        logger.debug("LL Model Parameters: %s", ll_common_params)
        model_classes = {
            "OpenAI": lambda: ChatOpenAI(model=model_name, api_key=model_api_key, **ll_common_params),
            "Cohere": lambda: ChatCohere(model=model_name, cohere_api_key=model_api_key, **ll_common_params),
            "ChatOllama": lambda: ChatOllama(model=model_name, base_url=model_url, model_kwargs=ll_common_params),
            "Perplexity": lambda: ChatOpenAI(
                model=model_name, base_url=model_url, api_key=model_api_key, **ll_common_params
            ),
            "ChatOCIGenAI": lambda oci_cfg=oci_config: ChatOCIGenAI(
                model_id=model_name,
                client=init_genai_client(oci_cfg),
                compartment_id=oci_cfg.compartment_id,
                model_kwargs={
                    (k if k != "max_completion_tokens" else "max_tokens"): v
                    for k, v in ll_common_params.items()
                    if k not in {"streaming"}
                },
            ),
            "GenericOpenAI": lambda: ChatOpenAI(
                model=model_name, base_url=model_url, api_key=model_api_key, **ll_common_params
            ),
        }
    if embedding:
        logger.debug("Configuring Embed Model")
        model_classes = {
            "OpenAIEmbeddings": lambda: OpenAIEmbeddings(model=model_name, api_key=model_api_key),
            "CohereEmbeddings": lambda: CohereEmbeddings(model=model_name, cohere_api_key=model_api_key),
            "OllamaEmbeddings": lambda: OllamaEmbeddings(model=model_name, base_url=model_url),
            "HuggingFaceEndpointEmbeddings": lambda: HuggingFaceEndpointEmbeddings(model=model_url),
            "OCIGenAIEmbeddings": lambda oci_cfg=oci_config: OCIGenAIEmbeddings(
                model_id=model_name,
                client=init_genai_client(oci_cfg),
                compartment_id=oci_cfg.compartment_id,
            ),
            "GenericOpenAIEmbeddings": lambda: OpenAIEmbeddings(
                model=model_name, base_url=model_url, api_key=model_api_key
            ),
        }

    try:
        logger.debug("Searching for %s in %s", model_api, model_classes)
        client = model_classes[model_api]()
        logger.debug("Model Client: %s", client)
        return client
    except (UnboundLocalError, KeyError):
        logger.error("Unable to find client; expect trouble!")
        return None
