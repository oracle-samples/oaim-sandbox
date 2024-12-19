"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore ollama, minilm, pplx, thenlper, mxbai, nomic

import os
import configparser
import oci
import server.oci as server_oci
from common.schema import OracleCloudSettings


def main() -> list[OracleCloudSettings]:
    config = []
    try:
        file = os.path.expanduser(os.environ.get("OCI_CLI_CONFIG_FILE", default=oci.config.DEFAULT_LOCATION))
        config_parser = configparser.ConfigParser()
        config_parser.read(file)
        for section in config_parser.sections() + ["DEFAULT"]:
            try:
                profile_data = oci.config.from_file(profile_name=section)
            except oci.exceptions.InvalidKeyFilePath:
                continue
            profile_data["profile"] = section
            config.append(profile_data)
    except oci.exceptions.ConfigFileNotFound:
        pass

    # If no default profile was found, append one
    if not any(item["profile"] == oci.config.DEFAULT_PROFILE for item in config):
        config.append({"profile": oci.config.DEFAULT_PROFILE})

    # override the default profile with EnvVars if set
    for default in config:
        if default["profile"] == oci.config.DEFAULT_PROFILE:
            default["tenancy"] = os.environ.get("OCI_CLI_TENANCY", default.get("tenancy", None))
            default["region"] = os.environ.get("OCI_CLI_REGION", default.get("region", None))
            default["user"] = os.environ.get("OCI_CLI_USER", default.get("user", None))
            default["fingerprint"] = os.environ.get("OCI_CLI_FINGERPRINT", default.get("fingerprint", None))
            default["key_file"] = os.environ.get("OCI_CLI_KEY_FILE", default.get("key_file", None))
            default["security_token_file"] = os.environ.get(
                "OCI_CLI_SECURITY_TOKEN_FILE", default.get("security_token_file", None)
            )
            default["log_requests"] = default.get("log_requests", False)
            default["additional_user_agent"] = default.get("additional_user_agent", "")
            default["pass_phrase"] = default.get("pass_phrase", None)

    oci_objects = []
    for oci_object in config:
        oci_config = OracleCloudSettings(**oci_object)
        oci_objects.append(oci_config)
        if oci_config.profile == "DEFAULT":
            try:
                client, namespace = server_oci.create_client(oci_config)
            except server_oci.OciException:
                continue
            oci_config.namespace = namespace
            oci_config.set_client(client)

    return oci_objects


if __name__ == "__main__":
    main()
