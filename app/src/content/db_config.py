"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes a web interface for database configuration using Streamlit (`st`).
It includes a form to input and test database connection settings.
"""

import inspect

import modules.logging_config as logging_config
import modules.db_utils as db_utils
import modules.st_common as st_common

import streamlit as st
from streamlit import session_state as state

logger = logging_config.logging.getLogger("db_config")


#####################################################
# Functions
#####################################################
def initialise_streamlit():
    """Initialise the database configuration settings into Streamlit state"""
    if "db_configured" in state:
        return

    state.db_config = db_utils.initialise()
    try:
        db_utils.connect(state.db_config)
        state.db_configured = True
    except db_utils.oracledb.DatabaseError as ex:
        state.db_configured = False
        logger.info("Unable to initialise database: %s", ex, exc_info=False)


#####################################################
# MAIN
#####################################################
def main():
    """Streamlit GUI"""
    initialise_streamlit()
    with st.form("Database Connectivity"):
        user = st.text_input(
            "Database User:",
            key="text_input_user",
            value=state.db_config["user"],
        )
        password = st.text_input(
            "Database Password:",
            type="password",
            key="text_input_password",
            value=state.db_config["password"],
        )
        dsn = st.text_input(
            "Database Connect String:",
            key="text_input_dsn",
            value=state.db_config["dsn"],
        )
        wallet_password = st.text_input(
            "Wallet Password (Optional):",
            type="password",
            key="text_input_wallet_password",
            value=state.db_config["wallet_password"],
        )
        if st.form_submit_button("Save"):
            if not user or not password or not dsn:
                st.error("Username, Password and Connect String fields are required.", icon="❌")
                state.db_configured = False
                st.stop()

            try:
                test_config = db_utils.initialise(user, password, dsn, wallet_password)
                db_utils.connect(test_config)
                st.success("Database Connectivity Tested Successfully", icon="✅")
                state.db_config = test_config
                st.success("Database Configuration Saved", icon="✅")
                state.db_configured = True
                st_common.reset_rag()
            except db_utils.oracledb.DatabaseError as ex:
                st.error(ex, icon="🚨")
                state.db_configured = False


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
