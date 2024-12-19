"""Hello"""

# spell-checker: disable
# pylint: disable=wrong-import-position
import asyncio
import json
import pprint
import server.agents.chatbot as chatbot
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage, AnyMessage, convert_to_openai_messages
from langchain_core.runnables import RunnableConfig
import server.bootstrap as bootstrap
import server.models as models
from common import schema

# Bootstrap Definition Data
model_objects = bootstrap.model_def.main()
prompt_objects = bootstrap.prompt_eng_def.main()
database_objects = bootstrap.database_def.main()
settings_objects = bootstrap.settings_def.main()

MESSAGE0 = "What does Lilian Weng say about the types of agent memory?"
MESSAGE1 = "In Oracle Database 23ai, how do I determine the accuracy of my vector indexes?"

thread_id = "default"
user_settings = next((settings for settings in settings_objects if settings.client == thread_id), None)
user_settings.rag.store_table = "TEXT_EMBEDDING_3_SMALL_8191_1639_COSINE"
user_settings.rag.model = "text-embedding-3-small"
user_settings.rag.rag_enabled = True

model_config = json.loads('{"model": "gpt-3.5-turbo"}')
ll_client = asyncio.run(models.get_client(model_objects=model_objects, model_config=model_config))
if user_settings.rag.rag_enabled:
    user_settings.prompts.sys = "RAG Example"
else:
    user_settings.prompts.sys = "Basic Example"
sys_prompt = next(
    (prompt for prompt in prompt_objects if prompt.category == "sys" and prompt.name == user_settings.prompts.sys),
    None,
)


embed_client, ctx_prompt, db_conn = None, None, None
if user_settings.rag.rag_enabled:
    model_config = user_settings.rag
    embed_client = asyncio.run(models.get_client(model_objects=model_objects, model_config=model_config.model_dump()))
    user_ctx_prompt = getattr(user_settings.prompts, "ctx", "Basic Example")
    ctx_prompt = next(
        (prompt for prompt in prompt_objects if prompt.category == "ctx" and prompt.name == user_ctx_prompt), None
    )
    user_db = getattr(model_config, "database", "DEFAULT")
    db_conn = next((settings.connection for settings in database_objects if settings.name == user_db), None)

kwargs = {
    "input": {"messages": [HumanMessage(content=MESSAGE0)]},
    "config": RunnableConfig(
        configurable={
            "thread_id": thread_id,
            "ll_client": ll_client,
            "embed_client": embed_client,
            "db_conn": db_conn,
        },
        metadata={
            "use_history": user_settings.ll_model.chat_history,
            "rag_settings": user_settings.rag,
            "sys_prompt": sys_prompt,
            "ctx_prompt": ctx_prompt,
        },
    ),
}

agent: CompiledStateGraph = chatbot.chatbot_graph
response = agent.invoke(**kwargs)
#print(response)

# state_snapshot = agent.get_state(
#     config=RunnableConfig(
#         configurable={
#             "thread_id": client,
#         }
#     )
# )
# messages: list[AnyMessage] = state_snapshot.values["messages"]
# chat_messages = convert_to_openai_messages(messages)
# print(chat_messages)
