"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

Script initializes a web interface for Oracle Cloud Infrastructure (OCI)
It includes a form to input and test OCI API Access.

Session States Set:
- oci_config: Stores OCI Configuration
"""
# spell-checker:ignore streamlit, ocid

import inspect

import streamlit as st
from streamlit import session_state as state

import sandbox.utils.api_call as api_call
import sandbox.utils.st_common as st_common

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("config.oci")

# Set endpoint if server has been established
OCI_API_ENDPOINT = None
if "server" in state:
    OCI_API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/oci"


#####################################################
# Functions
#####################################################
def get_oci() -> dict[str, dict]:
    """Get a dictionary of all OCI Configurations"""
    if "oci_config" not in state or state["oci_config"] == {}:
        try:
            response = api_call.get(url=OCI_API_ENDPOINT)
            state["oci_config"] = {
                item["profile"]: {k: v for k, v in item.items() if k != "profile"} for item in response["data"]
            }
            logger.info("State created: state['oci_config']")
        except api_call.ApiError as ex:
            st.error(f"Unable to retrieve oci_configuration: {ex}", icon="🚨")
            state["oci_config"] = {}


def patch_oci(
    profile: str, user: str, fingerprint: str, tenancy: str, region: str, key_file: str, security_token_file: str
) -> None:
    """Update OCI"""
    # Check if the oci configuration is changed
    if (
        state.oci_config[profile]["user"] != user
        or state.oci_config[profile]["fingerprint"] != fingerprint
        or state.oci_config[profile]["tenancy"] != tenancy
        or state.oci_config[profile]["region"] != region
        or state.oci_config[profile]["key_file"] != key_file
        or state.oci_config[profile]["security_token_file"] != security_token_file
        or not state.oci_config[profile]["namespace"]
    ):
        try:
            api_call.patch(
                url=OCI_API_ENDPOINT + "/" + profile,
                payload={
                    "json": {
                        "user": user,
                        "fingerprint": fingerprint,
                        "tenancy": tenancy,
                        "region": region,
                        "key_file": key_file,
                        "security_token_file": security_token_file,
                    }
                },
            )
            st.success(f"{profile} OCI Configuration - Updated", icon="✅")
            st_common.clear_state_key("oci_config")
            st_common.clear_state_key("oci_error")
        except api_call.ApiError as ex:
            logger.error("OCI Update failed: %s", ex)
            state.oci_error = ex
            state.oci_config[profile]["namespace"] = None
        st.rerun()
    else:
        st.info(f"{profile} OCI Configuration - No Changes Detected.", icon="ℹ️")


#####################################################
# MAIN
#####################################################
def main() -> None:
    """Streamlit GUI"""
    st.header("Oracle Cloud Infrastructure")
    st.write("Configure OCI for Object Storage Access.")
    try:
        get_oci()  # Create/Rebuild state
    except api_call.ApiError:
        st.stop()
    # TODO(gotsysdba) Add select for profiles
    profile = "DEFAULT"
    st.subheader("Configuration")
    token_auth = st.checkbox("Use token authentication?", value=False)
    with st.form("update_oci_config"):
        user = st.text_input(
            "User OCID:",
            value=state.oci_config[profile]["user"],
            disabled=token_auth,
            key="oci_user",
        )
        security_token_file = st.text_input(
            "Security Token File:",
            value=state.oci_config[profile]["security_token_file"],
            disabled=not token_auth,
            key="oci_security_token_file",
        )
        fingerprint = st.text_input(
            "Fingerprint:",
            value=state.oci_config[profile]["fingerprint"],
            key="oci_fingerprint",
        )
        tenancy = st.text_input(
            "Tenancy OCID:",
            value=state.oci_config[profile]["tenancy"],
            key="oci_tenancy",
        )
        region = st.text_input(
            "Region:",
            value=state.oci_config[profile]["region"],
            help="Region of Source Bucket",
            key="oci_region",
        )
        key_file = st.text_input(
            "Key File:",
            value=state.oci_config[profile]["key_file"],
            key="oci_key_file",
        )
        if not state.oci_config[profile]["namespace"]:
            st.error("Current Status: Unverified")
            if "oci_error" in state:
                st.error(f"Unable to perform update: {state.oci_error}", icon="🚨")
        else:
            st.success(f"Current Status: Validated - Namespace: {state.oci_config[profile]['namespace']}")

        if st.form_submit_button(label="Save"):
            security_token_file = None if not token_auth else security_token_file
            user = None if token_auth else user
            if not (fingerprint and tenancy and region and key_file and (user or security_token_file)):
                st.error("All fields are required.", icon="❌")
                st.stop()
            patch_oci(profile, user, fingerprint, tenancy, region, key_file, security_token_file)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
