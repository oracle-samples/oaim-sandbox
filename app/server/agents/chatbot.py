"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore langgraph, oraclevs, checkpointer, ainvoke

from datetime import datetime, timezone
import json
from typing import Literal

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import tools_condition, ToolNode

from pydantic import BaseModel, Field

from server.agents.tools.oraclevs_retriever import oraclevs_tool
from common.schema import ChatResponse, ChatUsage, ChatChoices, ChatMessage
from common import logging_config

# from IPython.display import Image, display


logger = logging_config.logging.getLogger("server.agents.chatbot")


#############################################################################
# AGENT STATE
#############################################################################
class AgentState(MessagesState):
    """Establish our Agent State Machine"""

    logger.info("Establishing Agent State")
    final_response: ChatResponse  # OpenAI Response
    cleaned_messages: list  # Messages w/o VS Results


#############################################################################
# Functions
#############################################################################
def get_messages(state: AgentState, config: RunnableConfig) -> list:
    """Return a list of messages that will be passed to the model for completion
    Filter out old VS documents to avoid blowing-out the context window
    Leave the state as is for GUI functionality"""
    use_history = config["metadata"]["use_history"]

    # If user decided for no history, only take the last message
    state_messages = state["messages"] if use_history else state["messages"][-1:]

    messages = []
    logger.debug("*** Messages:")
    for msg in state_messages:
        logger.debug("--> %s", repr(msg))
        if isinstance(msg, SystemMessage):
            continue
        if isinstance(msg, ToolMessage):
            if messages:  # Check if there are any messages in the list
                messages.pop()  # Remove the last appended message
            continue
        messages.append(msg)

    return messages


def document_formatter(message) -> str:
    """Extract the RAG Documents and format into a string"""
    rag_context = json.loads(message)
    chunks = "\n\n".join([doc["page_content"] for doc in rag_context])
    logger.debug("Generated Chunks: %s", chunks)
    return chunks


#############################################################################
# NODES and EDGES
#############################################################################
def respond(state: AgentState, config: RunnableConfig) -> ChatResponse:
    """Respond in OpenAI Compatible return"""
    ai_message = state["messages"][-1]
    logger.debug("Formatting Response to OpenAI compatible message: %s", repr(ai_message))
    model_name = config["metadata"]["model_name"]
    if "model" in ai_message.response_metadata:
        ai_metadata = ai_message
    else:
        ai_metadata = state["messages"][1]
        logger.debug("Using Metadata from: %s", repr(ai_metadata))

    openai_response = ChatResponse(
        id=ai_message.id,
        created=int(datetime.now(timezone.utc).timestamp()),
        model=model_name,
        usage=ChatUsage(
            prompt_tokens=ai_metadata.response_metadata.get("token_usage", {}).get("prompt_tokens", -1),
            completion_tokens=ai_metadata.response_metadata.get("token_usage", {}).get("completion_tokens", -1),
            total_tokens=ai_metadata.response_metadata.get("token_usage", {}).get("total_tokens", -1),
        ),
        choices=[
            ChatChoices(
                index=0,
                message=ChatMessage(
                    role="ai",
                    content=ai_message.content,
                    additional_kwargs=ai_metadata.additional_kwargs,
                    response_metadata=ai_metadata.response_metadata,
                ),
                finish_reason=ai_metadata.response_metadata.get("finish_reason", "stop"),
                logprobs=None,
            )
        ],
    )
    return {"final_response": openai_response}


def grade_documents(state: AgentState, config: RunnableConfig) -> Literal["vs_irrelevant", "vs_generate"]:
    """Determines whether the retrieved documents are relevant to the question."""
    logger.info("Grading RAG Response")

    # Data model
    class Grade(BaseModel):
        """Binary score for relevance check."""

        binary_score: str = Field(description="Relevance score 'yes' or 'no'")

    # LLM (Bound to Tool)
    model = config["configurable"].get("ll_client", None)
    llm_with_grader = model.with_structured_output(Grade)

    # Extract the context and question for the grader
    question = state["messages"][-3].content  # Tool call is [-2]
    context = document_formatter(state["messages"][-1].content)
    if "I think you found a bug!" in context or "Please fix your mistakes" in context:
        logger.exception("Found a bug: %s", context)
        return "vs_irrelevant"

    # Prompt
    grade_template = """
    You are a Grader assessing relevance of retrieved documents to user input.
    Here are the retrieved document:
    -------
    {context}
    -------
    Here is the user input:
    -------
    {question}
    -------
    If the documents contain keyword(s) or semantic meaning related to the user input,
    grade it as relevant. Give a binary score 'yes' or 'no' score to indicate whether the
    document is relevant to the question.
    """
    grader = PromptTemplate(
        template=grade_template,
        input_variables=["context", "question"],
    )
    logger.debug("Grading: %s against: %s", question, context)
    chain = grader | llm_with_grader

    scored_result = chain.invoke({"question": question, "context": context})
    score = scored_result.binary_score
    logger.info("Grading Decision: RAG Relevant: %s", score)
    if score == "yes":
        return "vs_generate"
    else:
        return "vs_irrelevant"


