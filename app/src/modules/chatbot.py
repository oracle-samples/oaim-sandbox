"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore langchain, flashrank, rerank, openai, ollama, vectorstore, pplx, mult, giskard

# Avoid warnings (and temptation to substitute) about "input"
# pylint: disable=redefined-builtin
import modules.logging_config as logging_config

# Langchain Framework
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

logger = logging_config.logging.getLogger("modules.chatbot")


def generate_response(
    chat_mgr,
    input,
    chat_history,
    enable_history,
    rag_params,
    chat_instr,
    context_instr=None,
    stream=False,
):
    """Determine Chain to establish"""
    # chat_mgr is the init'd ChatCmd class and we're calling the chat function
    # return will be: answer, chat options, RAG content
    logger.info(
        "Sending user input... RAG: %r",
        rag_params["enable"],
    )
    if rag_params["enable"]:
        return chat_mgr.langchain_rag(
            rag_params,
            chat_instr,
            context_instr,
            input,
            chat_history,
            enable_history,
            stream,
        )
    else:
        return chat_mgr.langchain(chat_instr, input, chat_history, enable_history, stream)


class ChatCmd:
    """Main Chat Class"""

    def __init__(self, llm_client, vectorstore):
        self.llm_client = llm_client
        self.vectorstore = vectorstore
        self.history_config = {"configurable": {"session_id": "any"}}

    #####################################################
    # Langchain - Non-RAG
    def langchain(self, chat_instr, input, chat_history, enable_history, stream):
        """Chain without RAG"""

        prompt_messages = [("system", chat_instr)]
        if enable_history and len(chat_history.messages) > 0:
            prompt_messages.append(MessagesPlaceholder("chat_history"))
        prompt_messages.append(("human", "{input}"))
        qa_prompt = ChatPromptTemplate.from_messages(prompt_messages)

        chain = qa_prompt | self.llm_client
        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: chat_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        if stream:
            return chain_with_history.stream({"input": input}, self.history_config)
        else:
            return chain_with_history.invoke({"input": input}, self.history_config)

    #####################################################
    # Langchain - RAG
    def langchain_rag(
        self,
        rag_params,
        chat_instr,
        context_instr,
        input,
        chat_history,
        enable_history,
        stream,
    ):
        """Chain implementing RAG"""
        logger.info("Setting up Retriever")

        # Search Type
        search_type = rag_params["search_type"]
        if search_type == "Similarity":
            retriever = self.vectorstore.as_retriever(
                search_type="similarity", search_kwargs={"k": rag_params["top_k"]}
            )
        elif search_type == "Similarity Score Threshold":
            retriever = self.vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "k": rag_params["top_k"],
                    "score_threshold": rag_params["score_threshold"],
                },
            )
        elif search_type == "Maximal Marginal Relevance":
            retriever = self.vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": rag_params["top_k"],
                    "fetch_k": rag_params["fetch_k"],
                    "lambda_mult": rag_params["lambda_mult"],
                },
            )

        retrieved_documents = retriever.invoke(input)
        logger.debug("Retrieved %i documents", len(retrieved_documents))
        # Retrieve documents for inspection (Use for debugging)
        # for i, doc in enumerate(retrieved_documents):
        #     logger.debug("Document %i %s", i + 1, doc)

        # QA Chain
        context_messages = [("system", context_instr)]
        if enable_history and len(chat_history.messages) > 0:
            context_messages.append(MessagesPlaceholder("chat_history"))
        context_messages.append(("human", "{input}"))
        contextualize_q_prompt = ChatPromptTemplate.from_messages(context_messages)

        prompt_messages = [("system", f"{chat_instr}\n {{context}}")]
        if enable_history and len(chat_history.messages) > 0:
            prompt_messages.append(MessagesPlaceholder("chat_history"))
        prompt_messages.append(("human", "{input}"))
        qa_prompt = ChatPromptTemplate.from_messages(prompt_messages)

        question_answer_chain = create_stuff_documents_chain(self.llm_client, qa_prompt)

        # Re-Ranking
        logger.info("Use Re-Rank: %r", rag_params["rerank"])
        if rag_params["rerank"]:
            # Instantiate the FlashrankRerank compressor
            compressor = FlashrankRerank()
            # Create the ContextualCompressionRetriever with the
            # FlashrankRerank compressor and the base retriever
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor, base_retriever=retriever
            )
            history_aware_retriever = create_history_aware_retriever(
                self.llm_client, compression_retriever, contextualize_q_prompt
            )
        else:
            history_aware_retriever = create_history_aware_retriever(
                self.llm_client, retriever, contextualize_q_prompt
            )

        # History Aware Chain
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            lambda session_id: chat_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        if stream:
            return conversational_rag_chain.stream({"input": input}, self.history_config)
        else:
            return conversational_rag_chain.invoke({"input": input}, self.history_config)
