"""
Copyright (c) 2024-2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore langgraph, ocid, docos, giskard, testsets, testset, noauth
# spell-checker:ignore astream, ainvoke, oaim, litellm

import asyncio
import json
import pickle
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
import shutil
from typing import AsyncGenerator, Literal, Optional
from pydantic import HttpUrl
import requests

from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage, AnyMessage, convert_to_openai_messages, ChatMessage
from langchain_core.runnables import RunnableConfig
from giskard.rag import evaluate, QATestset
from litellm import APIConnectionError

from fastapi import FastAPI, Query, HTTPException, UploadFile, Response
from fastapi.responses import StreamingResponse

import server.bootstrap as bootstrap
import server.utils.databases as databases
import server.utils.oci as server_oci
import server.utils.models as models
import server.utils.embedding as embedding
import server.utils.testbed as testbed
import server.agents.chatbot as chatbot

import common.schema as schema
import common.functions as functions
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.endpoints")


# Load Models with Definition Data
DATABASE_OBJECTS = bootstrap.database_def.main()
MODEL_OBJECTS = bootstrap.model_def.main()
OCI_OBJECTS = bootstrap.oci_def.main()
PROMPT_OBJECTS = bootstrap.prompt_eng_def.main()
SETTINGS_OBJECTS = bootstrap.settings_def.main()


#####################################################
# Helpers
#####################################################
def get_client_settings(client: schema.ClientIdType) -> schema.Settings:
    """Return schema.Settings Object based on client ID"""
    client_settings = next((settings for settings in SETTINGS_OBJECTS if settings.client == client), None)
    if not client_settings:
        raise HTTPException(status_code=404, detail=f"Client {client}: not found")
    return client_settings


def get_client_oci(client: schema.ClientIdType) -> schema.OracleCloudSettings:
    """Return schema.Settings Object based on client ID"""
    auth_profile = "DEFAULT"
    client_settings = get_client_settings(client)
    if client_settings.oci:
        auth_profile = getattr(client_settings.oci, "auth_profile", "DEFAULT")

    return next((oci for oci in OCI_OBJECTS if oci.auth_profile == auth_profile), None)


def get_client_db(client: schema.ClientIdType) -> schema.Database:
    """Return a schema.Database Object based on client settings"""
    db_name = "DEFAULT"
    client_settings = get_client_settings(client)
    if client_settings.rag:
        db_name = getattr(client_settings.rag, "database", "DEFAULT")
        db_obj = next((db for db in DATABASE_OBJECTS if db.name == db_name), None)
        # Refresh the connection if disconnected
        if db_obj:
            databases.test(db_obj)

    return db_obj


#####################################################
# Endpoints
#####################################################
def register_endpoints(noauth: FastAPI, auth: FastAPI) -> None:
    """Called by the server startup to load the endpoints"""

    #################################################
    # Kubernetes
    #################################################
    @noauth.get("/v1/liveness")
    async def liveness_probe():
        """Kubernetes liveness probe"""
        return {"status": "alive"}

    @noauth.get("/v1/readiness")
    async def readiness_probe():
        """Kubernetes ready probe"""
        return {"status": "ready"}

    #####################################################
    # databases Endpoints
    #####################################################
    @auth.get("/v1/databases", description="Get all database configurations", response_model=list[schema.Database])
    async def databases_list() -> list[schema.Database]:
        """List all databases"""
        for db in DATABASE_OBJECTS:
            logger.debug("Checking database: %s", db)
            try:
                db_conn = databases.connect(db)
            except databases.DbException:
                logger.debug("Unable to connect to database: %s", db)
                continue
            db.vector_stores = embedding.get_vs(db_conn)

        return DATABASE_OBJECTS

    @auth.get(
        "/v1/databases/{name}",
        description="Get single database configuration and vector storage",
        response_model=schema.Database,
    )
    async def databases_get(name: schema.DatabaseNameType) -> schema.Database:
        """Get single database"""
        db = next((db for db in DATABASE_OBJECTS if db.name == name), None)
        if not db:
            raise HTTPException(status_code=404, detail=f"schema.Database: {name} not found")

        db_conn = databases.connect(db)
        db.vector_stores = embedding.get_vs(db_conn)
        return db

    @auth.patch(
        "/v1/databases/{name}",
        description="Update, Test, Set as default database configuration",
    )
    async def databases_update(name: schema.DatabaseNameType, payload: schema.DatabaseAuth) -> Response:
        """Update schema.Database"""
        logger.debug("Received Database Payload: %s", payload)
        db = next((db for db in DATABASE_OBJECTS if db.name == name), None)
        if db:
            try:
                payload.config_dir = db.config_dir
                payload.wallet_location = db.wallet_location
                db_conn = databases.connect(payload)
            except databases.DbException as ex:
                db.connected = False
                logger.debug("Raising Exception: %s", str(ex))
                raise HTTPException(status_code=ex.status_code, detail=ex.detail) from ex
            db.user = payload.user
            db.password = payload.password
            db.dsn = payload.dsn
            db.wallet_password = payload.wallet_password
            db.connected = True
            db.vector_stores = embedding.get_vs(db_conn)
            db.set_connection(db_conn)
            # Unset and disconnect other databases
            for other_db in DATABASE_OBJECTS:
                if other_db.name != name and other_db.connection:
                    other_db.set_connection(databases.disconnect(db.connection))
                    other_db.connected = False
            return Response(status_code=204)
        raise HTTPException(status_code=404, detail=f"schema.Database: {name} not found")

    #################################################
    # embed Endpoints
    #################################################
    @auth.patch("/v1/embed/drop_vs", description="Drop Vector Store")
    async def embed_drop_vs(client: schema.ClientIdType, vs: schema.DatabaseVectorStorage) -> Response:
        """Drop Vector Storage"""
        embedding.drop_vs(get_client_db(client).connection, vs)
        return Response(status_code=204)

    @auth.post(
        "/v1/embed/web/store",
        description="Store Web Files for Embedding.",
    )
    async def store_web_file(client: schema.ClientIdType, request: list[HttpUrl]) -> Response:
        """Store contents from a web URL"""
        temp_directory = functions.get_temp_directory(client, "embedding")

        # Save the file temporarily
        for url in request:
            filename = Path(urlparse(str(url)).path).name
            response = requests.get(url, timeout=60)
            content_type = response.headers.get("Content-Type", "").lower()

            if "application/pdf" in content_type or "application/octet-stream" in content_type:
                with open(temp_directory / filename, "wb") as file:
                    file.write(response.content)
            elif "text" in content_type or "html" in content_type:
                with open(temp_directory / filename, "w", encoding="utf-8") as file:
                    file.write(response.text)
            else:
                shutil.rmtree(temp_directory)
                raise HTTPException(
                    status_code=500,
                    detail=f"Unprocessable content type: {content_type}",
                )

        stored_files = [f.name for f in temp_directory.iterdir() if f.is_file()]
        return Response(content=json.dumps(stored_files), media_type="application/json")

    @auth.post(
        "/v1/embed/local/store",
        description="Store Local Files for Embedding.",
    )
    async def store_local_file(client: schema.ClientIdType, files: list[UploadFile]) -> Response:
        """Store contents from a local file uploaded to streamlit"""
        temp_directory = functions.get_temp_directory(client, "embedding")
        for file in files:
            filename = temp_directory / file.filename
            file_content = await file.read()
            with filename.open("wb") as file:
                file.write(file_content)

        stored_files = [f.name for f in temp_directory.iterdir() if f.is_file()]
        return Response(content=json.dumps(stored_files), media_type="application/json")

    @auth.post(
        "/v1/embed",
        description="Split and Embed Corpus.",
    )
    async def split_embed(
        client: schema.ClientIdType,
        request: schema.DatabaseVectorStorage,
        rate_limit: int = 0,
    ) -> Response:
        """Perform Split and Embed"""
        oci_config = get_client_oci(client)
        temp_directory = functions.get_temp_directory(client, "embedding")

        try:
            files = [f for f in temp_directory.iterdir() if f.is_file()]
            logger.info("Processing Files: %s", files)
        except FileNotFoundError as ex:
            raise HTTPException(
                status_code=404,
                detail=f"Client {client} documents folder not found",
            ) from ex
        if not files:
            raise HTTPException(
                status_code=404,
                detail=f"No Files found in client {client} folder",
            )
        try:
            split_docos, _ = embedding.load_and_split_documents(
                files,
                request.model,
                request.chunk_size,
                request.chunk_overlap,
                write_json=False,
                output_dir=None,
            )
            embed_client = await models.get_client(
                MODEL_OBJECTS, {"model": request.model, "rag_enabled": True}, oci_config
            )
            embedding.populate_vs(
                vector_store=request,
                db_details=get_client_db(client),
                embed_client=embed_client,
                input_data=split_docos,
                rate_limit=rate_limit,
            )
            return Response(
                content=json.dumps({"message": f"{len(split_docos)} chunks embedded."}), media_type="application/json"
            )
        except ValueError as ex:
            raise HTTPException(status_code=500, detail=str(ex)) from ex
        except Exception as ex:
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex
        finally:
            shutil.rmtree(temp_directory)  # Clean up the temporary directory

    #################################################
    # models Endpoints
    #################################################
    @auth.get("/v1/models", description="Get all models", response_model=list[schema.Model])
    async def models_list(
        model_type: Optional[schema.ModelTypeType] = Query(None),
        only_enabled: bool = False,
    ) -> list[schema.Model]:
        """List all models after applying filters if specified"""
        models_ret = await models.apply_filter(MODEL_OBJECTS, model_type=model_type, only_enabled=only_enabled)

        return models_ret

    @auth.get("/v1/models/{name:path}", description="Get a single model", response_model=schema.Model)
    async def models_get(name: schema.ModelNameType) -> schema.Model:
        """List a specific model"""
        models_ret = await models.apply_filter(MODEL_OBJECTS, model_name=name)
        if not models_ret:
            raise HTTPException(status_code=404, detail=f"schema.Model {name}: not found")

        return models_ret[0]

    @auth.patch("/v1/models/update", description="Update a model")
    async def models_update(name: schema.ModelNameType, payload: schema.Model) -> Response:
        """Update a model"""
        logger.debug("Received model payload: %s", payload)
        model_upd = await models.apply_filter(MODEL_OBJECTS, model_name=name)
        if not model_upd:
            raise HTTPException(status_code=404, detail=f"Model {name}: not found")

        for key, value in payload:
            if hasattr(model_upd[0], key):
                setattr(model_upd[0], key, value)
            else:
                raise HTTPException(status_code=404, detail=f"Invalid model setting: {key}")

        return Response(status_code=204)

    @auth.patch("/v1/models/delete", description="Delete a model")
    async def models_delete(name: schema.ModelNameType) -> Response:
        """Update a model"""
        global MODEL_OBJECTS
        MODEL_OBJECTS = [model for model in MODEL_OBJECTS if model.name != name]

        return Response(status_code=204)

    @auth.post("/v1/models/create", description="Create a model", response_model=schema.Model)
    async def model_create(payload: schema.Model) -> schema.Model:
        """Update a model"""
        logger.debug("Received model payload: %s", payload)
        if payload.name == "new" or payload.api == "unknown":
            raise HTTPException(status_code=406, detail="Model name and API must be specified.")
        if payload.name in MODEL_OBJECTS:
            raise HTTPException(status_code=409, detail=f"Model {payload.name}: already exists.")
        openai_compat = next(
            (model_config.openai_compat for model_config in MODEL_OBJECTS if model_config.api == payload.api), False
        )
        payload.openai_compat = openai_compat
        MODEL_OBJECTS.append(payload)

        return payload

    #################################################
    # oci Endpoints
    #################################################
    @auth.get("/v1/oci", description="View OCI Configuration", response_model=list[schema.OracleCloudSettings])
    async def oci_list() -> list[schema.OracleCloudSettings]:
        """List OCI Configuration"""
        return OCI_OBJECTS

    @auth.get(
        "/v1/oci/compartments/{auth_profile}",
        description="Get OCI Compartments",
        response_model=dict,
    )
    async def oci_list_compartments(auth_profile: schema.OCIProfileType) -> dict:
        """Return a list of compartments"""
        oci_config = next((oci_config for oci_config in OCI_OBJECTS if oci_config.auth_profile == auth_profile), None)
        compartments = server_oci.get_compartments(oci_config)
        return compartments

    @auth.get(
        "/v1/oci/buckets/{compartment}/{auth_profile}",
        description="Get OCI Object Storage buckets in Compartment OCID",
        response_model=list,
    )
    async def oci_list_buckets(auth_profile: schema.OCIProfileType, compartment: str) -> list:
        """Return a list of buckets; Validate OCID using Pydantic class"""
        compartment_obj = schema.OracleResource(ocid=compartment)
        oci_config = next((oci_config for oci_config in OCI_OBJECTS if oci_config.auth_profile == auth_profile), None)
        buckets = server_oci.get_buckets(compartment_obj.ocid, oci_config)
        return buckets

    @auth.get(
        "/v1/oci/objects/{bucket_name}/{auth_profile}",
        description="Get OCI Object Storage buckets objects",
        response_model=list,
    )
    async def oci_list_bucket_objects(auth_profile: schema.OCIProfileType, bucket_name: str) -> list:
        """Return a list of bucket objects; Validate OCID using Pydantic class"""
        oci_config = next((oci_config for oci_config in OCI_OBJECTS if oci_config.auth_profile == auth_profile), None)
        objects = server_oci.get_bucket_objects(bucket_name, oci_config)
        return objects

    @auth.patch("/v1/oci/{auth_profile}", description="Update, Test, Set as Default OCI Configuration")
    async def oci_update(auth_profile: schema.OCIProfileType, payload: schema.OracleCloudSettings) -> Response:
        """Update OCI Configuration"""
        logger.debug("Received OCI Payload: %s", payload)
        oci_config = next((oci_config for oci_config in OCI_OBJECTS if oci_config.auth_profile == auth_profile), None)
        if oci_config:
            try:
                namespace = server_oci.get_namespace(payload)
            except server_oci.OciException as ex:
                raise HTTPException(status_code=401, detail=str(ex)) from ex
            oci_config.namespace = namespace
            oci_config.tenancy = payload.tenancy if payload.tenancy else oci_config.tenancy
            oci_config.region = payload.region if payload.region else oci_config.region
            oci_config.user = payload.user if payload.user else oci_config.user
            oci_config.fingerprint = payload.fingerprint if payload.fingerprint else oci_config.fingerprint
            oci_config.key_file = payload.key_file if payload.key_file else oci_config.key_file
            oci_config.security_token_file = (
                payload.security_token_file if payload.security_token_file else oci_config.security_token_file
            )
            # OCI GenAI
            try:
                oci_config.service_endpoint = (
                    payload.service_endpoint if payload.service_endpoint else oci_config.service_endpoint
                )
                oci_config.compartment_id = (
                    payload.compartment_id if payload.compartment_id else oci_config.compartment_id
                )
                if oci_config.service_endpoint != "" and oci_config.compartment_id != "":
                    for model in MODEL_OBJECTS:
                        if "OCI" in model.api:
                            model.enabled = True
                            model.url = oci_config.service_endpoint
            except AttributeError:
                pass
            return Response(status_code=204)

        raise HTTPException(status_code=404, detail=f"OCI Profile {auth_profile}: not found")

    @auth.post(
        "/v1/oci/objects/download/{bucket_name}/{auth_profile}",
        description="Download files from Object Storage",
    )
    async def oci_download_objects(
        client: schema.ClientIdType,
        bucket_name: str,
        auth_profile: schema.OCIProfileType,
        request: list[str],
    ) -> Response:
        """Download files from Object Storage"""
        # Files should be placed in the embedding folder
        temp_directory = functions.get_temp_directory(client, "embedding")
        oci_config = next((oci_config for oci_config in OCI_OBJECTS if oci_config.auth_profile == auth_profile), None)
        for object_name in request:
            server_oci.get_object(temp_directory, object_name, bucket_name, oci_config)

        downloaded_files = [f.name for f in temp_directory.iterdir() if f.is_file()]
        return Response(content=json.dumps(downloaded_files), media_type="application/json")

    #################################################
    # prompts Endpoints
    #################################################
    @auth.get(
        "/v1/prompts",
        description="Get all prompt configurations",
        response_model=list[schema.Prompt],
    )
    async def prompts_list(
        category: Optional[schema.PromptCategoryType] = Query(None),
    ) -> list[schema.Prompt]:
        """List all prompts after applying filters if specified"""
        prompts_all = PROMPT_OBJECTS
        # Apply filtering if query parameters are provided
        if category is not None:
            logger.info("Filtering prompts on category: %s", category)
            prompts_all = [prompt for prompt in PROMPT_OBJECTS if prompt.category == category]

        return prompts_all

    @auth.get(
        "/v1/prompts/{category}/{name}",
        description="Get single schema.Prompt Configuration",
        response_model=schema.Prompt,
    )
    async def prompts_get(category: schema.PromptCategoryType, name: schema.PromptNameType) -> schema.Prompt:
        """Get a single schema.Prompt"""
        prompt = next(
            (prompt for prompt in PROMPT_OBJECTS if prompt.category == category and prompt.name == name), None
        )
        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt {category}-{name}: not found")

        return prompt

    @auth.patch(
        "/v1/prompts/{category}/{name}",
        description="Update schema.Prompt Configuration",
    )
    async def prompts_update(
        category: schema.PromptCategoryType, name: schema.PromptNameType, payload: schema.PromptText
    ) -> Response:
        """Update a single schema.Prompt"""
        logger.debug("Received %s (%s) schema.Prompt Payload: %s", name, category, payload)
        for prompt in PROMPT_OBJECTS:
            if prompt.name == name and prompt.category == category:
                # Update the prompt with the new text
                prompt.prompt = payload.prompt

                return Response(status_code=204)

        raise HTTPException(status_code=404, detail=f"Prompt {category}:{name} not found")

    #################################################
    # settings Endpoints
    #################################################
    @auth.get("/v1/settings", description="Get client settings", response_model=schema.Settings)
    async def settings_get(client: schema.ClientIdType) -> schema.Settings:
        """Get settings for a specific client by name"""
        return get_client_settings(client)

    @auth.patch("/v1/settings", description="Update client settings")
    async def settings_update(client: schema.ClientIdType, payload: schema.Settings) -> Response:
        """Update a single client settings"""
        logger.debug("Received %s Client Payload: %s", client, payload)
        client_settings = get_client_settings(client)

        SETTINGS_OBJECTS.remove(client_settings)
        payload.client = client
        SETTINGS_OBJECTS.append(payload)

        return Response(status_code=204)

    @auth.post("/v1/settings", description="Create new client settings", response_model=schema.Settings)
    async def settings_create(client: schema.ClientIdType) -> schema.Settings:
        """Get settings for a specific client by name"""
        if any(settings.client == client for settings in SETTINGS_OBJECTS):
            raise HTTPException(status_code=400, detail=f"Client {client}: already exists")
        default_settings = next((settings for settings in SETTINGS_OBJECTS if settings.client == "default"), None)

        # Copy the default settings
        client_settings = schema.Settings(**default_settings.model_dump())
        client_settings.client = client
        SETTINGS_OBJECTS.append(client_settings)

        return client_settings

    #################################################
    # chat Endpoints
    #################################################
    async def completion_generator(
        client: schema.ClientIdType, request: schema.ChatRequest, call: Literal["completions", "streams"]
    ) -> AsyncGenerator[str, None]:
        """Generate a completion from agent, stream the results"""
        client_settings = get_client_settings(client)
        logger.debug("Settings: %s", client_settings)
        logger.debug("Request: %s", request.model_dump())

        # Establish LL schema.Model Params (if the request specs a model, otherwise override from settings)
        model = request.model_dump()
        if not model["model"]:
            model = client_settings.ll_model.model_dump()

        oci_config = get_client_oci(client)
        # Setup Client schema.Model
        ll_client = await models.get_client(MODEL_OBJECTS, model, oci_config)
        if not ll_client:
            yield "I'm sorry, I'm unable to initialise the Language Model.  Please refresh the application."
        # except Exception as ex:
        #     logger.error("An exception initializing model: %s", ex)
        #     raise HTTPException(status_code=500, detail="Unexpected error") from ex

        # Get Prompts
        try:
            user_sys_prompt = getattr(client_settings.prompts, "sys", "Basic Example")
            sys_prompt = next(
                (prompt for prompt in PROMPT_OBJECTS if prompt.category == "sys" and prompt.name == user_sys_prompt),
                None,
            )
        except AttributeError as ex:
            # schema.Settings not on server-side
            logger.error("A settings exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

        # Setup RAG
        embed_client, ctx_prompt, db_conn = None, None, None
        if client_settings.rag.rag_enabled:
            embed_client = await models.get_client(MODEL_OBJECTS, client_settings.rag.model_dump(), oci_config)

            user_ctx_prompt = getattr(client_settings.prompts, "ctx", "Basic Example")
            ctx_prompt = next(
                (prompt for prompt in PROMPT_OBJECTS if prompt.category == "ctx" and prompt.name == user_ctx_prompt),
                None,
            )
            db_conn = get_client_db(client).connection

        kwargs = {
            "input": {"messages": [HumanMessage(content=request.messages[0].content)]},
            "config": RunnableConfig(
                configurable={
                    "thread_id": client,
                    "ll_client": ll_client,
                    "embed_client": embed_client,
                    "db_conn": db_conn,
                },
                metadata={
                    "model_name": model["model"],
                    "use_history": client_settings.ll_model.chat_history,
                    "rag_settings": client_settings.rag,
                    "sys_prompt": sys_prompt,
                    "ctx_prompt": ctx_prompt,
                },
            ),
        }
        logger.debug("Completion Kwargs: %s", kwargs)
        agent: CompiledStateGraph = chatbot.chatbot_graph
        try:
            async for chunk in agent.astream_events(**kwargs, version="v2"):
                # The below will produce A LOT of output; uncomment when desperate
                # logger.debug("Streamed Chunk: %s", chunk)
                if chunk["event"] == "on_chat_model_stream":
                    if "tools_condition" in str(chunk["metadata"]["langgraph_triggers"]):
                        continue  # Skip Tool Call messages
                    if "vs_retrieve" in str(chunk["metadata"]["langgraph_node"]):
                        continue  # Skip Fake-Tool Call messages
                    content = chunk["data"]["chunk"].content
                    if content != "" and call == "streams":
                        yield content.encode("utf-8")
                last_response = chunk["data"]
            if call == "streams":
                yield "[stream_finished]"  # This will break the Chatbot loop
            elif call == "completions":
                final_response = last_response["output"]["final_response"]
                yield final_response  # This will be captured for ChatResponse
        except Exception as ex:
            logger.error("An invoke exception occurred: %s", ex)
            # yield f"I'm sorry; {ex}"
            # TODO(gotsysdba) - If a message is returned;
            # format and return (this should be done in the agent)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

    @auth.post(
        "/v1/chat/completions",
        description="Submit a message for full completion.",
        response_model=schema.ChatResponse,
    )
    async def chat_post(client: schema.ClientIdType, request: schema.ChatRequest) -> schema.ChatResponse:
        """Full Completion Requests"""
        last_message = None
        async for chunk in completion_generator(client, request, "completions"):
            last_message = chunk
        return last_message

    @auth.post(
        "/v1/chat/streams",
        description="Submit a message for streamed completion.",
        response_class=StreamingResponse,
        include_in_schema=False,
    )
    async def chat_stream(client: schema.ClientIdType, request: schema.ChatRequest) -> StreamingResponse:
        """Completion Requests"""
        return StreamingResponse(
            completion_generator(client, request, "streams"),
            media_type="application/octet-stream",
        )

    @auth.get(
        "/v1/chat/history",
        description="Get Chat History",
        response_model=list[schema.ChatMessage],
    )
    async def chat_history_get(client: schema.ClientIdType) -> list[ChatMessage]:
        """Return Chat History"""
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
            return chat_messages
        except KeyError:
            return [ChatMessage(content="I'm sorry, I have no history of this conversation", role="system")]

    #################################################
    # testbed Endpoints
    #################################################
    @auth.get("/v1/testbed/testsets", description="Get Stored TestSets.", response_model=list[schema.TestSets])
    async def testbed_get_testsets(client: schema.ClientIdType) -> list[schema.TestSets]:
        """Get a list of stored TestSets, create TestSet objects if they don't exist"""
        testsets = testbed.get_testsets(db_conn=get_client_db(client).connection)
        return testsets

    @auth.get("/v1/testbed/evaluations", description="Get Stored Evaluations.", response_model=list[schema.Evaluation])
    async def testbed_get_evaluations(
        client: schema.ClientIdType, tid: schema.TestSetsIdType
    ) -> list[schema.Evaluation]:
        """Get Evaluations"""
        evaluations = testbed.get_evaluations(db_conn=get_client_db(client).connection, tid=tid.upper())
        return evaluations

    @auth.get(
        "/v1/testbed/evaluation",
        description="Get Stored Single schema.Evaluation.",
        response_model=schema.EvaluationReport,
    )
    async def testbed_get_evaluation(
        client: schema.ClientIdType, eid: schema.TestSetsIdType
    ) -> schema.EvaluationReport:
        """Get Evaluations"""
        evaluation = testbed.process_report(db_conn=get_client_db(client).connection, eid=eid.upper())
        return evaluation

    @auth.get("/v1/testbed/testset_qa", description="Get Stored schema.TestSets Q&A.", response_model=schema.TestSetQA)
    async def testbed_get_testset_qa(client: schema.ClientIdType, tid: schema.TestSetsIdType) -> schema.TestSetQA:
        """Get TestSet Q&A"""
        return testbed.get_testset_qa(db_conn=get_client_db(client).connection, tid=tid.upper())

    @auth.post("/v1/testbed/testset_load", description="Upsert TestSets.", response_model=schema.TestSetQA)
    async def testbed_upsert_testsets(
        client: schema.ClientIdType,
        files: list[UploadFile],
        name: schema.TestSetsNameType,
        tid: Optional[schema.TestSetsIdType] = None,
    ) -> schema.TestSetQA:
        """Update stored TestSet data"""
        created = datetime.now().isoformat()
        db_conn = get_client_db(client).connection
        try:
            for file in files:
                file_content = await file.read()
                content = testbed.jsonl_to_json_content(file_content)
                db_id = testbed.upsert_qa(db_conn, name, created, content, tid)
            db_conn.commit()
        except Exception as ex:
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

        testset_qa = await testbed_get_testset_qa(client=client, tid=db_id)
        return testset_qa

    @auth.post("/v1/testbed/testset_generate", description="Generate Q&A Test Set.", response_model=schema.TestSetQA)
    async def testbed_generate_qa(
        client: schema.ClientIdType,
        files: list[UploadFile],
        name: schema.TestSetsNameType,
        ll_model: schema.ModelNameType = None,
        embed_model: schema.ModelNameType = None,
        questions: int = 2,
    ) -> schema.TestSetQA:
        """Retrieve contents from a local file uploaded and generate Q&A"""
        # Setup Models
        giskard_ll_model = await models.apply_filter(
            MODEL_OBJECTS,
            model_name=ll_model,
            model_type="ll",
            only_enabled=True,
        )
        giskard_embed_model = await models.apply_filter(
            MODEL_OBJECTS,
            model_name=embed_model,
            model_type="embed",
            only_enabled=True,
        )
        temp_directory = functions.get_temp_directory(client, "testbed")
        full_testsets = temp_directory / "all_testsets.jsonl"

        for file in files:
            try:
                # Read and save file content
                file_content = await file.read()
                filename = temp_directory / file.filename
                logger.info("Writing Q&A File to: %s", filename)
                with open(filename, "wb") as file:
                    file.write(file_content)

                # Process file for knowledge base
                text_nodes = testbed.load_and_split(filename)
                test_set = testbed.build_knowledge_base(
                    text_nodes, questions, giskard_ll_model[0], giskard_embed_model[0]
                )
                # Save test set
                test_set_filename = temp_directory / f"{name}.jsonl"
                test_set.save(test_set_filename)
                with (
                    open(test_set_filename, "r", encoding="utf-8") as source,
                    open(full_testsets, "a", encoding="utf-8") as destination,
                ):
                    destination.write(source.read())
            except APIConnectionError as ex:
                shutil.rmtree(temp_directory)
                logger.error("APIConnectionError Exception: %s", str(ex))
                raise HTTPException(status_code=424, detail=str(ex)) from ex
            except Exception as ex:
                shutil.rmtree(temp_directory)
                logger.error("Unknown TestSet Exception: %s", str(ex))
                raise HTTPException(status_code=500, detail=f"Unexpected testset error: {str(ex)}") from ex

            # Store tests in database
            with open(full_testsets, "rb") as file:
                upload_file = UploadFile(file=file, filename=full_testsets)
                testset_qa = await testbed_upsert_testsets(client=client, files=[upload_file], name=name)
            shutil.rmtree(temp_directory)

        return testset_qa

    @auth.post(
        "/v1/testbed/evaluate",
        description="Evaluate Q&A Test Set.",
        response_model=schema.EvaluationReport,
    )
    def testbed_evaluate_qa(
        client: schema.ClientIdType, tid: schema.TestSetsIdType, judge: schema.ModelNameType
    ) -> schema.EvaluationReport:
        """Run evaluate against a testset"""

        def get_answer(question: str):
            """Submit question against the chatbot"""
            request = schema.ChatRequest(
                messages=[ChatMessage(role="human", content=question)],
            )
            ai_response = asyncio.run(chat_post(client=client, request=request))
            return ai_response.choices[0].message.content

        evaluated = datetime.now().isoformat()
        client_settings = get_client_settings(client)
        # Change Disable History
        client_settings.ll_model.chat_history = False
        # Change Grade RAG
        client_settings.rag.grading = False

        db_conn = get_client_db(client).connection
        testset = testbed.get_testset_qa(db_conn=db_conn, tid=tid.upper())
        qa_test = "\n".join(json.dumps(item) for item in testset.qa_data)
        temp_directory = functions.get_temp_directory(client, "testbed")

        with open(temp_directory / f"{tid}_output.txt", "w", encoding="utf-8") as file:
            file.write(qa_test)
        loaded_testset = QATestset.load(temp_directory / f"{tid}_output.txt")

        # Setup Judge Model
        logger.debug("Starting evaluation with Judge: %s", judge)
        oci_config = get_client_oci(client)
        judge_client = asyncio.run(models.get_client(MODEL_OBJECTS, {"model": judge}, oci_config, True))
        report = evaluate(get_answer, testset=loaded_testset, llm_client=judge_client)

        eid = testbed.insert_evaluation(
            db_conn=db_conn,
            tid=tid,
            evaluated=evaluated,
            correctness=report.correctness,
            settings=client_settings.model_dump_json(),
            rag_report=pickle.dumps(report),
        )
        db_conn.commit()
        shutil.rmtree(temp_directory)

        return testbed.process_report(db_conn=db_conn, eid=eid)

    logger.info("Endpoints Loaded.")
