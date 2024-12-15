"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore ainvoke, langgraph, modelcfg, jsonable, genai

import copy
from typing import Optional, Any

from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage, AnyMessage, convert_to_openai_messages
from langchain_core.runnables import RunnableConfig


import common.logging_config as logging_config
import common.schema as schema
from common.functions import client_gen_id
import server.agents.chatbot as chatbot
import server.bootstrap as bootstrap  # __init__.py imports scripts
import server.models as models
import server.databases as databases

from fastapi import FastAPI, Query, HTTPException

logger = logging_config.logging.getLogger("server.endpoints")

# Load Models with Definition Data
model_objects = bootstrap.model_def.main()
prompt_objects = bootstrap.prompt_eng_def.main()
database_objects = bootstrap.database_def.main()
settings_objects = bootstrap.settings_def.main()


#####################################################
# Endpoints
#####################################################
def register_endpoints(app: FastAPI) -> None:
    logger.debug("Registering Server Endpoints")

    #################################################
    # Models
    #################################################
    @app.get("/v1/models", response_model=schema.ResponseList[schema.ModelModel])
    async def models_list(
        model_type: Optional[schema.ModelTypeType] = Query(None),
        enabled: Optional[schema.ModelEnabledType] = Query(None),
    ) -> schema.ResponseList[schema.ModelModel]:
        """List all models after applying filters if specified"""
        models_ret = await models.filter(model_objects, model_type=model_type, enabled=enabled)

        return schema.ResponseList[schema.ModelModel](data=models_ret)

    @app.get("/v1/models/{name}", response_model=schema.Response[schema.ModelModel])
    async def models_get(name: schema.ModelNameType) -> schema.Response[schema.ModelModel]:
        models_ret = await models.filter(model_objects, model_name=name)
        if not models_ret:
            raise HTTPException(status_code=404, detail=f"Model {name} not found")

        return schema.Response[schema.ModelModel](data=models_ret[0])

    @app.patch("/v1/models/{name}", response_model=schema.Response[schema.ModelModel])
    async def models_update(name: schema.ModelNameType, patch: dict[str, Any]) -> schema.Response[schema.ModelModel]:
        logger.debug("Received Model Payload: %s", patch)
        model_upd = await models.filter(model_objects, model_name=name)
        if not model_upd:
            raise HTTPException(status_code=404, detail=f"Model {name} not found")

        for key, value in patch.items():
            if hasattr(model_upd[0], key):
                setattr(model_upd[0], key, value)
            else:
                raise HTTPException(status_code=400, detail=f"Invalid key: {key}")

        return schema.Response[schema.ModelModel](data=model_upd[0])

    #################################################
    # Prompt Engineering
    #################################################
    @app.get(
        "/v1/prompts",
        description="Get all Prompt Configurations",
        response_model=schema.ResponseList[schema.PromptModel],
    )
    async def prompts_list(
        category: Optional[schema.PromptCategoryType] = Query(None),
    ) -> schema.ResponseList[schema.PromptModel]:
        """List all prompts after applying filters if specified"""
        prompts_all = prompt_objects
        # Apply filtering if query parameters are provided
        if category is not None:
            logger.info("Filtering prompts on category: %s", category)
            prompts_all = [prompt for prompt in prompts_all if prompt.category == category]

        return schema.ResponseList[schema.PromptModel](data=prompts_all)

    @app.get(
        "/v1/prompts/{category}/{name}",
        description="Get single Prompt Configuration",
        response_model=schema.Response[schema.Prompt],
    )
    async def prompts_get(
        category: schema.PromptCategoryType, name: schema.PromptNameType
    ) -> schema.Response[schema.Prompt]:
        """Get a single Prompt"""
        prompt = next(
            (prompt for prompt in prompt_objects if prompt.category == category and prompt.name == name), None
        )
        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt {category}:{name} not found")

        return schema.Response[schema.Prompt](data=prompt)

    @app.patch(
        "/v1/prompts/{category}/{name}",
        description="Update Prompt Configuration",
        response_model=schema.Response[schema.PromptModel],
    )
    async def prompts_update(
        category: schema.PromptCategoryType, name: schema.PromptNameType, patch: schema.Request[schema.Prompt]
    ) -> schema.Response[schema.PromptModel]:
        """Update a single Prompt"""
        logger.debug("Received %s (%s) Prompt Payload: %s", name, category, patch)
        for prompt in prompt_objects:
            if prompt.name == name and prompt.category == category:
                # Update the prompt with the new text
                prompt.prompt = patch.data.prompt
                return schema.Response[schema.PromptModel](data=prompt)

        raise HTTPException(status_code=404, detail=f"Prompt {category}:{name} not found")

    #################################################
    # Database
    #################################################
    @app.get(
        "/v1/databases",
        description="Get all Databases Configurations",
        response_model=schema.ResponseList[schema.DatabaseModel],
    )
    async def databases_list() -> schema.ResponseList[schema.DatabaseModel]:
        """List all databases"""
        return schema.ResponseList[schema.DatabaseModel](
            data=database_objects,
            msg=f"{len(database_objects)} database(s) found",
        )

    @app.get(
        "/v1/databases/{name}",
        description="Get single Database Configuration",
        response_model=schema.Response[schema.DatabaseModel],
    )
    async def databases_get(name: schema.DatabaseNameType) -> schema.ResponseList[schema.DatabaseModel]:
        """Get single db object"""
        db = next((db for db in database_objects if db.name == name), None)
        if not db:
            raise HTTPException(status_code=404, detail=f"Database {name} not found")

        return schema.Response[schema.DatabaseModel](
            data=db,
            msg=f"{name} database found",
        )

    @app.patch(
        "/v1/databases/{name}",
        description="Update, Test, Set as Default Database Configuration",
        response_model=schema.Response[schema.DatabaseModel],
    )
    async def databases_update(
        name: schema.DatabaseNameType, patch: schema.Request[schema.Database]
    ) -> schema.Response[schema.DatabaseModel]:
        """Update Database"""
        logger.debug("Received Database Payload: %s", patch)
        db = next((db for db in database_objects if db.name == name), None)
        if db:
            conn, status = databases.connect(db)
            if status == "VALID":
                db.user = patch.data.user
                db.password = patch.data.password
                db.dsn = patch.data.dsn
                db.wallet_password = patch.data.wallet_password
                db.vector_stores = databases.get_vs(conn)
                db.set_connection(conn)
                db.status = "CONNECTED"
                # Unset and disconnect other databases
                for other_db in database_objects:
                    if other_db.name != name and other_db.connection:
                        other_db.set_connection(databases.disconnect(db.connection))
                        other_db.status = "VALID"
                return schema.Response[schema.DatabaseModel](data=db, msg=f"{name} updated and set as default")
            else:
                raise HTTPException(status_code=404, detail=f"Unable to connect to database {name}: {status}")
        raise HTTPException(status_code=404, detail=f"Database {name} not found")

    #################################################
    # Settings
    #################################################
    @app.get("/v1/settings/{client}", response_model=schema.Response[schema.SettingsModel])
    async def settings_get(client: str) -> schema.Response[schema.SettingsModel]:
        """Get settings for a specific client by name"""
        client_settings = next((settings for settings in settings_objects if settings.client == client), None)
        if not client_settings:
            raise HTTPException(status_code=404, detail="Client not found")

        return schema.Response[schema.SettingsModel](data=client_settings)

    @app.patch("/v1/settings/{client}", response_model=schema.Response[schema.SettingsModel])
    async def settings_update(
        client: str, patch: schema.Request[schema.SettingsModel]
    ) -> schema.Response[schema.SettingsModel]:
        """Update a single Client Settings"""
        logger.debug("Received %s Client Payload: %s", client, patch)
        client_settings = next((settings for settings in settings_objects if settings.client == client), None)
        if client_settings:
            settings_objects.remove(client_settings)
            settings_objects.append(patch.data)
            return schema.Response[schema.SettingsModel](data=patch.data, msg=f"Client {client} settings updated")

        raise HTTPException(status_code=404, detail=f"Client {client} settings not found")

    @app.post("/v1/settings/{client}", response_model=schema.Response[schema.SettingsModel])
    async def settings_create(client: str) -> schema.Response[schema.SettingsModel]:
        """Create new settings for a specific client"""
        logger.debug("Received %s Client create request", client)
        if any(settings.client == client for settings in settings_objects):
            raise HTTPException(status_code=400, detail="Client already exists")

        default_settings = next((settings for settings in settings_objects if settings.client == "default"), None)

        # Copy the default settings
        settings = copy.deepcopy(default_settings)
        settings.client = client
        settings_objects.append(settings)

        return schema.Response(data=settings)

    #################################################
    # Chat Completions
    #################################################
    @app.post("/v1/chat/completions", description="Submit a message for completion.")
    async def chat_post(
        request: schema.ChatRequest,
        client: str = None,
    ) -> schema.ChatResponse:
        thread_id = client_gen_id() if not client else client
        user_settings = next((settings for settings in settings_objects if settings.client == thread_id), None)
        logger.info("User (%s) Settings: %s", thread_id, user_settings)
        # Establish LL Model Params
        ll_client = await models.get_client(model_objects, request)
        try:
            user_sys_prompt = getattr(user_settings.prompts, 'sys', "Basic Example")
            sys_prompt = next(
                (prompt for prompt in prompt_objects if prompt.category == "sys" and prompt.name == user_sys_prompt), None
            )
        except AttributeError as ex:
            # Settings not on server-side
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex
        
        embed_client, ctx_prompt, db_conn = None, None, None
        if user_settings.rag.rag_enabled:
            rag_config = user_settings.rag
            embed_client = await models.get_client(model_objects, rag_config)
            user_ctx_prompt = getattr(user_settings.prompts, "ctx", "Basic Example")
            ctx_prompt = next(
                (prompt for prompt in prompt_objects if prompt.category == "ctx" and prompt.name == user_ctx_prompt), None
            )
            user_db = getattr(rag_config, "database", "DEFAULT")
            db_conn = next((settings.connection for settings in database_objects if settings.name == user_db), None)

        kwargs = {
            "input": {"messages": [HumanMessage(content=request.messages[0].content)]},
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
        try:
            # invoke from langchain_core.language_models.BaseChatModel
            # output in OpenAI compatible format
            response = agent.invoke(**kwargs)["final_response"]
            return response
        except Exception as ex:
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

    @app.get(
        "/v1/chat/history/{client}",
        description="Get Chat History",
        response_model=schema.ResponseList[schema.ChatMessage],
    )
    async def chat_history_get(client: str) -> schema.ResponseList[schema.ChatMessage]:
        agent: CompiledStateGraph = chatbot.chatbot_graph
        try:
            state_snapshot = agent.get_state(
                config=RunnableConfig(
                    configurable={
                        "thread_id": client,
                    }
                )
            )
            messages: list[AnyMessage] = state_snapshot.values["messages"]
            chat_messages = convert_to_openai_messages(messages)
            return schema.ResponseList[schema.ChatMessage](data=chat_messages)
        except KeyError:
            return schema.ResponseList[schema.ChatMessage](
                data=[schema.ChatMessage(content="I'm sorry, I have no history of this conversation", role="system")]
            )
