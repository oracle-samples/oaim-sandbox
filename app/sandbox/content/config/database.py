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

import common.schema as schema
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.config.database")

# Set endpoint if server has been established
API_ENDPOINT = None
if "server" in state:
    API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/databases"


#####################################################
# Functions
#####################################################
def get() -> dict[str, dict]:
    """Get a dictionary of all Databases"""
    if "database_config" not in state or state["database_config"] == dict():
        try:
            response = api_call.get(url=API_ENDPOINT, token=state.server["key"])
            state["database_config"] = {
                item["name"]: {k: v for k, v in item.items() if k != "name"} for item in response
            }
            logger.info("State created: state['database_config']")
        except api_call.SandboxError as ex:
            st.error(f"Unable to retrieve databases: {ex}", icon="🚨")
            state["database_config"] = dict()


def patch(name: str, user: str, password: str, dsn: str, wallet_password: str) -> None:
    """Update Database"""
    # Check if the database configuration is changed, or if not ACTIVE
    if (
        state.database_config[name]["user"] != user
        or state.database_config[name]["password"] != password
        or state.database_config[name]["dsn"] != dsn
        or state.database_config[name]["wallet_password"] != wallet_password
        or state.database_config[name]["status"] != "ACTIVE"
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
            get()  # Refresh the Config
        except api_call.SandboxError as ex:
            logger.error("Database Update failed: %s", ex)
            st.error(f"Unable to perform update: {ex}", icon="🚨")
    else:
        st.info(f"{name} Database Configuration - No Changes Required.", icon="ℹ️")


#####################################################
# MAIN
#####################################################
def main() -> None:
    """Streamlit GUI"""
    st.header("Database")
    st.write("Configure the database vector storage.")
    get()  # Create/Rebuild state

    name = "DEFAULT"
    st.subheader(f"{name} Configuration")
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
        if state.database_config[name]["status"] != "ACTIVE":
            st.error(f"Current Status: {state.database_config[name]['status']}")

        if st.form_submit_button("Save"):
            if not user or not password or not dsn:
                st.error("Username, Password and Connect String fields are required.", icon="❌")
                st.stop()
            patch(name, user, password, dsn, wallet_password)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
