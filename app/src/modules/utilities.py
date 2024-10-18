"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore oracledb, genai, ashburn, pplx, giskard, giskarded, pypdf, testset
# spell-checker:ignore langchain, docstore, vectorstores, vectorstorage, vectorstore
# spell-checker:ignore oraclevs, openai, ollama

import json
import time
import os
import configparser
import re
from typing import List, Union
import math
import pickle
import requests
from pypdf import PdfReader
import pandas as pd

import modules.logging_config as logging_config
import modules.metadata as meta
import oracledb

from openai import OpenAI

from langchain.docstore.document import Document as LangchainDocument
from langchain_community.vectorstores import oraclevs as LangchainVS
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_community.chat_models import ChatPerplexity
from langchain_cohere import ChatCohere
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

from giskard.llm import set_llm_api, set_default_client
from giskard.llm.client.openai import OpenAIClient
from giskard.llm.embeddings.openai import OpenAIEmbedding
from giskard.rag import KnowledgeBase, generate_testset
from giskard.rag.question_generators import simple_questions, complex_questions

logger = logging_config.logging.getLogger("modules.utilities")

# Avoid OCI logging overriding
import oci  # pylint: disable=wrong-import-position


###############################################################################
# General
###############################################################################
def is_url_accessible(url):
    """Check that URL is Available"""
    logger.debug("Checking %s is accessible", url)
    try:
        response = requests.get(url, timeout=2)
        logger.info("Checking %s resulted in %s", url, response.status_code)
        # Check if the response status code is 200 (OK) 403 (Forbidden) 404 (Not Found) 421 (Misdirected)
        if response.status_code in [200, 403, 404, 421]:
            return True, None
        else:
            err_msg = f"{url} is not accessible. (Status: {response.status_code})"
            logger.warning(err_msg)
            return False, err_msg
    except requests.exceptions.ConnectionError:
        err_msg = f"{url} is not accessible. (Connection Error)"
        logger.warning(err_msg)
        return False, err_msg
    except requests.exceptions.Timeout:
        err_msg = f"{url} is not accessible. (Request Timeout)"
        logger.warning(err_msg)
        return False, err_msg
    except requests.RequestException as ex:
        logger.exception(ex, exc_info=False)
        return False, ex


###############################################################################
# Models
###############################################################################
def get_ll_model(model, ll_models_config=None, giskarded=False):
    """Return a formatted LL model"""
    if ll_models_config is None:
        ll_models_config = meta.ll_models()
    lm_params = ll_models_config[model]

    logger.info(
        "Configuring LLM - URL: %s; Temp - %s; Max Tokens - %s",
        lm_params["url"],
        lm_params["temperature"][0],
        lm_params["max_tokens"][0],
    )

    llm_api = lm_params["api"]
    llm_url = lm_params["url"]

    logger.debug("Matching LLM API: %s", llm_api)

    ## Start - Add Additional Model Authentication Here
    client = None
    if giskarded:
        giskard_key = lm_params.get("api_key") or "giskard"
        _client = OpenAI(api_key=giskard_key, base_url=f"{llm_url}/v1/")
        client = OpenAIClient(model=model, client=_client)
    elif llm_api == "OpenAI":
        client = ChatOpenAI(
            api_key=lm_params["api_key"],
            model_name=model,
            temperature=lm_params["temperature"][0],
            max_tokens=lm_params["max_tokens"][0],
            top_p=lm_params["top_p"][0],
            frequency_penalty=lm_params["frequency_penalty"][0],
            presence_penalty=lm_params["presence_penalty"][0],
        )
    elif llm_api == "Cohere":
        client = ChatCohere(
            cohere_api_key=lm_params["api_key"],
            model=model,
            temperature=lm_params["temperature"][0],
            max_tokens=lm_params["max_tokens"][0],
            top_p=lm_params["top_p"][0],
            frequency_penalty=lm_params["frequency_penalty"][0],
            presence_penalty=lm_params["presence_penalty"][0],
        )
    elif llm_api == "ChatPerplexity":
        client = ChatPerplexity(
            pplx_api_key=lm_params["api_key"],
            model=model,
            temperature=lm_params["temperature"][0],
            max_tokens=lm_params["max_tokens"][0],
            model_kwargs={
                "top_p": lm_params["top_p"][0],
                "frequency_penalty": lm_params["frequency_penalty"][0],
                "presence_penalty": lm_params["presence_penalty"][0],
            },
        )
    elif llm_api == "ChatOllama":
        client = ChatOllama(
            model=model,
            base_url=llm_url,
            temperature=lm_params["temperature"][0],
            max_tokens=lm_params["max_tokens"][0],
            model_kwargs={
                "top_p": lm_params["top_p"][0],
                "frequency_penalty": lm_params["frequency_penalty"][0],
                "presence_penalty": lm_params["presence_penalty"][0],
            },
        )
    ## End - Add Additional Model Authentication Here
    api_accessible, err_msg = is_url_accessible(llm_url)

    return client, api_accessible, err_msg


