"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import os
import configparser
import modules.logging_config as logging_config

logger = logging_config.logging.getLogger("modules.oci_utils")

# Avoid OCI logging overridding
import oci  # pylint: disable=wrong-import-position


class OciException(Exception):
    """Custom OCI Exception"""

    def __init__(self, message, error_code=None):
        super().__init__(message)
        self.error_code = error_code

    def __str__(self):
        if self.error_code:
            return f"[Error {self.error_code}]: {self.args[0]}"
        return self.args[0]


def init_client(client_type, config=None, retries=True):
    """Initialise OCI Client with either user or Token"""
    # Setup Retries
    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY
    if not retries:
        retry_strategy = oci.retry.NoneRetryStrategy()

    # Initialise Client (Workload Identiy, Token and API)
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


def initialise(
    user=None,
    fingerprint=None,
    tenancy=None,
    region=None,
    key_file=None,
    security_token_file=None,
):
    """Initalise the configuration for OCI AuthN"""
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

    # Ingest configfile when parameter are missing
    if not (fingerprint and tenancy and region and key_file and (user or security_token_file)):
        logger.info("Ingesting Configfile: %s", config_file)
        file_contents = config_from_file(config_file, config_profile)
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


def get_config_profiles(file=None):
    """Get Profiles from OCI Config File"""
    profiles = []
    if file and os.path.exists(file):
        config = configparser.ConfigParser()
        config.read(file)
        profiles = config.sections()
        if config.defaults():
            profiles.insert(0, "DEFAULT")

    return profiles


def config_from_file(file=None, profile=None):
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


def get_namespace(config, retries=True):
    """Get the Object Storage Namespace.  Also used for testing AuthN"""
    logger.info("Getting Objectstore Namespace")
    try:
        client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
    except oci.exceptions.InvalidConfig:
        try:
            client = init_client(oci.object_storage.ObjectStorageClient, retries=retries)
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
    except FileNotFoundError as ex:
        raise OciException("Invalid Key Path") from ex
    except UnboundLocalError as ex:
        raise OciException("No Configuration - Disabling OCI") from ex

    return namespace


def get_compartments(config, retries=True):
    """Retrieve a list of compartments"""
    client = init_client(oci.identity.IdentityClient, config, retries)
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


def get_buckets(config, namespace, compartment, retries=True):
    """Get a list of buckets"""
    logger.info("Getting Buckets in %s", compartment)
    client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
    bucket_names = list()
    response = client.list_buckets(namespace_name=namespace, compartment_id=compartment, fields=["tags"])
    buckets = response.data
    for bucket in buckets:
        freeform_tags = bucket.freeform_tags or {}
        if freeform_tags.get("genai_chunk") != "true":
            bucket_names.append(bucket.name)

    return bucket_names


def get_bucket_objects(config, namespace, bucket_name, retries=True):
    """Get a list of Bucket Objects"""
    client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
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


def create_bucket(config, namespace, compartment, bucket_name, retries=True):
    """Create a bucket for split documents if it doesn't exist"""
    logger.info("Creating new bucket: %s", bucket_name)
    client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
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


def get_object(config, namespace, bucket_name, directory, object_name, retries=True):
    """Download Object Storage Object"""
    client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
    file_name = os.path.basename(object_name)
    file_path = os.path.join(directory, file_name)
    response = client.get_object(namespace_name=namespace, bucket_name=bucket_name, object_name=object_name)

    with open(file_path, "wb") as f:
        for content in response.data.raw.stream(1024 * 1024, decode_content=False):
            f.write(content)
    file_size = os.path.getsize(file_path)
    logger.info("Downloaded %s to %s (%i bytes)", file_name, file_path, file_size)

    return file_path


def put_object(config, namespace, compartment, bucket_name, file_path, retries=True):
    """Upload file to Object Storage"""
    file_name = os.path.basename(file_path)
    file_name = os.path.basename(file_path)
    client = init_client(oci.object_storage.ObjectStorageClient, config, retries)
    upload_manager = oci.object_storage.UploadManager(client, allow_parallel_uploads=True, parallel_process_count=10)
    try:
        upload_manager.upload_file(namespace, bucket_name, file_name, file_path)
    except oci.exceptions.ServiceError as ex:
        logger.exception(ex, exc_info=False)
        create_bucket(config, namespace, compartment, bucket_name)
        upload_manager.upload_file(namespace, bucket_name, file_name, file_path)
    logger.info("Uploaded %s to %s", file_name, bucket_name)

    os.remove(file_path)
