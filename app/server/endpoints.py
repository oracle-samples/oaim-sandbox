"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore ainvoke, langgraph, modelcfg, jsonable, genai, ocid, docos, ollama, giskard, testsets, testset, noauth

import copy
import os
import shutil
import tempfile
import json
import asyncio
import pickle


from datetime import datetime
from typing import Optional
from pathlib import Path

import requests

from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage, AnyMessage, convert_to_openai_messages, ChatMessage
from langchain_core.runnables import RunnableConfig
from giskard.rag import evaluate, QATestset

import common.logging_config as logging_config
import common.schema as schema
from common.functions import client_gen_id, get_temp_directory
import server.agents.chatbot as chatbot
import server.bootstrap as bootstrap  # __init__.py imports scripts
import server.models as models
import server.databases as databases
import server.oci as server_oci
import server.embedding as embedding
import server.testbed as testbed

from fastapi import FastAPI, Query, HTTPException, UploadFile, Response

logger = logging_config.logging.getLogger("server.endpoints")

# Load Models with Definition Data
database_objects = bootstrap.database_def.main()
model_objects = bootstrap.model_def.main()
oci_objects = bootstrap.oci_def.main()
prompt_objects = bootstrap.prompt_eng_def.main()
settings_objects = bootstrap.settings_def.main()


#####################################################
# Helpers
#####################################################
def get_db_conn(db_name: str = "DEFAULT"):
    return next((db.connection for db in database_objects if db.name == db_name), None)