def get_embedding_model(model, embed_model_config=None, giskarded=False):
    """Return a formatted embedding model"""
    logger.info("Retrieving Embedding Model for: %s", model)
    if embed_model_config is None:
        embed_model_config = meta.embedding_models()

    embed_api = embed_model_config[model]["api"]
    embed_url = embed_model_config[model]["url"]
    embed_key = embed_model_config[model]["api_key"]

    logger.debug("Matching Embedding API: %s", embed_api)
    if giskarded:
        giskard_key = embed_key or "giskard"
        _client = OpenAI(api_key=giskard_key, base_url=f"{embed_url}/v1/")
        client = OpenAIEmbedding(model=model, client=_client)
    elif embed_api.__name__ == "OpenAIEmbeddings":
        try:
            client = embed_api(model=model, openai_api_key=embed_key)
        except Exception as ex:
            logger.exception(ex)
            raise ValueError from ex
    elif embed_api.__name__ == "OllamaEmbeddings":
        client = embed_api(model=model, base_url=embed_url)
    elif embed_api.__name__ == "CohereEmbeddings":
        client = embed_api(model=model, cohere_api_key=embed_key)
    else:
        client = embed_api(model=embed_url)

    api_accessible, err_msg = is_url_accessible(embed_url)

    return client, api_accessible, err_msg


###############################################################################
# Database
###############################################################################
def db_initialize(user=None, password=None, dsn=None, wallet_password=None):
    """Create the configuration for connecting to an Oracle Database"""
    config = {
        "user": user,
        "password": password,
        "dsn": dsn,
        "wallet_password": wallet_password,
        "tcp_connect_timeout": 5,
    }

    # Update with EnvVars if set and not provided
    if not config["user"]:
        config["user"] = os.environ.get("DB_USERNAME", default=None)
    if not config["password"]:
        config["password"] = os.environ.get("DB_PASSWORD", default=None)
    if not config["dsn"]:
        config["dsn"] = os.environ.get("DB_DSN", default=None)
    if not config["wallet_password"]:
        config["wallet_password"] = os.environ.get("DB_WALLET_PASSWORD", default=None)

    # ADB mTLS (this is a default location req. for images; do not change)
    tns_directory = os.environ.get("TNS_ADMIN", default="tns_admin")
    config["config_dir"] = tns_directory
    if "wallet_password" in config and config["wallet_password"] is not None:
        config["wallet_location"] = config["config_dir"]

    logger.debug("Database Configuration: %s", config)
    return config


def db_connect(config):
    """Establish a connection to an Oracle Database"""
    conn = oracledb.connect(**config)
    logger.debug("Database Connection Established")
    return conn


def execute_sql(conn, run_sql):
    """Execute SQL against Oracle Database"""
    try:
        cursor = conn.cursor()
        cursor.execute(run_sql)
        logger.info("SQL Executed")
    except oracledb.DatabaseError as ex:
        if ex.args and len(ex.args) > 0:
            error_obj = ex.args[0]
            if (
                # ORA-00955: name is already used by an existing object
                hasattr(error_obj, "code") and error_obj.code == 955
            ):
                logger.info("Table Exists")
        else:
            logger.exception(ex, exc_info=False)
            raise
    finally:
        cursor.close()


###############################################################################
# Vector Storage
###############################################################################
def init_vs(db_conn, embedding_function, store_table, distance_metric):
    """initialize the Vector Store"""
    logger.info("Initializing Vectorstore table: %s", embedding_function)
    try:
        vectorstore = OracleVS(db_conn, embedding_function, store_table, distance_metric)
    except:
        logger.exception("Failed to initialize the Vector Store")
        raise

    logger.info("Vectorstore %s loaded", vectorstore)
    return vectorstore


