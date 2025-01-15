"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

Script initializes a web interface for Oracle Cloud Infrastructure (OCI)
It includes a form to input and test OCI API Access.
"""
# spell-checker:ignore streamlit, ocid

import inspect

import modules.logging_config as logging_config
import modules.utilities as utilities

import streamlit as st
from streamlit import session_state as state

logger = logging_config.logging.getLogger("oci_config")


#####################################################
# Functions
#####################################################
def initialize_streamlit():
    """
    Initialize Oracle Cloud Infrastructure (OCI) configuration settings
    This should only be run when state.oci_configured is not defined
    """
    if "oci_configured" in state:
        return

    logger.info("Initializing OCI Configuration")
    if "oci_config" not in state:
        state.oci_config = utilities.oci_initialize()
    try:
        utilities.oci_get_namespace(state.oci_config, retries=False)
        state.oci_configured = True
    except utilities.OciException as ex:
        logger.exception(ex, exc_info=False)
        state.oci_configured = False


#####################################################
# MAIN
#####################################################
def main():
    """Streamlit GUI"""
    initialize_streamlit()
    # TODO(gotsysdba) Add input for File and Profile

    auth_sources = ["User", "Token"]
    auth_index = auth_sources.index("Token") if state.oci_config["security_token_file"] else 0
    auth_source = st.radio(
        "OCI Authentication:",
        auth_sources,
        horizontal=True,
        index=auth_index,
        key="radio_auth_source",
    )
    oci_user_auth = auth_source != "Token"
    if oci_user_auth:
        state.oci_config["security_token_file"] = None
    else:
        state.oci_config["user"] = None

    with st.form("OCI API Configuration"):
        user = st.text_input(
            "User OCID:",
            value=state.oci_config["user"],
            disabled=not oci_user_auth,
            key="text_input_user",
        )
        security_token_file = st.text_input(
            "Security Token File:",
            value=state.oci_config["security_token_file"],
            disabled=oci_user_auth,
            key="text_input_security_token_file",
        )
        fingerprint = st.text_input(
            "Fingerprint:",
            value=state.oci_config["fingerprint"],
            key="text_input_fingerprint",
        )
        tenancy = st.text_input("Tenancy OCID:", value=state.oci_config["tenancy"], key="text_input_tenancy")
        region = st.text_input(
            "Region:",
            value=state.oci_config["region"],
            help="Region of Source Bucket",
            key="text_input_region",
        )
        key_file = st.text_input("Key File:", value=state.oci_config["key_file"], key="text_input_key_file")
        compartment_id = st.text_input("Compartment ID:", value=state.oci_config["compartment_id"], key="text_input_compartment_id")

        if st.form_submit_button(label="Save"):
            print("I'm Here!")
            st.empty()
            if oci_user_auth:
                security_token_file = None
            if not oci_user_auth:
                user = None
            if not (fingerprint and tenancy and region and key_file and (user or security_token_file)):
                st.error("All fields are required.", icon="❌")
                state.oci_configured = False
                st.stop()

            try:
                test_config = utilities.oci_initialize(
                    user, fingerprint, tenancy, region, key_file, security_token_file
                )
                logger.debug("Testing OCI config: %s", test_config)
                utilities.oci_get_namespace(test_config, retries=False)
                st.success("OCI API Authentication Tested Successfully", icon="✅")
                state.oci_config = test_config
                st.success("OCI Configuration Saved", icon="✅")
                state.oci_configured = True
            except utilities.OciException as ex:
                logger.exception(ex, exc_info=False)
                st.error(ex, icon="🚨")
                state.oci_configured = False


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
