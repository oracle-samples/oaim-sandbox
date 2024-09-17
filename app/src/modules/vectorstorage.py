"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import json
import re
from typing import List
import math
import modules.logging_config as logging_config

from langchain.docstore.document import Document as LangchainDocument
from langchain_community.vectorstores import oraclevs as LangchainVS
from langchain_community.vectorstores.oraclevs import OracleVS

from modules.db_utils import execute_sql
import modules.metadata as meta
import modules.st_common as st_common

logger = logging_config.logging.getLogger("modules.vectorstorage")


def init_vs(db_conn, embedding_function, store_table, distance_metric):
    """Initialise the Vector Store"""
    try:
        vectorstore = OracleVS(db_conn, embedding_function, store_table, distance_metric)
    except:
        logger.exception("Failed to initialise the Vector Store")
        raise

    logger.info("Vectorstore %s loaded", vectorstore)
    return vectorstore


def get_embedding_model(model, embed_model_config=None):
    """Return a formatted embedding model"""
    logger.debug("Retrieving Embedding Model for: %s", model)
    if embed_model_config is None:
        embed_model_config = meta.embedding_models()

    embed_api = embed_model_config[model]["api"]
    embed_url = embed_model_config[model]["url"]
    embed_key = embed_model_config[model]["api_key"]

    logger.debug("Matching Embedding API: %s", embed_api)

    if embed_api.__name__ == "OpenAIEmbeddings":
        try:
            model = embed_api(model=model, openai_api_key=embed_key)
        except Exception as ex:
            logger.exception(ex)
            raise ValueError from ex
    elif embed_api.__name__ == "OllamaEmbeddings":
        model = embed_api(model=model, base_url=embed_url)
    else:
        model = embed_api(model=embed_url)

    api_accessible, err_msg = st_common.is_url_accessible(embed_url)

    return model, api_accessible, err_msg


def get_vs_table(model, chunk_size, chunk_overlap, distance_metric):
    """Get a list of Vector Store Tables"""
    chunk_overlap_ceil = math.ceil(chunk_overlap)
    table_string = f"{model}_{chunk_size}_{chunk_overlap_ceil}_{distance_metric}"
    store_table = re.sub(r"\W", "_", table_string.upper())
    store_comment = (
        f'{{"model": "{model}",'
        f'"chunk_size": {chunk_size},'
        f'"chunk_overlap": {chunk_overlap_ceil},'
        f'"distance_metric": "{distance_metric}"}}'
    )
    logger.info("Vector Store Table: %s; Comment: %s", store_table, store_comment)
    return store_table, store_comment


def populate_vs(
    db_conn,
    store_table,
    store_comment,
    model_name,
    distance_metric,
    documents: List[LangchainDocument] = None,
    src_files: List = None,
):
    """Populate the Vector Storage"""

    def json_to_doc(file: str):
        """Creates a list of LangchainDocument from a JSON file. Returns the list of documents."""
        logger.info("Converting %s to Document", file)

        with open(file, "r", encoding="utf-8") as document:
            chunks = json.load(document)
            docs = []
            for chunk in chunks:
                page_content = chunk["kwargs"]["page_content"]
                metadata = chunk["kwargs"]["metadata"]
                docs.append(LangchainDocument(page_content=str(page_content), metadata=metadata))

        logger.info("Total Chunk Size: %i bytes", docs.__sizeof__())
        logger.info("Chunks ingested: %i", len(docs))
        return docs

    if src_files:
        documents = []
        for file in src_files:
            documents.extend(json_to_doc(file))

    logger.info("Size of Payload: %i bytes", documents.__sizeof__())
    logger.info("Total Chunks: %i", len(documents))

    # Remove duplicates (copywrites, etc)
    unique_texts = {}
    unique_chunks = []
    for chunk in documents:
        if chunk.page_content not in unique_texts:
            unique_texts[chunk.page_content] = True
            unique_chunks.append(chunk)
    logger.info("Total Unique Chunks: %i", len(unique_chunks))

    # Need to consider this, it duplicates from_documents
    LangchainVS.drop_table_purge(db_conn, store_table)

    vectorstore = OracleVS(
        client=db_conn,
        embedding_function=model_name,
        table_name=store_table,
        distance_strategy=distance_metric,
    )

    # Batch Size does not have a measurable impact on performance
    # but does eliminate issues with timeouts
    batch_size = 1000
    for i in range(0, len(unique_chunks), batch_size):
        batch = unique_chunks[i : i + batch_size]
        logger.info(
            "Processing: %i Chunks of %i",
            len(unique_chunks) if len(unique_chunks) < i + batch_size else i + batch_size,
            len(unique_chunks),
        )
        OracleVS.add_documents(vectorstore, documents=batch)

    # Build the Index
    logger.info("Creating index on: %s", store_table)
    try:
        LangchainVS.create_index(db_conn, vectorstore)
    except Exception as ex:
        logger.error("Unable to create vector index: %s", ex)

    # Comment the VS table
    comment = f"COMMENT ON TABLE {store_table} IS 'GENAI: {store_comment}'"
    execute_sql(db_conn, comment)
    db_conn.close()