def get_vs_table(model, chunk_size, chunk_overlap, distance_metric, embed_alias=None):
    """Get a list of Vector Store Tables"""
    chunk_overlap_ceil = math.ceil(chunk_overlap)
    table_string = f"{model}_{chunk_size}_{chunk_overlap_ceil}_{distance_metric}"
    if embed_alias:
        table_string = f"{embed_alias}_{table_string}"
    store_table = re.sub(r"\W", "_", table_string.upper())
    store_comment = (
        f'{{"alias": "{embed_alias}",'
        f'"model": "{model}",'
        f'"chunk_size": {chunk_size},'
        f'"chunk_overlap": {chunk_overlap_ceil},'
        f'"distance_metric": "{distance_metric}"}}'
    )
    logger.info("Vector Store Table: %s; Comment: %s", store_table, store_comment)
    return store_table, store_comment


def populate_vs(
    db_conn,
    store_table,
    store_comment,
    model_name,
    distance_metric,
    input_data: Union[List["LangchainDocument"], List] = None,
    rate_limit=0,
):
    """Populate the Vector Storage"""

    def json_to_doc(file: str):
        """Creates a list of LangchainDocument from a JSON file. Returns the list of documents."""
        logger.info("Converting %s to Document", file)

        with open(file, "r", encoding="utf-8") as document:
            chunks = json.load(document)
            docs = []
            for chunk in chunks:
                page_content = chunk["kwargs"]["page_content"]
                metadata = chunk["kwargs"]["metadata"]
                docs.append(LangchainDocument(page_content=str(page_content), metadata=metadata))

        logger.info("Total Chunk Size: %i bytes", docs.__sizeof__())
        logger.info("Chunks ingested: %i", len(docs))
        return docs

    # Loop through files and create Documents
    if isinstance(input_data[0], LangchainDocument):
        logger.debug("Processing Documents: %s", input_data)
        documents = input_data
    else:
        documents = []
        for file in input_data:
            logger.info("Processing file: %s into a Document.", file)
            documents.extend(json_to_doc(file))

    logger.info("Size of Payload: %i bytes", documents.__sizeof__())
    logger.info("Total Chunks: %i", len(documents))

    # Remove duplicates (copy-writes, etc)
    unique_texts = {}
    unique_chunks = []
    for chunk in documents:
        if chunk.page_content not in unique_texts:
            unique_texts[chunk.page_content] = True
            unique_chunks.append(chunk)
    logger.info("Total Unique Chunks: %i", len(unique_chunks))

    # Need to consider this, it duplicates from_documents
    logger.info("Dropping table %s", store_table)
    LangchainVS.drop_table_purge(db_conn, store_table)

    vectorstore = OracleVS(
        client=db_conn,
        embedding_function=model_name,
        table_name=store_table,
        distance_strategy=distance_metric,
    )

    # Batch Size does not have a measurable impact on performance
    # but does eliminate issues with timeouts
    # Careful increasing as may break token rate limits
    batch_size = 500
    for i in range(0, len(unique_chunks), batch_size):
        batch = unique_chunks[i : i + batch_size]
        logger.info(
            "Processing: %i Chunks of %i (Rate Limit: %i)",
            len(unique_chunks) if len(unique_chunks) < i + batch_size else i + batch_size,
            len(unique_chunks),
            rate_limit,
        )
        OracleVS.add_documents(vectorstore, documents=batch)
        if rate_limit > 0:
            interval = 60 / rate_limit
            logger.info("Rate Limiting: sleeping for %i seconds", interval)
            time.sleep(interval)

    # Build the Index
    logger.info("Creating index on: %s", store_table)
    try:
        LangchainVS.create_index(db_conn, vectorstore)
    except Exception as ex:
        logger.error("Unable to create vector index: %s", ex)

    # Comment the VS table
    comment = f"COMMENT ON TABLE {store_table} IS 'GENAI: {store_comment}'"
    execute_sql(db_conn, comment)
    db_conn.close()


