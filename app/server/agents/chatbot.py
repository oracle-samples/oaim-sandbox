"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore langgraph, oraclevs, checkpointer

from datetime import datetime, timezone
import json
from typing import Literal

from langchain_core.messages import RemoveMessage
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

logger = logging_config.logging.getLogger("server.agents.chatbot")


#############################################################################
# AGENT STATE
#############################################################################
class AgentState(MessagesState):
    """Establish our Agent State Machine"""

    logger.info("Establishing Agent State")
    final_response: ChatResponse
    tools: list[str]


#############################################################################
# NODES and EDGES
#############################################################################
def format_response(state: AgentState) -> ChatResponse:
    """Format the response to be OpenAI Compatible"""
    logger.info("Formatting Response to OpenAI compatible")
    logger.debug("Formatting Response of message: %s", state["messages"][1])
    ai_metadata = state["messages"][1]
    ai_message = state["messages"][-1]

    openai_response = ChatResponse(
        id=ai_metadata.id,
        created=int(datetime.now(timezone.utc).timestamp()),
        model=ai_metadata.response_metadata["model_name"],
        usage=ChatUsage(
            prompt_tokens=ai_metadata.response_metadata["token_usage"]["prompt_tokens"],
            completion_tokens=ai_metadata.response_metadata["token_usage"]["completion_tokens"],
            total_tokens=ai_metadata.response_metadata["token_usage"]["total_tokens"],
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
                finish_reason=ai_metadata.response_metadata["finish_reason"],
                logprobs=None,
            )
        ],
    )
    response = {"final_response": openai_response}
    return response


# def grade_documents(state: AgentState, config: RunnableConfig) -> Literal["generate", "rewrite"]:
def grade_documents(state: AgentState, config: RunnableConfig) -> Literal["generate", "agent"]:
    """Determines whether the retrieved documents are:wq! relevant to the question."""
    logger.info("Grading RAG Response")

    # Data model
    class Grade(BaseModel):
        """Binary score for relevance check."""

        binary_score: str = Field(description="Relevance score 'yes' or 'no'")

    # LLM
    model = config["configurable"].get("ll_client", None)

    # LLM with tool and validation
    if config["metadata"]["rag_settings"].rag_enabled:
        model = model.bind_tools(tools, tool_choice="oraclevs_tool")
    llm_with_tool = model.with_structured_output(Grade)

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
    grade it as relevant. If the user input is a generic greeting, give a binary score of 'no'
    otherwise give a binary score 'yes' or 'no' score to indicate whether the
    document is relevant to the question.
    """

    grade_prompt = PromptTemplate(
        template=grade_template,
        input_variables=["context", "question"],
    )
    chain = grade_prompt | llm_with_tool

    messages = state["messages"]
    question = messages[0].content
    context = messages[-1].content
    if "I think you found a bug!" in context or "Please fix your mistakes" in context:
        logger.exception("Found a bug: %s", context)
        return "generate"

    scored_result = chain.invoke({"question": question, "context": context})
    score = scored_result.binary_score
    logger.info("Grading Decision: RAG Relevant: %s", score)
    if score == "yes":
        return "generate"
    else:
        logger.info("Removing Tools Call Messages")
        my_messages = list(chatbot_graph.get_state(config))
        state["messages"] = state["messages"][:-2]
        config["metadata"]["rag_settings"].rag_enabled = False
        return {"messages": [state["messages"]]}
        #return "agent"
        # return "rewrite"


# def rewrite(state: AgentState, config: RunnableConfig):
#     """Transform the query to produce a better question."""
#     logger.info("Attempting to rewrite query after failed Grade")
#     question = state["messages"][0].content

#     # Formulate a new message
#     rewrite_message = f"""
#     Look at the input and history then try to reason about the underlying semantic intent or meaning.
#     Here is the initial question:
#     -------
#     {question}
#     -------
#     Formulate an improved question:
#     """
#     # Send rewrite request
#     model = config["configurable"].get("ll_client", None)
#     response = model.invoke([SystemMessage(content=rewrite_message)])
#     return {"messages": [response]}


def generate(state: AgentState, config: RunnableConfig) -> None:
    """Generate answer when RAG enabled; modify state with response"""
    logger.info("Generating RAG Response")

    messages = state["messages"]
    # Retrieve the Human Question
    question = messages[0].content
    # Extract the RAG Documents and format
    rag_context = json.loads(messages[-1].content)
    chunks = "\n\n".join([doc["page_content"] for doc in rag_context])
    logger.debug("Generate Chunks: %s", chunks)

    # Generate prompt with RAG context
    generate_template = "SystemMessage(content='{sys_prompt}\n {context}'), HumanMessage(content='{question}')"
    prompt_template = PromptTemplate(
        template=generate_template,
        input_variables=["sys_prompt", "context", "question"],
    )

    # Chain and Run
    llm = config["configurable"].get("ll_client", None)
    generate_chain = prompt_template | llm | StrOutputParser()

    response = generate_chain.invoke(
        {
            "sys_prompt": config["metadata"]["sys_prompt"].prompt,
            "context": chunks,
            "question": question,
        }
    )
    return {"messages": ("assistant", response)}


def agent(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Invokes the agent model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, or simply end.
    """
    logger.info("Calling Chatbot Agent")
    # If user decided for no history, only take the last message
    use_history = config["metadata"]["use_history"]

    # TODO: Remove tool calls that will blow-up the context window before sending
    messages = state["messages"] if use_history else state["messages"][-1:]

    model = config["configurable"].get("ll_client", None)

    # Bind the retriever if RAG is enabled
    logger.info("RAG Enabled? %s", config["metadata"]["rag_settings"].rag_enabled)
    if config["metadata"]["rag_settings"].rag_enabled:
        logger.info("Binding agent to RAG tools")
        model = model.bind_tools(tools, tool_choice="oraclevs_tool")

    response = model.invoke(messages)
    return {"messages": [response]}


#############################################################################
# GRAPH
#############################################################################
# Setup Tools
tools = [oraclevs_tool]

workflow = StateGraph(AgentState)

# Define the nodes we will cycle between
workflow.add_node("agent", agent)
workflow.add_node("retrieve", ToolNode(tools))
# workflow.add_node("rewrite", rewrite)
workflow.add_node("generate", generate)
workflow.add_node("respond", format_response)

# Call agent node to decide to retrieve or not
workflow.add_edge(START, "agent")

# Decide whether to retrieve based on tools usage, otherwise respond
workflow.add_conditional_edges("agent", tools_condition, {"tools": "retrieve", END: "respond"})

# Edges taken after the conditional agent node is called.
# Assess agent decision
workflow.add_conditional_edges("retrieve", grade_documents)

# Generate the Output
workflow.add_edge("generate", "respond")
# workflow.add_edge("rewrite", "agent")
workflow.add_edge("respond", END)

# Compile
memory = MemorySaver()
chatbot_graph = workflow.compile(checkpointer=memory)
