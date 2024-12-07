"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore ainvoke, langgraph, modelcfg, jsonable

import copy
import json
from typing import Optional, Any, Tuple
from uuid import uuid4

from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage, convert_to_openai_messages
from langchain_core.runnables import RunnableConfig


import common.logging_config as logging_config
import common.schema as schema
import server.agents.chatbot as chatbot
import server.bootstrap as bootstrap  # __init__.py imports scripts
import server.models as models
import server.database as database

from fastapi import FastAPI, Query, HTTPException

logger = logging_config.logging.getLogger("server.endpoints")

# Load Models with Definition Data
model_objects = [schema.ModelModel(**model_dict) for model_dict in bootstrap.model_def.main()]
prompt_objects = [schema.PromptModel(**prompt_dict) for prompt_dict in bootstrap.prompt_eng_def.main()]
database_objects = [schema.DatabaseModel(**database_dict) for database_dict in bootstrap.database_def.main()]
settings_objects = [schema.Settings(**settings_dict) for settings_dict in bootstrap.settings_def.main()]


#####################################################
# Endpoints
#####################################################
def register_endpoints(app: FastAPI) -> None:
    logger.debug("Registering Server Endpoints")

    #################################################
    # Models
    #################################################
    @app.get("/v1/models", response_model=schema.ResponseList[schema.ModelModel])
    async def list_models(
        model_type: Optional[schema.ModelTypeType] = Query(None),
        enabled: Optional[schema.ModelEnabledType] = Query(None),
    ) -> schema.ResponseList[schema.ModelModel]:
        """List all models after applying filters if specified"""
        models_ret = await models.filter_models(model_objects, model_type=model_type, enabled=enabled)

        return schema.ResponseList[schema.ModelModel](data=models_ret)

    @app.get("/v1/models/{name}", response_model=schema.Response[schema.ModelModel])
    async def get_model(name: schema.ModelNameType) -> schema.Response[schema.ModelModel]:
        models_ret = await models.filter_models(model_objects, model_name=name)
        if not models_ret:
            raise HTTPException(status_code=404, detail=f"Model {name} not found")

        return schema.Response[schema.ModelModel](data=models_ret[0])

    @app.patch("/v1/models/{name}", response_model=schema.Response[schema.ModelModel])
    async def update_model(name: schema.ModelNameType, patch: dict[str, Any]) -> schema.Response[schema.ModelModel]:
        logger.debug("Received Model Payload: %s", patch)
        model_upd = await models.filter_models(model_objects, model_name=name)
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
    @app.get("/v1/prompts", response_model=schema.ResponseList[schema.PromptModel])
    async def list_prompts(
        category: Optional[schema.PromptCategoryType] = Query(None),
    ) -> schema.ResponseList[schema.PromptModel]:
        """List all prompts after applying filters if specified"""
        prompts_all = prompt_objects
        # Apply filtering if query parameters are provided
        if category is not None:
            logger.info("Filtering prompts on category: %s", category)
            prompts_all = [prompt for prompt in prompts_all if prompt.category == category]

        return schema.ResponseList[schema.PromptModel](data=prompts_all)

    @app.get("/v1/prompts/{category}/{name}", response_model=schema.Response[schema.Prompt])
    async def get_prompt(
        category: schema.PromptCategoryType, name: schema.PromptNameType
    ) -> schema.Response[schema.Prompt]:
        """Get a single Prompt"""
        prompt = next(
            (prompt for prompt in prompt_objects if prompt.category == category and prompt.name == name), None
        )
        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt {category}:{name} not found")

        return schema.Response[schema.Prompt](data=prompt)

    @app.patch("/v1/prompts/{category}/{name}", response_model=schema.Response[schema.PromptModel])
    async def update_prompt(
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
    def test_database(db_config: schema.DatabaseModel) -> Tuple[schema.Statuses, str]:
        err = None
        try:
            _ = database.connect(db_config, test=True)
            status = "ACTIVE"
        except database.oracledb.DatabaseError as ex:
            err = str(ex)
            status = "INACTIVE"
            if "ORA-01017" in err:
                status = "BAD_AUTH"
        return status, err

    def get_vector_stores(db_config: schema.DatabaseModel) -> list:
        """Retrieve Vector Storage Tables"""
        logger.info("Looking for Vector Storage Tables")
        sql = """SELECT ut.table_name, 
                        REPLACE(utc.comments, 'GENAI: ', '') AS comments
                   FROM all_tab_comments utc, all_tables ut
                  WHERE utc.table_name = ut.table_name
                    AND utc.comments LIKE 'GENAI:%'"""
        return database.execute_sql(db_config, sql)

    @app.get("/v1/databases", response_model=schema.ResponseList[schema.DatabaseModel])
    async def list_databases() -> schema.ResponseList[schema.DatabaseModel]:
        """List all databases"""
        databases_all = []
        for db in database_objects:
            status, _ = test_database(db)
            db.status = status
            if status == "ACTIVE":
                vector_stores = []
                results = get_vector_stores(db)
                for table_name, comments in results:
                    comments_dict = json.loads(comments)
                    vector_stores.append(schema.DatabaseVectorStorage(table=table_name, **comments_dict))
                db.vector_stores = vector_stores
            databases_all.append(db)
        return schema.ResponseList[schema.DatabaseModel](
            data=databases_all,
            msg=f"{len(databases_all)} database(s) configured",
        )

    @app.patch("/v1/databases/{name}", response_model=schema.Response[schema.DatabaseModel])
    async def update_database(
        name: schema.DatabaseNameType, patch: schema.Request[schema.Database]
    ) -> schema.Response[schema.DatabaseModel]:
        """Update Database"""
        logger.debug("Received Database Payload: %s", patch)
        for db in database_objects:
            if db.name == name:
                # Test the new configuration
                status, err = test_database(patch.data)
                if status == "ACTIVE":
                    # Update the database with the new configuration
                    db.user = patch.data.user
                    db.password = patch.data.password
                    db.dsn = patch.data.dsn
                    db.wallet_password = patch.data.wallet_password
                    return schema.Response[schema.DatabaseModel](data=db, msg="f{name} updated")
                else:
                    raise HTTPException(status_code=500, detail=err)
        raise HTTPException(status_code=404, detail=f"Database {name} not found")

    #################################################
    # Settings
    #################################################
    @app.get("/v1/settings/{client}", response_model=schema.Response[schema.Settings])
    async def get_client_settings(client: str) -> schema.Response[schema.Settings]:
        """Get settings for a specific client by name"""
        client_settings = next((settings for settings in settings_objects if client in settings.client), None)
        if not client_settings:
            raise HTTPException(status_code=404, detail="Client not found")

        return schema.Response[schema.Settings](data=client_settings)

    @app.post("/v1/settings", response_model=schema.Response[schema.Settings])
    def upload_client_settings(settings: schema.Settings):
        client = settings.client
        client_settings = next((settings for settings in settings_objects if settings.client == client), None)
        if client_settings:
            settings_objects.remove(client_settings)
        settings_objects.append(settings)

        return schema.Response[schema.Settings](data=settings)

    @app.post("/v1/settings/{client}", response_model=schema.Response[schema.Settings])
    async def create_client_settings(client: str) -> schema.Response[schema.Settings]:
        """Create new settings for a specific client"""
        if any(settings.client == client for settings in settings_objects):
            raise HTTPException(status_code=400, detail="Client already exists")

        default_settings = next((settings for settings in settings_objects if settings.client == "default"), None)

        # Copy the default settings
        new_settings = copy.deepcopy(default_settings)
        new_settings.client = client
        settings_objects.append(new_settings)

        return schema.Response(data=new_settings)

    #################################################
    # Chat Completions
    #################################################
    @app.post("/v1/chat/completions")
    async def chat(
        request: schema.ChatRequest,
        client: str = None,
    ) -> schema.ChatResponse:
        agent: CompiledStateGraph = chatbot.chatbot_graph

        thread_id = str(uuid4()) if not client else client
        llm = await models.get_model_client(model_objects, "ll", request)
        chat_history = request.chat_history

        # Convert the request to Langchain
        all_messages: AnyMessage = []
        human_message: HumanMessage = []
        for message in request.messages:
            try:
                msg_content = message.content[0]["text"]
            except TypeError:
                msg_content = message.content

            if message.role == "system":
                all_messages.append(SystemMessage(content=msg_content))
            else:
                human_message = [HumanMessage(content=msg_content)]

        all_messages.extend(human_message)
        kwargs = {
            "input": {"messages": all_messages},
            "config": RunnableConfig(
                configurable={
                    "thread_id": thread_id,
                    "model": llm,
                    "chat_history": chat_history,
                }
            ),
        }
        try:
            # ainvoke from langchain_core.language_models.BaseChatModel
            response = agent.invoke(**kwargs)["final_response"]
            return response
        except Exception as ex:
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

    @app.get("/v1/chat/history/{client}", response_model=schema.ResponseList[schema.ChatMessage])
    async def get_chat_history(client: str) -> schema.ResponseList[schema.ChatMessage]:
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
