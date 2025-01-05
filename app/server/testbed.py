"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v 1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore giskard testset, ollama

import pandas as pd

from pypdf import PdfReader
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

from giskard.llm import set_llm_model, set_embedding_model
from giskard.rag import generate_testset, KnowledgeBase, QATestset
from giskard.rag.question_generators import simple_questions, complex_questions

import common.schema as schema
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.testbed")

def configure_and_set_model(client_model):
    model_name, params = None, None
    if client_model.api == "OpenAI" or client_model.api == "OpenAIEmbeddings":
        model_name, params = client_model.name, {"api_key": client_model.api_key}
    elif client_model.api == "ChatOllama":
        model_name, params = (
            f"ollama/{client_model.name}",
            {"disable_structured_output": True, "api_base": client_model.url},
        )
    elif client_model.api == "OllamaEmbeddings":
        model_name, params = f"ollama/{client_model.name}", {"api_base": client_model.url}

    if client_model.type == "ll":
        set_llm_model(model_name, **params)
    else:
        set_embedding_model(model_name, **params)


def load_and_split(eval_file, chunk_size=2048):
    """Load and Split Document for Testbed"""
    logger.info("Loading %s; Chunk Size: %i", eval_file, chunk_size)
    loader = PdfReader(eval_file)
    documents = []
    for page in loader.pages:
        document = Document(text=page.extract_text())
        documents.append(document)
    splitter = SentenceSplitter(chunk_size=chunk_size)
    text_nodes = splitter(documents)

    return text_nodes


def build_knowledge_base(text_nodes: str, questions: int, ll_model: schema.Model, embed_model: schema.Model):
    """Establish a temporary Knowledge Base"""
    logger.info("KnowledgeBase creation starting...")
    configure_and_set_model(ll_model)
    configure_and_set_model(embed_model)

    knowledge_base_df = pd.DataFrame([node.text for node in text_nodes], columns=["text"])
    knowledge_base = KnowledgeBase(data=knowledge_base_df)
    logger.info("KnowledgeBase Created")

    testset = generate_testset(
        knowledge_base,
        question_generators=[
            simple_questions,
            complex_questions,
        ],
        num_questions=questions,
        agent_description="A chatbot answering questions on a knowledge base",
    )

    return testset

def load_qa_test(test_set: dict) -> QATestset:
    return QATestset.load(test_set)