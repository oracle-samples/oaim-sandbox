"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore vectorstore, vectorstores, oraclevs, mult, langgraph

from typing import Annotated

from langchain_core.tools import BaseTool, tool
from langchain_core.documents.base import Document
from langchain_core.runnables import RunnableConfig
from langchain_community.vectorstores.oraclevs import OracleVS
from langgraph.prebuilt import InjectedState

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.tools.oraclevs_retriever")


#############################################################################
# Oracle Vector Store Retriever Tool
#############################################################################
def oraclevs_tool(
    state: Annotated[dict, InjectedState],
    config: RunnableConfig,
) -> list[dict]:
    """Oracle Vector Search Tool"""
    try:
        #print(config["configurable"])
        db_conn = config["configurable"]["db_conn"]
        embed_client = config["configurable"]["embed_client"]
        rag_settings = config["metadata"]["rag_settings"]
        logger.info("Initializing Vector Store: %s", rag_settings.vector_store)
        try:
            logger.info("Connecting to VectorStore")
            vectorstore = OracleVS(db_conn, embed_client, rag_settings.vector_store, rag_settings.distance_metric)
        except Exception as ex:
            logger.exception("Failed to initialize the Vector Store")
            raise ex

        try:
            search_type = rag_settings.search_type
            search_kwargs = {"k": rag_settings.top_k}

            if search_type == "Similarity":
                retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs=search_kwargs)
            elif search_type == "Similarity Score Threshold":
                search_kwargs["score_threshold"] = rag_settings.score_threshold
                retriever = vectorstore.as_retriever(
                    search_type="similarity_score_threshold", search_kwargs=search_kwargs
                )
            elif search_type == "Maximal Marginal Relevance":
                search_kwargs.update(
                    {
                        "fetch_k": rag_settings.fetch_k,
                        "lambda_mult": rag_settings.lambda_mult,
                    }
                )
                retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs=search_kwargs)
            else:
                raise ValueError(f"Unsupported search_type: {search_type}")
            logger.info("Invoking retriever on: %s", {state["messages"][-2].content})
            documents = retriever.invoke(state["messages"][-2].content)
        except Exception as ex:
            logger.exception("Failed to perform Oracle Vector Store retrieval")
            raise ex
    except (AttributeError, KeyError, TypeError) as ex:
        documents = Document(
            id="DocumentException",
            page_content="I'm sorry, I think you found a bug!",
            metadata={"source": f"{ex}"}
        )

    documents_dict = [vars(doc) for doc in documents]
    logger.info("Found Documents: %s", documents_dict)
    return documents_dict

oraclevs_retriever: BaseTool = tool(oraclevs_tool)
oraclevs_retriever.name = "oraclevs_retriever"