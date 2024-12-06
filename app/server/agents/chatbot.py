"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# spell-checker:ignore checkpointer, langgraph, ainvoke

from datetime import datetime, timezone

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda, RunnableSerializable

from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from common.schema import ChatResponse, ChatUsage, ChatChoices, ChatMessage
from common import logging_config

logger = logging_config.logging.getLogger("server.agents.chat")


# Define chatbot agent as a "state machine"
class ChatbotState(MessagesState):
    """Final structured OpenAI response"""

    final_response: ChatResponse


def chat_pipeline(
    model: BaseChatModel,
    chat_history: bool = True,
) -> RunnableSerializable[ChatbotState, AIMessage]:
    """When not chat_history, only send through the last message"""
    preprocessor = RunnableLambda(
        lambda state: state["messages"] if chat_history else state["messages"][-1:],
        name="StateModifier",
    )
    return preprocessor | model


def format_response(state: ChatbotState):
    ai_message = state["messages"][-1]

    chat_response = ChatResponse(
        id=ai_message.id,
        created=int(datetime.now(timezone.utc).timestamp()),
        model=ai_message.response_metadata["model_name"],
        usage=ChatUsage(
            prompt_tokens=ai_message.response_metadata["token_usage"]["prompt_tokens"],
            completion_tokens=ai_message.response_metadata["token_usage"]["completion_tokens"],
            total_tokens=ai_message.response_metadata["token_usage"]["total_tokens"],
        ),
        choices=[
            ChatChoices(
                index=0,
                message=ChatMessage(
                    role="ai",
                    content=ai_message.content,
                    additional_kwargs=ai_message.additional_kwargs,
                    response_metadata=ai_message.response_metadata,
                ),
                finish_reason=ai_message.response_metadata["finish_reason"],
                logprobs=None,
            )
        ],
    )
    return {"final_response": chat_response}


def call_model(state: ChatbotState, config: RunnableConfig) -> ChatbotState:
    llm = config["configurable"].get("model", None)
    chat_history = config["configurable"].get("chat_history", True)
    runnable = chat_pipeline(llm, chat_history)
    response = runnable.invoke(state, config)

    return {"messages": [response]}


#############################################################################
# MAIN
#############################################################################
# Start Graph
workflow = StateGraph(ChatbotState)
workflow.add_node("chatbot", call_model)
workflow.add_node("respond", format_response)

# Start Graph with LLM Call
workflow.add_edge(START, "chatbot")

# End Graph with formatted output
workflow.add_edge("respond", END)

workflow.add_edge("chatbot", "respond")

# Create a "CompileGraph" to invoke the state.
memory = MemorySaver()
chatbot_graph = workflow.compile(checkpointer=memory)
