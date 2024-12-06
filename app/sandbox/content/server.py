"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, oaim

import os
import inspect

import streamlit as st
from streamlit import session_state as state

import oaim_server
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.content.server")


#####################################################
# Functions
#####################################################
def initialize() -> None:
    """initialize Streamlit Session State"""
    if "server" not in state:
        logger.info("Initializing state.server")
        state.server = {"url": os.getenv("API_SERVER_URL", "http://localhost")}
        state.server["port"] = int(os.getenv("API_SERVER_PORT", "8000"))
        state.server["pid"] = oaim_server.start_server(state.server["port"])
        state.server["key"] = os.getenv("API_SERVER_KEY")

def server_restart() -> None:
    os.environ["API_SERVER_KEY"] = state.user_server_key
    state.server["port"] = state.user_server_port
    state.server["key"] = os.getenv("API_SERVER_KEY")

    oaim_server.stop_server(state.server["pid"])
    state.server["pid"] = oaim_server.start_server(state.server["port"])
    state.pop('sever_client', None)


#####################################################
# MAIN
#####################################################
def main() -> None:
    """Streamlit GUI"""
    initialize()
    st.header("API Server")

    left, right = st.columns([0.2, 0.8])
    left.number_input(
        "API Server Port:",
        value=state.server["port"],
        key="user_server_port",
        min_value=1,
        max_value=65535,
    )
    right.text_input(
        "API Server Key:",
        value=state.server["key"],
        key="user_server_key",
        type="password",
    )
    st.button("Restart Server", type="primary", on_click=server_restart)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