#####################################################
# Endpoints
#####################################################
def register_endpoints(noauth: FastAPI, auth: FastAPI) -> None:
    """Called by the server startup to load the endpoints"""

    #################################################
    # Kubernetes
    #################################################
    @noauth.get("/v1/liveness")
    async def liveness_probe(response: Response):
        response.status_code = 200
        return {"status": "alive"}

    @noauth.get("/v1/readiness")
    async def readiness_probe(response: Response):
        response.status_code = 200
        return {"status": "ready"}

    #################################################
    # Database
    #################################################
    @auth.get(
        "/v1/databases",
        description="Get all Databases Configurations",
        response_model=schema.ResponseList[schema.Database],
    )
    async def databases_list() -> schema.ResponseList[schema.Database]:
        """List all databases without gathering VectorStorage"""
        for db in database_objects:
            logger.info("Checking database: %s", db)
            try:
                db_conn = databases.connect(db)
            except databases.DbException:
                continue
            db.vector_stores = embedding.get_vs(db_conn)
        return schema.ResponseList[schema.Database](
            data=database_objects,
            msg=f"{len(database_objects)} database(s) found",
        )

    @auth.get(
        "/v1/databases/{name}",
        description="Get single Database Configuration and Vector Storage",
        response_model=schema.Response[schema.Database],
    )
    async def databases_get(name: schema.DatabaseNameType) -> schema.ResponseList[schema.Database]:
        """Get single db object"""
        db = next((db for db in database_objects if db.name == name), None)
        if not db:
            raise HTTPException(status_code=404, detail=f"Database {name} not found")

        db_conn = databases.connect(db)
        db.vector_stores = embedding.get_vs(db_conn)
        return schema.Response[schema.Database](
            data=db,
            msg=f"{name} database found",
        )

    @auth.patch(
        "/v1/databases/{name}",
        description="Update, Test, Set as Default Database Configuration",
        response_model=schema.Response[schema.DatabaseModel],
    )
    async def databases_update(
        name: schema.DatabaseNameType, payload: schema.DatabaseModel
    ) -> schema.Response[schema.Database]:
        """Update Database"""
        logger.info("Received Database Payload: %s", payload)
        db = next((db for db in database_objects if db.name == name), None)
        if db:
            try:
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
            for other_db in database_objects:
                if other_db.name != name and other_db.connection:
                    other_db.set_connection(databases.disconnect(db.connection))
                    other_db.connected = False
            return schema.Response[schema.Database](data=db, msg=f"{name} updated and set as default")
        raise HTTPException(status_code=404, detail=f"Database {name} not found")

    #################################################
    # Models
    #################################################
    @auth.get("/v1/models", response_model=schema.ResponseList[schema.Model])
    async def models_list(
        model_type: Optional[schema.ModelTypeType] = Query(None),
        only_enabled: bool = False,
    ) -> schema.ResponseList[schema.Model]:
        """List all models after applying filters if specified"""
        models_ret = await models.apply_filter(model_objects, model_type=model_type, only_enabled=only_enabled)

        return schema.ResponseList[schema.Model](data=models_ret)

    @auth.get("/v1/models/{name}", response_model=schema.Response[schema.Model])
    async def models_get(name: schema.ModelNameType) -> schema.Response[schema.Model]:
        """List a specific model"""
        models_ret = await models.apply_filter(model_objects, model_name=name)
        if not models_ret:
            raise HTTPException(status_code=404, detail=f"Model {name} not found")

        return schema.Response[schema.Model](data=models_ret[0])

    @auth.patch("/v1/models/{name}", response_model=schema.Response[schema.Model])
    async def models_update(name: schema.ModelNameType, payload: schema.ModelModel) -> schema.Response[schema.Model]:
        """Update a model"""
        logger.debug("Received Model Payload: %s", payload)
        model_upd = await models.apply_filter(model_objects, model_name=name)
        if not model_upd:
            raise HTTPException(status_code=404, detail=f"Model {name} not found")

        for key, value in payload:
            if hasattr(model_upd[0], key):
                setattr(model_upd[0], key, value)
            else:
                raise HTTPException(status_code=400, detail=f"Invalid key: {key}")

        return schema.Response[schema.Model](data=model_upd[0])

    #################################################
    # OCI
    #################################################
    @auth.get(
        "/v1/oci", description="View OCI Configuration", response_model=schema.ResponseList[schema.OracleCloudSettings]
    )
    async def oci_list() -> schema.ResponseList[schema.OracleCloudSettings]:
        """List OCI Configuration"""
        return schema.ResponseList[schema.OracleCloudSettings](
            data=oci_objects, msg=f"{len(oci_objects)} OCI Configurations found"
        )

    @auth.get(
        "/v1/oci/compartments/{profile}",
        description="Get OCI Compartments",
        response_model=schema.Response[dict],
    )
    async def oci_list_compartments(profile: schema.OCIProfileType) -> schema.Response[dict]:
        """Return a list of compartments"""
        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        compartments = server_oci.get_compartments(oci_config)
        return schema.Response[dict](data=compartments, msg=f"{len(compartments)} OCI compartments found")

    @auth.get(
        "/v1/oci/buckets/{compartment}/{profile}",
        description="Get OCI Object Storage buckets in Compartment OCID",
        response_model=schema.Response[list],
    )
    async def oci_list_buckets(profile: schema.OCIProfileType, compartment: str) -> schema.Response[list]:
        """Return a list of buckets; Validate OCID using Pydantic class"""
        compartment_obj = schema.OracleResource(ocid=compartment)
        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        buckets = server_oci.get_buckets(compartment_obj.ocid, oci_config)
        return schema.Response[list](data=buckets, msg=f"{len(buckets)} OCI buckets found")

    @auth.get(
        "/v1/oci/objects/{bucket_name}/{profile}",
        description="Get OCI Object Storage buckets objects",
        response_model=schema.Response[list],
    )
    async def oci_list_bucket_objects(profile: schema.OCIProfileType, bucket_name: str) -> schema.Response[list]:
        """Return a list of bucket objects; Validate OCID using Pydantic class"""
        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        objects = server_oci.get_bucket_objects(bucket_name, oci_config)
        return schema.Response[list](data=objects, msg=f"{len(objects)} bucket objects found")

    @auth.patch(
        "/v1/oci/{profile}",
        description="Update, Test, Set as Default OCI Configuration",
        response_model=schema.Response[schema.OracleCloudSettings],
    )
    async def oci_update(
        profile: schema.OCIProfileType, payload: schema.OracleCloudSettings
    ) -> schema.Response[schema.OracleCloudSettings]:
        """Update OCI Configuration"""
        logger.debug("Received OCI Payload: %s", payload)
        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        if oci_config:
            try:
                namespace = server_oci.get_namespace(payload)
            except server_oci.OciException as ex:
                raise HTTPException(status_code=401, detail=str(ex)) from ex
            oci_config.namespace = namespace
            oci_config.tenancy = payload.tenancy
            oci_config.region = payload.region
            oci_config.user = payload.user
            oci_config.fingerprint = payload.fingerprint
            oci_config.key_file = payload.key_file
            oci_config.security_token_file = payload.security_token_file
            return schema.Response[schema.OracleCloudSettings](
                data=oci_config, msg=f"{profile} updated and set as default"
            )
        raise HTTPException(status_code=404, detail=f"{profile} profile for OCI not found")

    @auth.post(
        "/v1/oci/objects/download/{bucket_name}/{profile}",
        description="Download files from Object Storage",
        response_model=schema.Response[list],
    )
    async def oci_download_objects(
        bucket_name: str,
        profile: schema.OCIProfileType,
        request: list[str],
        client: str = "server",
        directory: str = "docs",
    ) -> schema.Response[list]:
        """Download files from Object Storage"""
        temp_directory = get_temp_directory()
        client_folder = Path(temp_directory) / client / directory
        client_folder.mkdir(parents=True, exist_ok=True)

        oci_config = next((oci_config for oci_config in oci_objects if oci_config.profile == profile), None)
        for object_name in request:
            server_oci.get_object(client_folder, object_name, bucket_name, oci_config)

        # Return a response that the object was downloaded successfully
        dir_files = [f for f in os.listdir(client_folder) if os.path.isfile(os.path.join(client_folder, f))]
        return schema.Response[list](data=dir_files, msg=f"{len(dir_files)} objects downloaded")

    #################################################
    # Prompt Engineering
    #################################################
    @auth.get(
        "/v1/prompts",
        description="Get all Prompt Configurations",
        response_model=schema.ResponseList[schema.Prompt],
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

        return schema.ResponseList[schema.Prompt](data=prompts_all, msg=f"{len(prompts_all)} Prompts found")

    @auth.get(
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

        return schema.Response[schema.Prompt](data=prompt, msg=f"Prompt {category}:{name} found")

    @auth.patch(
        "/v1/prompts/{category}/{name}",
        description="Update Prompt Configuration",
        response_model=schema.Response[schema.Prompt],
    )
    async def prompts_update(
        category: schema.PromptCategoryType, name: schema.PromptNameType, payload: schema.PromptModel
    ) -> schema.Response[schema.Prompt]:
        """Update a single Prompt"""
        logger.debug("Received %s (%s) Prompt Payload: %s", name, category, payload)
        for prompt in prompt_objects:
            if prompt.name == name and prompt.category == category:
                # Update the prompt with the new text
                prompt.prompt = payload.prompt
                return schema.Response[schema.Prompt](data=prompt, msg=f"Prompt {category}:{name} updated")

        raise HTTPException(status_code=404, detail=f"Prompt {category}:{name} not found")

    #################################################
    # Settings
    #################################################
    @auth.get("/v1/settings", response_model=schema.Response[schema.Settings])
    async def settings_get(client: str = "server") -> schema.Response[schema.Settings]:
        """Get settings for a specific client by name"""
        client_settings = next((settings for settings in settings_objects if settings.client == client), None)
        if not client_settings:
            raise HTTPException(status_code=404, detail=f"Client {client} not found")

        return schema.Response[schema.Settings](data=client_settings, msg=f"Client {client} found")

    @auth.patch("/v1/settings", response_model=schema.Response[schema.Settings])
    async def settings_update(payload: schema.Settings, client: str = "server") -> schema.Response[schema.Settings]:
        """Update a single Client Settings"""
        logger.debug("Received %s Client Payload: %s", client, payload)
        client_settings = next((settings for settings in settings_objects if settings.client == client), None)
        if client_settings:
            settings_objects.remove(client_settings)
            payload.client = client
            settings_objects.append(payload)
            return schema.Response[schema.Settings](data=payload, msg=f"Client {client} settings updated")

        raise HTTPException(status_code=404, detail=f"Client {client} settings not found")

    @auth.post("/v1/settings", response_model=schema.Response[schema.Settings])
    async def settings_create(client: str = "server") -> schema.Response[schema.Settings]:
        """Create new settings for a specific client"""
        logger.debug("Received %s Client create request", client)
        if any(settings.client == client for settings in settings_objects):
            raise HTTPException(status_code=400, detail=f"Client {client} already exists")

        default_settings = next((settings for settings in settings_objects if settings.client == "default"), None)

        # Copy the default settings
        settings = copy.deepcopy(default_settings)
        settings.client = client
        settings_objects.append(settings)

        return schema.Response(data=settings, msg=f"Client {client} settings created")

    #################################################
    # Embedding
    #################################################
    @auth.post(
        "/v1/embed/drop_vs",
        description="Drop Vector Store",
        response_model=schema.Response[str],
    )
    async def embed_drop_vs(vs: schema.DatabaseVectorStorage) -> schema.Response[str]:
        """Drop Vector Storage"""
        embedding.drop_vs(get_db_conn(), vs)

        return schema.Response[str](data=vs.vector_store, msg="Vector Store Dropped")

    @auth.post(
        "/v1/embed/web/store",
        description="Store Web Files for Embedding.",
        response_model=schema.Response[list],
    )
    async def store_web_file(
        request: list[str], client: str = "server", directory: str = "docs"
    ) -> schema.Response[list]:
        """Store contents from a web URL"""
        temp_directory = get_temp_directory()
        client_folder = Path(temp_directory) / client / directory
        client_folder.mkdir(parents=True, exist_ok=True)

        # Save the file temporarily
        for url in request:
            filename = client_folder / os.path.basename(url)
            response = requests.get(url, timeout=60)
            content_type = response.headers.get("Content-Type", "").lower()

            if "application/pdf" in content_type or "application/octet-stream" in content_type:
                with open(filename, "wb") as file:
                    file.write(response.content)
            elif "text" in content_type or "html" in content_type:
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(response.text)
            else:
                raise HTTPException(status_code=500, detail=f"Unprocessable content type: {content_type}")

        # Return a response that the file was stored successfully
        files = [f for f in os.listdir(client_folder) if os.path.isfile(os.path.join(client_folder, f))]
        return schema.Response[list](data=files, msg=f"{len(files)} stored")

    @auth.post(
        "/v1/embed/local/store",
        description="Store Local Files for Embedding.",
        response_model=schema.Response[list],
    )
    async def store_local_file(
        files: list[UploadFile], client: str = "server", directory: str = "docs"
    ) -> schema.Response[list]:
        """Store contents from a local file uploaded to streamlit"""
        temp_directory = get_temp_directory()
        client_folder = Path(temp_directory) / client / directory
        client_folder.mkdir(parents=True, exist_ok=True)

        # Save the file temporarily
        for file in files:
            filename = client_folder / file.filename
            file_content = await file.read()
            with filename.open("wb") as temp_file:
                temp_file.write(file_content)

        # Return a response that the file was uploaded successfully
        files = [f for f in os.listdir(client_folder) if os.path.isfile(os.path.join(client_folder, f))]
        return schema.Response[list](data=files, msg=f"{len(files)} stored")

    @auth.post(
        "/v1/embed",
        description="Split and Embed Corpus.",
        response_model=schema.Response[list],
    )
    async def split_embed(
        request: schema.DatabaseVectorStorage, client: str = "server", directory: str = "docs", rate_limit: int = 0
    ) -> schema.Response[list]:
        """Perform Split and Embed"""
        temp_directory = get_temp_directory()
        client_folder = Path(temp_directory) / client / directory
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
            embed_client = await models.get_client(model_objects, {"model": request.model, "rag_enabled": True})
            embedding.populate_vs(
                vector_store=request,
                db_conn=get_db_conn(),
                embed_client=embed_client,
                input_data=split_docos,
                rate_limit=rate_limit,
            )
            return_files = list({doc.metadata["filename"] for doc in split_docos if "filename" in doc.metadata})
            return schema.Response[list](data=return_files, msg=f"{len(split_docos)} chunks embedded.")
        except ValueError as ex:
            raise HTTPException(status_code=500, detail=str(ex)) from ex
        except Exception as ex:
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex
        finally:
            shutil.rmtree(client_folder)  # Clean up the temporary directory

    #################################################
    # Chat Completions
    #################################################
    @auth.post("/v1/chat/completions", description="Submit a message for completion.")
    async def chat_post(
        request: schema.ChatRequest,
        client: str = None,
    ) -> schema.ChatResponse:
        """Chatbot Completion"""
        thread_id = client_gen_id() if not client else client
        user_settings = next((settings for settings in settings_objects if settings.client == thread_id), None)
        logger.debug("Settings: %s", user_settings)
        logger.debug("Request: %s", request.model_dump())
        # Establish LL Model Params (if the request specs a model, otherwise override from settings)
        model = request.model_dump()
        if not model["model"]:
            model = user_settings.ll_model.model_dump()
        logger.debug("Model: %s", model)
        try:
            ll_client = await models.get_client(model_objects, model)
        except Exception as ex:
            logger.error("An exception initializing model: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

        try:
            user_sys_prompt = getattr(user_settings.prompts, "sys", "Basic Example")
            sys_prompt = next(
                (prompt for prompt in prompt_objects if prompt.category == "sys" and prompt.name == user_sys_prompt),
                None,
            )
        except AttributeError as ex:
            # Settings not on server-side
            logger.error("A settings exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

        embed_client, ctx_prompt, user_db = None, None, None
        if user_settings.rag.rag_enabled:
            rag_config = user_settings.rag
            embed_client = await models.get_client(model_objects, rag_config.model_dump())
            user_db = getattr(rag_config, "database", "DEFAULT")

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
                    "db_conn": get_db_conn(db_name=user_db),
                },
                metadata={
                    "model_name": model["model"],
                    "use_history": user_settings.ll_model.chat_history,
                    "rag_settings": user_settings.rag,
                    "sys_prompt": sys_prompt,
                    "ctx_prompt": ctx_prompt,
                },
            ),
        }
        logger.info("Completion Kwargs: %s", kwargs)
        agent: CompiledStateGraph = chatbot.chatbot_graph
        try:
            # invoke from langchain_core.language_models.BaseChatModel
            # output in OpenAI compatible format
            response = agent.invoke(**kwargs)["final_response"]
            return response
        except Exception as ex:
            logger.error("An invoke exception occurred: %s", ex)
            # TODO: gotsysdba - If a message is returned; attempt to format and return (this might be done in the agent instead)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

    @auth.get(
        "/v1/chat/history",
        description="Get Chat History",
        response_model=schema.ResponseList[schema.ChatMessage],
    )
    async def chat_history_get(client: str = "server") -> schema.ResponseList[schema.ChatMessage]:
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
            return schema.ResponseList[schema.ChatMessage](data=chat_messages)
        except KeyError:
            return schema.ResponseList[schema.ChatMessage](
                data=[schema.ChatMessage(content="I'm sorry, I have no history of this conversation", role="system")]
            )

    #################################################
    # Testbed
    #################################################
    @auth.get(
        "/v1/testbed/testsets",
        description="Get Stored TestSets.",
        response_model=schema.ResponseList[schema.TestSets],
    )
    async def testbed_get_testsets() -> schema.Response[schema.TestSets]:
        """Get a list of stored TestSets, create TestSet objects if they don't exist"""
        testsets = testbed.get_testsets(db_conn=get_db_conn())
        return schema.ResponseList[schema.TestSets](
            data=testsets,
            msg=f"{len(testsets)} TestSet(s) found",
        )

    @auth.get(
        "/v1/testbed/evaluations",
        description="Get Stored Evaluations.",
        response_model=schema.ResponseList[schema.Evaluation],
    )
    async def testbed_get_evaluations(tid: schema.TestSetsIdType) -> schema.ResponseList[schema.Evaluation]:
        """Get Evaluations"""
        evaluations = testbed.get_evaluations(db_conn=get_db_conn(), tid=tid.upper())
        return schema.ResponseList[schema.Evaluation](
            data=evaluations,
            msg=f"{len(evaluations)} Evaluation(s) found.",
        )

    @auth.get(
        "/v1/testbed/evaluation",
        description="Get Stored Single Evaluation.",
        response_model=schema.Response[schema.EvaluationReport],
    )
    async def testbed_get_evaluation(eid: schema.TestSetsIdType) -> schema.Response[schema.EvaluationReport]:
        """Get Evaluations"""
        evaluation = testbed.process_report(db_conn=get_db_conn(), eid=eid.upper())
        return schema.Response[schema.EvaluationReport](
            data=evaluation,
            msg="Evaluation found.",
        )

    @auth.get(
        "/v1/testbed/testset_qa",
        description="Get Stored TestSets Q&A.",
        response_model=schema.Response[schema.TestSetQA],
    )
    async def testbed_get_testset_qa(tid: schema.TestSetsIdType) -> schema.Response[schema.TestSetQA]:
        """Get TestSet Q&A"""
        testset_qa = testbed.get_testset_qa(db_conn=get_db_conn(), tid=tid.upper())
        return schema.Response[schema.TestSetQA](
            data=testset_qa,
            msg="TestSet Q&A found",
        )

    @auth.post(
        "/v1/testbed/testset_load",
        description="Upsert TestSets.",
        response_model=schema.Response[schema.TestSetQA],
    )
    async def testbed_upsert_testsets(
        files: list[UploadFile], name: schema.TestSetsNameType, tid: Optional[schema.TestSetsIdType] = None
    ) -> schema.Response[schema.TestSetQA]:
        """Update stored TestSet data"""
        created = datetime.now().isoformat()
        db_conn = get_db_conn()
        try:
            for file in files:
                file_content = await file.read()
                content = testbed.jsonl_to_json_content(file_content)
                db_id = testbed.upsert_qa(db_conn, name, created, content, tid)
            db_conn.commit()
        except Exception as ex:
            logger.error("An exception occurred: %s", ex)
            raise HTTPException(status_code=500, detail="Unexpected error") from ex

        testset_qa = await testbed_get_testset_qa(tid=db_id)
        return testset_qa

    @auth.post(
        "/v1/testbed/testset_generate",
        description="Generate Q&A Test Set.",
        response_model=schema.Response[schema.TestSetQA],
    )
    async def testbed_generate_qa(
        files: list[UploadFile],
        name: schema.TestSetsNameType,
        ll_model: schema.ModelNameType = None,
        embed_model: schema.ModelNameType = None,
        questions: int = 0,
    ) -> schema.Response[schema.TestSetQA]:
        """Retrieve contents from a local file uploaded and generate Q&A"""
        # Setup Models
        giskard_ll_model = await models.apply_filter(
            model_objects,
            model_name=ll_model,
            model_type="ll",
            only_enabled=True,
        )
        giskard_embed_model = await models.apply_filter(
            model_objects,
            model_name=embed_model,
            model_type="embed",
            only_enabled=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            full_testsets = f"{temp_dir}/{name}_full.jsonl"
            for file in files:
                try:
                    # Read and save file content
                    file_content = await file.read()
                    filename = f"{temp_dir}/{file.filename}"
                    logger.info("Writing Q&A File to: %s", filename)
                    with open(filename, "wb") as temp_file:
                        temp_file.write(file_content)

                    # Process file for knowledge base
                    text_nodes = testbed.load_and_split(filename)
                    test_set = testbed.build_knowledge_base(
                        text_nodes, questions, giskard_ll_model[0], giskard_embed_model[0]
                    )
                    # Save test set
                    test_set_filename = f"{temp_dir}/{name}.jsonl"
                    test_set.save(test_set_filename)
                    with (
                        open(test_set_filename, "r", encoding="utf-8") as source,
                        open(full_testsets, "a", encoding="utf-8") as destination,
                    ):
                        destination.write(source.read())
                except Exception as ex:
                    logger.error("Error processing file: %s", str(ex))
                    raise

            # Store tests in database
            with open(full_testsets, "rb") as file:
                upload_file = UploadFile(file=file, filename=f"{name}.jsonl")
                testset_qa = await testbed_upsert_testsets(files=[upload_file], name=name)

        return testset_qa

    @auth.post(
        "/v1/testbed/evaluate",
        description="Evaluate Q&A Test Set.",
        response_model=schema.Response[schema.EvaluationReport],
    )
    def testbed_evaluate_qa(tid: schema.TestSetsIdType) -> schema.Response[schema.EvaluationReport]:
        """Run evaluate against a testset"""
        evaluated = datetime.now().isoformat()
        testbed_settings = next((settings for settings in settings_objects if settings.client == "testbed"), None)
        # Change Disable History
        testbed_settings.ll_model.chat_history = False

        def get_answer(question: str):
            """Submit question against the chatbot"""
            request = schema.ChatRequest(
                model=testbed_settings.ll_model.model,
                messages=[ChatMessage(role="human", content=question)],
            )
            ai_response = asyncio.run(chat_post(request, "testbed"))
            return ai_response.choices[0].message.content

        db_conn = get_db_conn()
        testset = testbed.get_testset_qa(db_conn=db_conn, tid=tid.upper())
        qa_test = "\n".join(json.dumps(item) for item in testset.qa_data)
        temp_directory = get_temp_directory()
        with open(f"/{temp_directory}/{tid}_output.txt", "w", encoding="utf-8") as file:
            file.write(qa_test)
        loaded_testset = QATestset.load(f"/{temp_directory}/{tid}_output.txt")
        report = evaluate(get_answer, testset=loaded_testset)

        eid = testbed.insert_evaluation(
            db_conn=db_conn,
            tid=tid,
            evaluated=evaluated,
            correctness=report.correctness,
            settings=testbed_settings.model_dump_json(),
            rag_report=pickle.dumps(report),
        )
        db_conn.commit()

        return schema.Response[schema.EvaluationReport](
            data=testbed.process_report(db_conn=db_conn, eid=eid),
            msg="Evaluation Completed",
        )

    logger.info("Endpoints Loaded.")