def get_vs_tables(conn, enabled_embed):
    """Retrieve Vector Storage Tables"""
    logger.info("Looking for Vector Storage Tables")
    output = {}
    sql = """
        SELECT ut.table_name||':'||REPLACE(utc.comments, 'GENAI: ', '')
          FROM user_tab_comments utc, user_tables ut
         WHERE utc.table_name = ut.table_name
           AND utc.comments LIKE 'GENAI:%'"""
    try:
        cursor = conn.cursor()
        logger.debug("Executing SQL: %s", sql)
        for row in cursor.execute(sql):
            row_str = row[0]
            key, value = row_str.split(":", 1)
            value = json.loads(value)
            logger.info("--> Found Table: %s", key)
            if any(model_item == value["model"] for model_item in enabled_embed):
                output[key] = value
            else:
                logger.info("No enabled embedding model found to support table %s", key)
    except oracledb.DatabaseError as ex:
        logger.exception(ex, exc_info=False)
    finally:
        cursor.close()

    return json.dumps(output, indent=4)


###############################################################################
# Oracle Cloud Infrastructure
###############################################################################
class OciException(Exception):
    """Custom OCI Exception"""

    def __init__(self, message, error_code=None):
        super().__init__(message)
        self.error_code = error_code

    def __str__(self):
        if self.error_code:
            return f"[Error {self.error_code}]: {self.args[0]}"
        return self.args[0]


def oci_init_client(client_type, config=None, retries=True):
    """Initialize OCI Client with either user or Token"""
    # Setup Retries
    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY
    if not retries:
        retry_strategy = oci.retry.NoneRetryStrategy()

    # Initialize Client (Workload Identity, Token and API)
    if not config:
        logger.info("OCI Authentication with Workload Identity")
        signer = oci.auth.signers.get_oke_workload_identity_resource_principal_signer()
        # Region is required for endpoint generation; not sure its value matters
        client = client_type(config={"region": "us-ashburn-1"}, signer=signer)
    elif config and config["security_token_file"]:
        logger.info("OCI Authentication with Security Token")
        token = None
        with open(config["security_token_file"], "r", encoding="utf-8") as f:
            token = f.read()
        private_key = oci.signer.load_private_key_from_file(config["key_file"])
        signer = oci.auth.signers.SecurityTokenSigner(token, private_key)
        client = client_type({"region": config["region"]}, signer=signer)
    else:
        logger.info("OCI Authentication as Standard")
        client = client_type(config, retry_strategy=retry_strategy)
    return client


def oci_initialize(
    user=None,
    fingerprint=None,
    tenancy=None,
    region=None,
    key_file=None,
    security_token_file=None,
):
    """Initialize the configuration for OCI AuthN"""
    config = {
        "user": user,
        "fingerprint": fingerprint,
        "tenancy": tenancy,
        "region": region,
        "key_file": key_file,
        "security_token_file": security_token_file,
        "additional_user_agent": "",
        "log_requests": False,
        "pass_phrase": None,
    }

    config_file = os.environ.get("OCI_CLI_CONFIG_FILE", default=oci.config.DEFAULT_LOCATION)
    config_profile = os.environ.get("OCI_CLI_PROFILE", default=oci.config.DEFAULT_PROFILE)

    # Ingest config file when parameter are missing
    if not (fingerprint and tenancy and region and key_file and (user or security_token_file)):
        logger.info("Ingesting Config File: %s", config_file)
        file_contents = oci_config_from_file(config_file, config_profile)
        if file_contents:
            config = file_contents

    # Update with EnvVars (EnvVars override config when set)
    config["security_token_file"] = os.environ.get("OCI_CLI_SECURITY_TOKEN_FILE", config.get("security_token_file"))
    config["user"] = os.environ.get("OCI_CLI_USER", config.get("user"))
    config["fingerprint"] = os.environ.get("OCI_CLI_FINGERPRINT", config.get("fingerprint"))
    config["tenancy"] = os.environ.get("OCI_CLI_TENANCY", config.get("tenancy"))
    config["region"] = os.environ.get("OCI_CLI_REGION", config.get("region"))
    config["key_file"] = os.environ.get("OCI_CLI_KEY_FILE", config.get("key_file"))
    return config


def oci_get_config_profiles(file=None):
    """Get Profiles from OCI Config File"""
    profiles = []
    if file and os.path.exists(file):
        config = configparser.ConfigParser()
        config.read(file)
        profiles = config.sections()
        if config.defaults():
            profiles.insert(0, "DEFAULT")

    return profiles


def oci_config_from_file(file=None, profile=None):
    """Ingest OCI Configuration from file"""
    try:
        config_from_file_load = oci.config.from_file(
            (file if file else oci.config.DEFAULT_LOCATION),
            (profile if profile else oci.config.DEFAULT_PROFILE),
        )
        logger.info("OCI configuration set")
    except oci.exceptions.ConfigFileNotFound as ex:
        logger.exception(ex, exc_info=False)
        return None

    return config_from_file_load


