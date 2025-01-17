"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

Session States Set:
- user_settings: Stores all user settings
"""
# spell-checker:ignore streamlit, scriptrunner, oaim

import os

import streamlit as st
from streamlit import session_state as state

from sandbox.utils import api_call
from sandbox.content import server
from common.functions import client_gen_id

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("oaim_sandbox")


#############################################################################
# MAIN
#############################################################################
def main() -> None:
    """Streamlit GUI"""
    st.set_page_config(
        page_title="AI Microservices Sandbox",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://oracle-samples.github.io/oaim-sandbox/",
            "Report a bug": "https://github.com/oracle-samples/oaim-sandbox/issues/new",
        },
    )
    st.html(
        """
        <style>
        img[data-testid="stLogo"] {
            width: 100%;
            height: auto;
        }
        </style>
        """,
    )
    st.logo("sandbox/media/logo_light.png")

    # Setup Settings State
    api_endpoint = f"{state.server['url']}:{state.server['port']}/v1/settings"
    if "user_settings" not in state:
        try:
            state.user_settings = api_call.post(url=api_endpoint, params={"client": client_gen_id()})["data"]
        except api_call.ApiError as ex:
            st.error(ex, icon="🚨")
    if "server_settings" not in state:
        try:
            state.server_settings = api_call.get(url=api_endpoint, params={"client": "server"})["data"]
        except api_call.ApiError as ex:
            st.error(ex, icon="🚨")

    # Enable/Disable Functionality
    state.disabled = {}
    state.disabled["api"] = os.environ.get("DISABLE_API", "false").lower() == "true"
    state.disabled["tools"] = os.environ.get("DISABLE_TOOLS", "false").lower() == "true"
    state.disabled["tests"] = (
        os.environ.get("DISABLE_TESTS", "false").lower() == "true" and not state.disabled["tools"]
    )
    state.disabled["admin"] = (
        os.environ.get("DISABLE_ADMIN", "false").lower() == "true" and not state.disabled["tools"]
    )
    state.disabled["oci"] = os.environ.get("DISABLE_OCI", "false").lower() == "true" and not state.disabled["admin"]

    # Left Hand Side - Navigation
    chatbot = st.Page("sandbox/content/chatbot.py", title="ChatBot", icon="💬", default=True)
    navigation = {
        "": [chatbot],
    }
    if not state.disabled["tests"]:
        testbed = st.Page("sandbox/content/testbed.py", title="Testbed", icon="🧪")
        navigation[""].append(testbed)
    if not state.disabled["api"]:
        api_server = st.Page("sandbox/content/server.py", title="API Server", icon="📡")
        navigation[""].append(api_server)

    # Tools
    if not state.disabled["tools"]:
        prompt_eng = st.Page("sandbox/content/tools/prompt_eng.py", title="Prompts", icon="🎤")

        navigation["Tools"] = [prompt_eng]
    # Administration
    if not state.disabled["tools"] and not state.disabled["admin"]:
        # Define Additional Pages
        split_embed = st.Page("sandbox/content/tools/split_embed.py", title="Split/Embed", icon="📚")
        model_config = st.Page("sandbox/content/config/models.py", title="Models", icon="🤖")
        db_config = st.Page("sandbox/content/config/database.py", title="Database", icon="🗄️")
        settings = st.Page("sandbox/content/config/settings.py", title="Settings", icon="💾")
        # Update Navigation
        navigation["Tools"].insert(0, split_embed)
        navigation["Configuration"] = [db_config]
        navigation["Configuration"].append(model_config)
        navigation["Configuration"].append(settings)
        if not state.disabled["oci"]:
            oci_config = st.Page("sandbox/content/config/oci.py", title="OCI", icon="☁️")
            navigation["Configuration"].insert(2, oci_config)

    pg = st.navigation(navigation, position="sidebar", expanded=False)
    pg.run()


if __name__ == "__main__":
    server.initialize()
    main()
