"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import oci

from common.schema import OracleCloudSettings
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.oci")

class OciException(Exception):
    """Custom OCI Exception"""

    def __init__(self, message):
        super().__init__(message)

def create_client(
    config: OracleCloudSettings = None) -> tuple[oci.object_storage.ObjectStorageClient, str]:
    """Connect OCI Object Storage Client with either user or Token"""
    client_type = oci.object_storage.ObjectStorageClient
    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY

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

    logger.info("Attempting OCI Client Connection")
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
    except Exception as ex:
        raise OciException("Uncaught Exception - Disabling OCI") from ex

    return client, namespace
