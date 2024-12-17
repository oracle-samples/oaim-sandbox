"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes a web interface for database configuration using Streamlit (`st`).
It includes a form to input and test database connection settings.
"""
# spell-checker:ignore streamlit, selectbox

import inspect

import streamlit as st
from streamlit import session_state as state

import sandbox.utils.api_call as api_call
import sandbox.utils.st_common as st_common

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.config.database")

# Set endpoint if server has been established
API_ENDPOINT = None
if "server" in state:
    API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/databases"

#####################################################
# Functions
#####################################################
def get_databases() -> dict[str, dict]:
    """Get a dictionary of all Databases and store Vector Store Tables"""
    if "database_config" not in state or state["database_config"] == dict():
        try:
            response = api_call.get(url=API_ENDPOINT, token=state.server["key"])
            state["database_config"] = {
                item["name"]: {k: v for k, v in item.items() if k != "name"} for item in response
            }
            logger.info("State created: state['database_config']")
        except api_call.ApiError as ex:
            st.error(f"Unable to retrieve databases: {ex}", icon="🚨")
            state["database_config"] = dict()

def patch_database(name: str, user: str, password: str, dsn: str, wallet_password: str) -> None:
    """Update Database"""
    # Check if the database configuration is changed, or if not CONNECTED
    if (
        state.database_config[name]["user"] != user
        or state.database_config[name]["password"] != password
        or state.database_config[name]["dsn"] != dsn
        or state.database_config[name]["wallet_password"] != wallet_password
        or state.database_config[name]["status"] != "CONNECTED"
    ):
        try:
            api_call.patch(
                url=API_ENDPOINT + "/" + name,
                body={
                    "data": {
                        "user": user,
                        "password": password,
                        "dsn": dsn,
                        "wallet_password": wallet_password,
                    }
                },
                token=state.server["key"],
            )
            st.success(f"{name} Database Configuration - Updated", icon="✅")
            st_common.clear_state_key("database_config")
            st.rerun()
        except api_call.ApiError as ex:
            logger.error("Database Update failed: %s", ex)
            st.error(f"Unable to perform update: {ex}", icon="🚨")
    else:
        st.info(f"{name} Database Configuration - No Changes Detected.", icon="ℹ️")


#####################################################
# MAIN
#####################################################
def main() -> None:
    """Streamlit GUI"""
    st.header("Database")
    st.write("Configure the database used for vector storage.")
    try:
        get_databases()  # Create/Rebuild state
    except api_call.ApiError:
        st.stop()

    name = "DEFAULT"
    st.subheader("Configuration")
    with st.form("update_database_config"):
        user = st.text_input(
            "Database User:",
            value=state.database_config[name]["user"],
            key="database_user",
        )
        password = st.text_input(
            "Database Password:",
            value=state.database_config[name]["password"],
            key="database_password",
            type="password",
        )
        dsn = st.text_input(
            "Database Connect String:",
            value=state.database_config[name]["dsn"],
            key="database_dsn",
        )
        wallet_password = st.text_input(
            "Wallet Password (Optional):",
            value=state.database_config[name]["wallet_password"],
            key="database_wallet_password",
            type="password",
        )
        if state.database_config[name]["status"] != "CONNECTED":
            st.error(f"Current Status: {state.database_config[name]['status']}")
        else:
            st.success(f"Current Status: {state.database_config[name]['status']}")
        if st.form_submit_button("Save"):
            if not user or not password or not dsn:
                st.error("Username, Password and Connect String fields are required.", icon="❌")
                st.stop()
            patch_database(name, user, password, dsn, wallet_password)

    if state.database_config[name]["status"] == "CONNECTED":
        st.subheader("Database Vector Storage")
        if state.database_config[name]["vector_stores"]:
            table_col_format = st.columns([0.02, 0.05, 0.1, 0.05, 0.05, 0.05, 0.04])
            col1, col2, col3, col4, col5, col6, col7 = table_col_format
            col1.markdown("**<u>&nbsp;</u>**", unsafe_allow_html=True)
            col2.markdown("**<u>Alias</u>**", unsafe_allow_html=True)
            col3.markdown("**<u>Model</u>**", unsafe_allow_html=True)
            col4.markdown("**<u>Chunk Size</u>**", unsafe_allow_html=True)
            col5.markdown("**<u>Chunk Overlap</u>**", unsafe_allow_html=True)
            col6.markdown("**<u>Distance Metric</u>**", unsafe_allow_html=True)
            col7.markdown("**<u>Index Type</u>**", unsafe_allow_html=True)
            for vs in state.database_config[name]["vector_stores"]:
                vector_store = vs["vector_store"].lower()
                col1.button(
                    "",
                    icon="🗑️",
                    key=f"vector_stores_{vector_store}",
                )
                col2.text_input(
                    "Alias",
                    value=vs["alias"],
                    label_visibility="collapsed",
                    key=f"vector_stores_{vector_store}_alias",
                    disabled=True,
                )
                col3.text_input(
                    "Model",
                    value=vs["model"],
                    label_visibility="collapsed",
                    key=f"vector_stores_{vector_store}_model",
                    disabled=True,
                )
                col4.text_input(
                    "Chunk Size",
                    value=vs["chunk_size"],
                    label_visibility="collapsed",
                    key=f"vector_stores_{vector_store}_chunk_size",
                    disabled=True,
                )
                col5.text_input(
                    "Chunk Overlap",
                    value=vs["chunk_overlap"],
                    label_visibility="collapsed",
                    key=f"vector_stores_{vector_store}_chunk_overlap",
                    disabled=True,
                )
                col6.text_input(
                    "Distance Metric",
                    value=vs["distance_metric"],
                    label_visibility="collapsed",
                    key=f"vector_stores_{vector_store}_distance_metric",
                    disabled=True,
                )
                col7.text_input(
                    "Index Type",
                    value=vs["index_type"],
                    label_visibility="collapsed",
                    key=f"vector_stores_{vector_store}_index_type",
                    disabled=True,
                )
        else:
            st.write("No Vector Stores Found")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