def vs_irrelevant(state: AgentState) -> None:
    """
    Delete documents from last vs_retrieve as they are not relevant to the question
    """
    state["messages"][-1].content = "[]"


async def vs_generate(state: AgentState, config: RunnableConfig) -> None:
    """Generate answer when RAG enabled; modify state with response"""
    logger.info("Generating RAG Response")

    # Extract the context and question for the completion
    question = state["messages"][-3].content  # Tool call is [-2]
    context = document_formatter(state["messages"][-1].content)

    # Generate prompt with RAG context
    generate_template = "SystemMessage(content='{sys_prompt}\n {context}'), HumanMessage(content='{question}')"
    prompt_template = PromptTemplate(
        template=generate_template,
        input_variables=["sys_prompt", "context", "question"],
    )

    # Chain and Run
    llm = config["configurable"].get("ll_client", None)
    generate_chain = prompt_template | llm | StrOutputParser()

    logger.debug("Completing: %s against: %s", question, context)
    chain = {
        "sys_prompt": config["metadata"]["sys_prompt"].prompt,
        "context": context,
        "question": question,
    }

    response = await generate_chain.ainvoke(chain)
    return {"messages": ("assistant", response)}


async def agent(state: AgentState, config: RunnableConfig) -> AgentState:
    """Invokes the agent model; response will either be a tool call or completion"""
    use_rag = config["metadata"]["rag_settings"].rag_enabled
    logger.info("Starting Agent with RAG: %s", use_rag)

    model = config["configurable"].get("ll_client", None)
    # Bind the retriever to the model if RAG is enabled
    if use_rag:
        logger.debug("Binding model to oraclevs_tool")
        # tool_choice will force a vector search when RAG enabled
        try:
            model = model.bind_tools(tools, tool_choice="oraclevs_tool")
        except Exception as ex:
            # TODO(gotsysdba): Fallback to non-tool RAG
            logger.exception("Model doesn't support tools: %s", ex)

    messages = get_messages(state, config)

    # This response will either make a tool call or provide a completion
    if config["metadata"]["sys_prompt"].prompt:
        messages.insert(0, SystemMessage(content=config["metadata"]["sys_prompt"].prompt))
    logger.debug("Invoking on: %s", messages)

    # Invoke Chain
    response = await model.ainvoke(messages)
    return {"messages": [response], "cleaned_messages": messages}


async def generate_response(state: AgentState, config: RunnableConfig) -> AgentState:
    """Invokes the agent model; response will either be a tool call or completion"""
    model = config["configurable"].get("ll_client", None)
    messages = get_messages(state, config)
    if config["metadata"]["sys_prompt"].prompt:
        messages.insert(0, SystemMessage(content=config["metadata"]["sys_prompt"].prompt))
    logger.debug("Invoking on: %s", messages)
    response = await model.ainvoke(messages)
    return {"messages": [response], "cleaned_messages": messages}


#############################################################################
# GRAPH
#############################################################################
# Setup Tools
tools = [oraclevs_tool]

workflow = StateGraph(AgentState)

# Define the nodes
workflow.add_node("agent", agent)
workflow.add_node("vs_retrieve", ToolNode(tools))
workflow.add_node("vs_generate", vs_generate)
workflow.add_node("vs_irrelevant", vs_irrelevant)
workflow.add_node("generate_response", generate_response)
workflow.add_node("respond", respond)

# Call agent node to decide to retrieve or not
workflow.add_edge(START, "agent")

# Assess the agent decision to retrieve or not
workflow.add_conditional_edges("agent", tools_condition, {"tools": "vs_retrieve", END: "respond"})
# If retrieving, grade the documents returned and either generate (not relevant) or vs_generate (relevant)
workflow.add_conditional_edges("vs_retrieve", grade_documents)

# Generate the Output
workflow.add_edge("vs_irrelevant", "generate_response")
workflow.add_edge("generate_response", "respond")
workflow.add_edge("vs_generate", "respond")
workflow.add_edge("respond", END)

# Compile
memory = MemorySaver()
chatbot_graph = workflow.compile(checkpointer=memory)

# This will write a graph.png file of the LangGraph; don't deliver uncommented
# display(Image(chatbot_graph.get_graph(xray=True).draw_mermaid_png(output_file_path="graph.png")))