def oci_get_namespace(config, retries=True):
    """Get the Object Storage Namespace.  Also used for testing AuthN"""
    logger.info("Getting Object Storage Namespace")
    try:
        client = oci_init_client(oci.object_storage.ObjectStorageClient, config, retries)
    except oci.exceptions.InvalidConfig:
        try:
            client = oci_init_client(oci.object_storage.ObjectStorageClient, retries=retries)
        except ValueError:
            pass
    except FileNotFoundError:
        pass

    try:
        namespace = client.get_namespace().data
        logger.info("Succeeded - Namespace = %s", namespace)
    except oci.exceptions.InvalidConfig as ex:
        raise OciException("Invalid Config - Disabling OCI") from ex
    except oci.exceptions.ServiceError as ex:
        raise OciException("AuthN Error - Disabling OCI") from ex
    except oci.exceptions.RequestException as ex:
        raise OciException("No Network Access - Disabling OCI") from ex
    except FileNotFoundError as ex:
        raise OciException("Invalid Key Path") from ex
    except UnboundLocalError as ex:
        raise OciException("No Configuration - Disabling OCI") from ex

    return namespace


def oci_get_compartments(config, retries=True):
    """Retrieve a list of compartments"""
    client = oci_init_client(oci.identity.IdentityClient, config, retries)
    logger.info("Getting Compartments")
    compartment_paths_dict = {}
    response = client.list_compartments(
        compartment_id=config["tenancy"],
        compartment_id_in_subtree=True,
        access_level="ACCESSIBLE",
        sort_by="NAME",
        sort_order="ASC",
        lifecycle_state="ACTIVE",
    )
    compartments = response.data

    # Create a dictionary to map compartment ID to compartment details
    compartment_dict = {compartment.id: compartment for compartment in compartments}

    def construct_path(compartment):
        """Function to construct the full path of a compartment"""
        path = []
        current = compartment
        while current:
            path.append(current.name)
            current = compartment_dict.get(current.compartment_id)
        return " / ".join(reversed(path))

    # Create a dictionary with full paths as keys and OCIDs as values
    compartment_paths_dict = {construct_path(compartment): compartment.id for compartment in compartments}

    return compartment_paths_dict


def oci_get_buckets(config, namespace, compartment, retries=True):
    """Get a list of buckets"""
    logger.info("Getting Buckets in %s", compartment)
    client = oci_init_client(oci.object_storage.ObjectStorageClient, config, retries)
    bucket_names = list()
    response = client.list_buckets(namespace_name=namespace, compartment_id=compartment, fields=["tags"])
    buckets = response.data
    for bucket in buckets:
        freeform_tags = bucket.freeform_tags or {}
        if freeform_tags.get("genai_chunk") != "true":
            bucket_names.append(bucket.name)

    return bucket_names


def oci_get_bucket_objects(config, namespace, bucket_name, retries=True):
    """Get a list of Bucket Objects"""
    client = oci_init_client(oci.object_storage.ObjectStorageClient, config, retries)
    object_names = list()
    try:
        response = client.list_objects(
            namespace_name=namespace,
            bucket_name=bucket_name,
        )
        objects = response.data.objects
        object_names = [object.name for object in objects]
    except oci.exceptions.ServiceError:
        logger.debug("Bucket %s not found.  Will create on upload.", bucket_name)

    return object_names


def oci_create_bucket(config, namespace, compartment, bucket_name, retries=True):
    """Create a bucket for split documents if it doesn't exist"""
    logger.info("Creating new bucket: %s", bucket_name)
    client = oci_init_client(oci.object_storage.ObjectStorageClient, config, retries)
    try:
        client.create_bucket(
            namespace_name=namespace,
            create_bucket_details=oci.object_storage.models.CreateBucketDetails(
                name=bucket_name,
                compartment_id=compartment,
                freeform_tags={"genai_chunk": "true"},
            ),
        )
    except oci.exceptions.ServiceError as ex:
        if ex.status == 409:
            logger.info("Bucket %s already exists. Ignoring error.", bucket_name)
        else:
            logger.exception(ex, exc_info=False)


