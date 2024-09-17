"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import os

# Streamlit
import streamlit as st
from streamlit import session_state as state

# Utilities
import modules.logging_config as logging_config

# Configuration
from content.model_config import initialise_streamlit as model_initialise
from content.db_config import initialise_streamlit as db_initialise
from content.prompt_eng import initialise_streamlit as prompt_initialise
from content.oci_config import initialise_streamlit as oci_initialise

logger = logging_config.logging.getLogger("sandbox")

os.environ["USER_AGENT"] = "OAIM-SANDBOX"


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    # Initialise Components
    db_initialise()
    model_initialise()
    prompt_initialise()
    oci_initialise()

    # Setup rag_params into state enable as default
    if "rag_params" not in state:
        state.rag_params = {"enable": True}
    if "rag_user_idx" not in state:
        state.rag_user_idx = {}
    if "rag_filter" not in state:
        state.rag_filter = {}

    # GUI Defaults
    css = """
    <style>
        section.main > div {max-width:65rem}
        section[data-testid="stSidebar"] div.stButton button {
            width: 100%;
        }
        img[data-testid="stLogo"] {
            width: 10.5rem;
            height: 100%;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    st.logo("images/logo_light.png")

    # Page Definition
    state.disable_tools = os.environ.get("DISABLE_TOOLS", "false").lower() == "true"
    state.disable_tests = os.environ.get("DISABLE_TESTS", "false").lower() == "true" and not state.disable_tools
    state.disable_admin = os.environ.get("DISABLE_ADMIN", "false").lower() == "true" and not state.disable_tools
    state.disable_oci = os.environ.get("DISABLE_OCI", "false").lower() == "true" and not state.disable_admin

    chatbot = st.Page("content/chatbot.py", title="ChatBot", icon="🏠", default=True)
    navigation = {
        "": [chatbot],
    }
    if not state.disable_tests:
        test_framework = st.Page("content/test_framework.py", title="Test Framework", icon="🧪")
        navigation[""].append(test_framework)

    # Tools
    if not state.disable_tools:
        prompt_eng = st.Page("content/prompt_eng.py", title="Prompts", icon="🎤")
        navigation["Tools"] = [prompt_eng]

    # Administration
    import_settings = st.Page("content/import_settings.py", title="Import Settings", icon="💾")
    navigation["Configuration"] = [import_settings]
    if not state.disable_tools and not state.disable_admin:
        # Define Additional Pages
        split_embed = st.Page("content/split_embed.py", title="Split/Embed", icon="📚")
        model_config = st.Page("content/model_config.py", title="Models", icon="🤖")
        db_config = st.Page("content/db_config.py", title="Database", icon="🗄️")
        # Update Navigation
        navigation["Tools"].insert(0, split_embed)
        navigation["Configuration"].insert(0, model_config)
        navigation["Configuration"].insert(1, db_config)
        if not state.disable_oci:
            oci_config = st.Page("content/oci_config.py", title="OCI", icon="☁️")
            navigation["Configuration"].insert(2, oci_config)

    pg = st.navigation(navigation)
    pg.run()


if __name__ == "__main__":
    main()
