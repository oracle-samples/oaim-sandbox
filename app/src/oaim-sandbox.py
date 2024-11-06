"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# pylint: disable=invalid-name
# spell-checker:ignore streamlit, oaim, testid

import os

# Streamlit
import streamlit as st
from streamlit import session_state as state

# Utilities
import modules.logging_config as logging_config

# Configuration
from content.model_config import initialize_streamlit as model_initialize
from content.db_config import initialize_streamlit as db_initialize
from content.prompt_eng import initialize_streamlit as prompt_initialize
from content.oci_config import initialize_streamlit as oci_initialize
import content.api_server as api_server_content

logger = logging_config.logging.getLogger("sandbox")

os.environ["USER_AGENT"] = "OAIM-SANDBOX"
os.environ["GSK_DISABLE_SENTRY"] = "true"
os.environ["GSK_DISABLE_ANALYTICS"] = "true"


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    st.set_page_config(layout="wide")
    # initialize Components
    db_initialize()
    model_initialize()
    prompt_initialize()
    oci_initialize()
    api_server_content.initialize_streamlit()

    # Setup rag_params into state enable as default
    if "rag_params" not in state:
        state.rag_params = {"enable": True}
    if "rag_user_idx" not in state:
        state.rag_user_idx = {}
    if "rag_filter" not in state:
        state.rag_filter = {}

    # Start the API server
    if state.api_server_config["auto_start"]:
        api_server_content.api_server_start()
    if "user_chat_history" not in state:
        state.user_chat_history = True

    # GUI Defaults
    css = """
    <style>
        section[data-testid="stSidebar"] div.stButton button {
            width: 100%;
        }
        img[data-testid="stLogo"] {
            width: 100%;
            height: auto;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    st.logo("images/logo_light.png")

    # Enable/Disable Functionality
    state.disable_api = os.environ.get("DISABLE_API", "false").lower() == "true"
    state.disable_tools = os.environ.get("DISABLE_TOOLS", "false").lower() == "true"
    state.disable_tests = os.environ.get("DISABLE_TESTS", "false").lower() == "true" and not state.disable_tools
    state.disable_admin = os.environ.get("DISABLE_ADMIN", "false").lower() == "true" and not state.disable_tools
    state.disable_oci = os.environ.get("DISABLE_OCI", "false").lower() == "true" and not state.disable_admin

    # Left Hand Side - Navigation
    chatbot = st.Page("content/chatbot.py", title="ChatBot", icon="💬", default=True)
    navigation = {
        "": [chatbot],
    }
    if not state.disable_tests:
        test_framework = st.Page("content/test_framework.py", title="Test Framework", icon="🧪")
        navigation[""].append(test_framework)
    if not state.disable_api:
        api_server = st.Page("content/api_server.py", title="API Server", icon="📡")
        navigation[""].append(api_server)

    # Tools
    if not state.disable_tools:
        prompt_eng = st.Page("content/prompt_eng.py", title="Prompts", icon="🎤")
        navigation["Tools"] = [prompt_eng]
    # Administration
    if not state.disable_tools and not state.disable_admin:
        # Define Additional Pages
        split_embed = st.Page("content/split_embed.py", title="Split/Embed", icon="📚")
        model_config = st.Page("content/model_config.py", title="Models", icon="🤖")
        db_config = st.Page("content/db_config.py", title="Database", icon="🗄️")
        settings = st.Page("content/settings.py", title="Settings", icon="💾")
        # Update Navigation
        navigation["Tools"].insert(0, split_embed)
        navigation["Configuration"] = [model_config]
        navigation["Configuration"].append(db_config)
        navigation["Configuration"].append(settings)
        if not state.disable_oci:
            oci_config = st.Page("content/oci_config.py", title="OCI", icon="☁️")
            navigation["Configuration"].insert(2, oci_config)

    pg = st.navigation(navigation, position="sidebar", expanded=False)
    pg.run()


if __name__ == "__main__":
    main()
