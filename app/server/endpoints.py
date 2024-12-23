"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore ainvoke, langgraph, modelcfg, jsonable, genai, ocid, docos

import copy
import os
import shutil
from typing import Optional, Any
from pathlib import Path

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
import server.oci as server_oci
import server.embedding as embedding

from fastapi import FastAPI, Query, HTTPException, File, UploadFile

logger = logging_config.logging.getLogger("server.endpoints")

# Load Models with Definition Data
database_objects = bootstrap.database_def.main()
model_objects = bootstrap.model_def.main()
oci_objects = bootstrap.oci_def.main()
prompt_objects = bootstrap.prompt_eng_def.main()
settings_objects = bootstrap.settings_def.main()


#####################################################
# Endpoints
#####################################################
def register_endpoints(app: FastAPI) -> None:
    logger.debug("Registering Server Endpoints")

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
        logger.info("Received Database Payload: %s", patch)
        db = next((db for db in database_objects if db.name == name), None)
        if db:
            try:
                conn = databases.connect(patch.data)
            except databases.DbException as ex:
                db.connected = False
                raise HTTPException(status_code=500, detail=str(ex)) from ex
            db.user = patch.data.user
            db.password = patch.data.password
            db.dsn = patch.data.dsn
            db.wallet_password = patch.data.wallet_password
            db.connected = True
            db.vector_stores = databases.get_vs(conn)
            db.set_connection(conn)
            # Unset and disconnect other databases
            for other_db in database_objects:
                if other_db.name != name and other_db.connection:
                    other_db.set_connection(databases.disconnect(db.connection))
                    other_db.connected = False
            return schema.Response[schema.DatabaseModel](data=db, msg=f"{name} updated and set as default")
        raise HTTPException(status_code=404, detail=f"Database {name} not found")

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
    # OCI
    #################################################
    @app.get(
        "/v1/oci", description="View OCI Configuration", response_model=schema.ResponseList[schema.OracleCloudSettings]
    )
    async def oci_list() -> schema.ResponseList[schema.OracleCloudSettings]:
        """List OCI Configuration"""
        return schema.ResponseList[schema.OracleCloudSettings](data=oci_objects)

    @app.patch(
        "/v1/oci/{profile}",
        description="Update, Test, Set as Default OCI Configuration",
        response_model=schema.Response[schema.OracleCloudSettings],
    )
    async def oci_update(
        profile: schema.OCIProfileType, patch: schema.Request[schema.OracleCloudSettings]
    ) -> schema.Response[schema.OracleCloudSettings]:
        """Update OCI Configuration"""
        logger.debug("Received OCI Payload: %s", patch)
        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        if oci_config:
            try:
                namespace = server_oci.get_namespace(patch.data)
            except server_oci.OciException as ex:
                raise HTTPException(status_code=500, detail=str(ex)) from ex
            oci_config.namespace = namespace
            oci_config.tenancy = patch.data.tenancy
            oci_config.region = patch.data.region
            oci_config.user = patch.data.user
            oci_config.fingerprint = patch.data.fingerprint
            oci_config.key_file = patch.data.key_file
            oci_config.security_token_file = patch.data.security_token_file
            return schema.Response[schema.OracleCloudSettings](
                data=oci_config, msg=f"{profile} updated and set as default"
            )
        raise HTTPException(status_code=404, detail=f"{profile} profile for OCI not found")

    @app.get(
        "/v1/oci/compartments/{profile}",
        description="Get OCI Compartments",
        response_model=schema.Response[dict],
    )
    async def oci_list_compartments(profile: schema.OCIProfileType) -> schema.Response[dict]:
        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        compartments = server_oci.get_compartments(oci_config)
        return schema.Response[dict](data=compartments, msg=f"{len(compartments)} OCI compartments found")

    @app.get(
        "/v1/oci/buckets/{compartment}/{profile}",
        description="Get OCI Object Storage buckets in Compartment OCID",
        response_model=schema.Response[list],
    )
    async def oci_list_buckets(profile: schema.OCIProfileType, compartment: str) -> schema.Response[list]:
        # Validate OCID using Pydantic class
        compartment_obj = schema.OracleResource(ocid=compartment)
        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        buckets = server_oci.get_buckets(compartment_obj.ocid, oci_config)
        return schema.Response[list](data=buckets, msg=f"{len(buckets)} OCI buckets found")

    @app.get(
        "/v1/oci/bucket/objects/{bucket_name}/{profile}",
        description="Get OCI Object Storage buckets objects",
        response_model=schema.Response[list],
    )
    async def oci_list_bucket_objects(profile: schema.OCIProfileType, bucket_name: str) -> schema.Response[list]:
        # Validate OCID using Pydantic class
        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        objects = server_oci.get_bucket_objects(bucket_name, oci_config)
        return schema.Response[list](data=objects, msg=f"{len(objects)} bucket objects found")

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
    # Embedding
    #################################################
    @app.post(
        "/v1/embed/local/upload/{client}",
        description="Upload Local Files for Embedding.",
        response_model=schema.Response[list],
    )
    async def upload_local_file(client: str, file: UploadFile) -> schema.Response[list]:
        # Create a folder for the client if it doesn't exist
        logger.info("Received file: %s", file.filename)
        client_folder = Path(f"/tmp/{client}")
        client_folder.mkdir(parents=True, exist_ok=True)

        # Save the file temporarily
        temp_file_path = client_folder / file.filename
        file_content = await file.read()
        with temp_file_path.open("wb") as temp_file:
            temp_file.write(file_content)

        # Return a response that the file was uploaded successfully
        files = [f for f in os.listdir(client_folder) if os.path.isfile(os.path.join(client_folder, f))]
        return schema.Response[list](data=files, msg=f"{len(files)} uploaded")

    @app.post(
        "/v1/embed/{client}",
        description="Split and Embed Corpus.",
        response_model=schema.Response[list],
    )
    async def split_embed(
        client: str, request: schema.DatabaseVectorStorage, rate_limit: int = 0
    ) -> schema.Response[list]:
        client_folder = Path(f"/tmp/{client}")
        try:
            files = [str(file) for file in client_folder.iterdir() if file.is_file()]
            logger.info("Processing Files: %s", files)
        except FileNotFoundError as ex:
            raise HTTPException(status_code=404, detail=f"Client {client} documents folder not found") from ex
        try:
            split_docos, _ = embedding.load_and_split_documents(
                files,
                request.model,
                request.chunk_size,
                request.chunk_overlap,
                write_json=False,
                output_dir=None,
            )
            db = next((db for db in database_objects if db.name == request.database), None)
            embed_client = await models.get_client(model_objects, {"model": request.model, "rag_enabled": True})
            embedding.populate_vs(
                vector_store=request,
                db_conn=db.connection,
                embed_client=embed_client,
                input_data=split_docos,
                rate_limit=rate_limit,
            )
            return_files = list({doc.metadata["filename"] for doc in split_docos if "filename" in doc.metadata})
            return schema.Response[list](data=return_files, msg=f"{len(split_docos)} chunks embedded.")
        except Exception as ex:
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex
        finally:
            shutil.rmtree(client_folder)  # Clean up the temporary directory

    # @app.post("/v1/split/oci", description="Split files in OCI Object Storage.")
    # @app.post("/v1/split/web", description="Split Web Pages.")

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
        ll_client = await models.get_client(model_objects, request.model_dump())
        try:
            user_sys_prompt = getattr(user_settings.prompts, "sys", "Basic Example")
            sys_prompt = next(
                (prompt for prompt in prompt_objects if prompt.category == "sys" and prompt.name == user_sys_prompt),
                None,
            )
        except AttributeError as ex:
            # Settings not on server-side
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

        embed_client, ctx_prompt, db_conn = None, None, None
        if user_settings.rag.rag_enabled:
            rag_config = user_settings.rag
            embed_client = await models.get_client(model_objects, rag_config.model_dump())
            user_db = getattr(rag_config, "database", "DEFAULT")
            db_conn = next((settings.connection for settings in database_objects if settings.name == user_db), None)

            user_ctx_prompt = getattr(user_settings.prompts, "ctx", "Basic Example")
            ctx_prompt = next(
                (prompt for prompt in prompt_objects if prompt.category == "ctx" and prompt.name == user_ctx_prompt),
                None,
            )

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
