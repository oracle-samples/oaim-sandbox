"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore genai, ocids

from typing import Union

import oci

from common.schema import OracleCloudSettings
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.oci")


class OciException(Exception):
    """Custom OCI Exception"""

    def __init__(self, message):
        super().__init__(message)


def init_client(
    client_type: Union[
        oci.object_storage.ObjectStorageClient,
        oci.identity.IdentityClient,
    ],
    config: OracleCloudSettings = None,
    retries: bool = True,
) -> Union[
    oci.object_storage.ObjectStorageClient,
    oci.identity.IdentityClient,
]:
    """Initialize OCI Client with either user or Token"""
    # Setup Retries
    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY
    if not retries:
        retry_strategy = oci.retry.NoneRetryStrategy()

    # Dump Model into JSON
    config_json = config.model_dump(exclude_none=False)

    # Initialize Client (Workload Identity, Token and API)
    client = None
    if not config_json:
        logger.info("OCI Authentication with Workload Identity")
        oke_workload_signer = oci.auth.signers.get_oke_workload_identity_resource_principal_signer()
        client = client_type(config={}, signer=oke_workload_signer)
    elif config_json and config_json["security_token_file"]:
        logger.info("OCI Authentication with Security Token")
        token = None
        with open(config_json["security_token_file"], "r", encoding="utf-8") as f:
            token = f.read()
        private_key = oci.signer.load_private_key_from_file(config_json["key_file"])
        signer = oci.auth.signers.SecurityTokenSigner(token, private_key)
        client = client_type(config={"region": config_json["region"]}, signer=signer)
    else:
        logger.info("OCI Authentication as Standard")
        client = client_type(config_json, retry_strategy=retry_strategy)
    return client


def get_namespace(config: OracleCloudSettings = None, retries: bool = True) -> str:
    """Get the Object Storage Namespace.  Also used for testing AuthN"""
    logger.info("Getting Object Storage Namespace")
    client_type = oci.object_storage.ObjectStorageClient
    try:
        client = init_client(client_type, config, retries)
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
    except Exception as ex:
        raise OciException("Uncaught Exception - Disabling OCI") from ex

    return namespace


def get_compartments(config: OracleCloudSettings = None, retries: bool = True) -> set:
    """Retrieve a list of compartments"""
    client_type = oci.identity.IdentityClient
    client = init_client(client_type, config, retries)

    compartment_paths = {}
    response = client.list_compartments(
        compartment_id=config.tenancy,
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

    # Create a set with full paths as keys and OCIDs as values
    compartment_paths = {construct_path(compartment): compartment.id for compartment in compartments}
    logger.info("Returning %i Compartments", len(compartment_paths))
    return compartment_paths


def get_buckets(compartment: str, config: OracleCloudSettings = None, retries: bool = True) -> list:
    """Get a list of buckets"""
    client_type = oci.object_storage.ObjectStorageClient
    client = init_client(client_type, config, retries)

    logger.info("Getting Buckets in %s", compartment)
    client = init_client(client_type, config, retries)
    bucket_names = []
    response = client.list_buckets(namespace_name=config.namespace, compartment_id=compartment, fields=["tags"])
    buckets = response.data
    for bucket in buckets:
        freeform_tags = bucket.freeform_tags or {}
        if freeform_tags.get("genai_chunk") != "true":
            bucket_names.append(bucket.name)

    return bucket_names


def get_bucket_objects(bucket_name: str, config: OracleCloudSettings = None, retries: bool = True) -> list:
    """Get a list of Bucket Objects"""
    client_type = oci.object_storage.ObjectStorageClient
    client = init_client(client_type, config, retries)

    object_names = []
    try:
        response = client.list_objects(
            namespace_name=config.namespace,
            bucket_name=bucket_name,
        )
        objects = response.data.objects
        #TODO(gotsysba) - filter out non-supported objects
        object_names = [object.name for object in objects]
    except oci.exceptions.ServiceError:
        logger.debug("Bucket %s not found.  Will create on upload.", bucket_name)

    return object_names


# def create_bucket(config, namespace, compartment, bucket_name, retries=True):
#     """Create a bucket for split documents if it doesn't exist"""
#     logger.info("Creating new bucket: %s", bucket_name)
#     client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
#     try:
#         client.create_bucket(
#             namespace_name=namespace,
#             create_bucket_details=oci.object_storage.models.CreateBucketDetails(
#                 name=bucket_name,
#                 compartment_id=compartment,
#                 freeform_tags={"genai_chunk": "true"},
#             ),
#         )
#     except oci.exceptions.ServiceError as ex:
#         if ex.status == 409:
#             logger.info("Bucket %s already exists. Ignoring error.", bucket_name)
#         else:
#             logger.exception(ex, exc_info=False)


# def get_object(config, namespace, bucket_name, directory, object_name, retries=True):
#     """Download Object Storage Object"""
#     client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
#     file_name = os.path.basename(object_name)
#     file_path = os.path.join(directory, file_name)
#     response = client.get_object(namespace_name=namespace, bucket_name=bucket_name, object_name=object_name)

#     with open(file_path, "wb") as f:
#         for content in response.data.raw.stream(1024 * 1024, decode_content=False):
#             f.write(content)
#     file_size = os.path.getsize(file_path)
#     logger.info("Downloaded %s to %s (%i bytes)", file_name, file_path, file_size)

#     return file_path


# def put_object(config, namespace, compartment, bucket_name, file_path, retries=True):
#     """Upload file to Object Storage"""
#     file_name = os.path.basename(file_path)
#     logger.info("Uploading %s to %s as %s ", file_path, bucket_name, file_name)
#     client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
#     upload_manager = oci.object_storage.UploadManager(client, allow_parallel_uploads=True, parallel_process_count=10)
#     try:
#         upload_manager.upload_file(namespace, bucket_name, file_name, file_path)
#     except oci.exceptions.ServiceError as ex:
#         logger.exception(ex, exc_info=False)
#         create_bucket(config, namespace, compartment, bucket_name)
#         upload_manager.upload_file(namespace, bucket_name, file_name, file_path)
#     logger.info("Uploaded %s to %s", file_name, bucket_name)

#     os.remove(file_path)