def oci_get_object(config, namespace, bucket_name, directory, object_name, retries=True):
    """Download Object Storage Object"""
    client = oci_init_client(oci.object_storage.ObjectStorageClient, config, retries)
    file_name = os.path.basename(object_name)
    file_path = os.path.join(directory, file_name)
    response = client.get_object(namespace_name=namespace, bucket_name=bucket_name, object_name=object_name)

    with open(file_path, "wb") as f:
        for content in response.data.raw.stream(1024 * 1024, decode_content=False):
            f.write(content)
    file_size = os.path.getsize(file_path)
    logger.info("Downloaded %s to %s (%i bytes)", file_name, file_path, file_size)

    return file_path


def oci_put_object(config, namespace, compartment, bucket_name, file_path, retries=True):
    """Upload file to Object Storage"""
    file_name = os.path.basename(file_path)
    logger.info("Uploading %s to %s as %s ", file_path, bucket_name, file_name)
    client = oci_init_client(oci.object_storage.ObjectStorageClient, config, retries)
    upload_manager = oci.object_storage.UploadManager(client, allow_parallel_uploads=True, parallel_process_count=10)
    try:
        upload_manager.upload_file(namespace, bucket_name, file_name, file_path)
    except oci.exceptions.ServiceError as ex:
        logger.exception(ex, exc_info=False)
        oci_create_bucket(config, namespace, compartment, bucket_name)
        upload_manager.upload_file(namespace, bucket_name, file_name, file_path)
    logger.info("Uploaded %s to %s", file_name, bucket_name)

    os.remove(file_path)


###############################################################################
# Test Framework
###############################################################################
def dump_pickle(cucumber):
    """Dump pickle to file"""
    with open(cucumber, "wb") as file:
        pickle.dump(cucumber, file)
    logger.info("Dumped %s", cucumber)


def load_and_split(eval_file, tn_file, chunk_size=2048):
    """Load and Split Document"""
    logger.info("Loading %s; Chunk Size: %i", eval_file, chunk_size)
    loader = PdfReader(eval_file)
    documents = []
    for page in loader.pages:
        document = Document(text=page.extract_text())
        documents.append(document)
    splitter = SentenceSplitter(chunk_size=chunk_size)
    text_nodes = splitter(documents)
    logger.info("Writing: %s", tn_file)
    dump_pickle(tn_file)

    return text_nodes


def build_knowledge_base(text_nodes, kb_file, llm_client, embed_client):
    """Establish a temporary Knowledge Base"""
    logger.info("KnowledgeBase creation starting..")
    knowledge_base_df = pd.DataFrame([node.text for node in text_nodes], columns=["text"])
    knowledge_base_df.to_json(
        kb_file,
        orient="records",
    )
    knowledge_base = KnowledgeBase(knowledge_base_df, llm_client=llm_client, embedding_model=embed_client)
    logger.info("KnowledgeBase created and saved: %s", kb_file)

    return knowledge_base


def generate_qa(qa_file, kb, qa_count, api="openai", client=None):
    """Generate an example QA"""
    logger.info("QA Generation starting.. (client=%s)", client)
    set_llm_api(api)
    set_default_client(client)

    test_set = generate_testset(
        kb,
        question_generators=[
            simple_questions,
            complex_questions,
        ],
        num_questions=qa_count,
        agent_description="A chatbot answering questions on a knowledge base",
    )
    test_set.save(qa_file)
    logger.info("QA created and saved: %s", qa_file)

    return test_set


def merge_jsonl_files(file_list, temp_dir):
    """Take Uploaded QA files and merge into a single one"""
    output_file = os.path.join(temp_dir, "merged_dataset.jsonl")
    logger.info("Writing test set file: %s", output_file)
    with open(output_file, "w", encoding="utf-8") as outfile:
        for input_file in file_list:
            logger.info("Processing: %s", input_file)
            with open(input_file, "r", encoding="utf-8") as in_file:
                for line in in_file:
                    outfile.write(line)

    logger.info("De-duplicating: %s", output_file)
    df = pd.read_json(output_file, lines=True)
    duplicate_ids = df[df.duplicated("id", keep=False)]  # pylint: disable=no-member
    if not duplicate_ids.empty:
        # Remove duplicates, keeping the first occurrence
        df = df.drop_duplicates(subset="id", keep="first")  # pylint: disable=no-member
    df.to_json(output_file, orient="records", lines=True)
    logger.info("Wrote test set file: %s", output_file)

    return output_file
