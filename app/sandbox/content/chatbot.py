"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

Session States Set:
- user_client: Stores the SandboxClient
"""

# spell-checker:ignore streamlit
import asyncio
import inspect

import streamlit as st
from streamlit import session_state as state

import sandbox.utils.st_common as st_common
import sandbox.utils.client as client
from sandbox.content.config.models import get_model
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("content.chatbot")
#############################################################################
# Functions
#############################################################################


#############################################################################
# MAIN
#############################################################################
async def main() -> None:
    """Streamlit GUI"""

    #########################################################################
    # Sidebar Settings
    #########################################################################
    # Get a list of available language models, if none, then stop
    get_model(model_type="ll", only_enabled=True)
    available_ll_models = list(state.ll_model_enabled.keys())
    if not available_ll_models:
        st.error("No language models are configured and/or enabled. Disabling Sandbox.", icon="❌")
        st.stop()
    # the sidebars will set this to False if not everything is configured.
    state.enable_sandbox = True
    st_common.history_sidebar()
    st_common.ll_sidebar()
    st_common.rag_sidebar()
    # Stop when sidebar configurations not set
    if not state.enable_sandbox:
        st.stop()

    #########################################################################
    # Chatty-Bot Centre
    #########################################################################
    # Establish the SandboxClient
    if "user_client" not in state:
        state.user_client = client.SandboxClient(
            server=state.server,
            settings=state["user_settings"],
            timeout=600,
        )
    user_client: client.SandboxClient = state.user_client

    history = await user_client.get_history()
    if len(history) == 1:
        with st.chat_message("ai"):
            # Do not put this in the history as messages must alternate human/ai
            st.write("Hello, how can I help you?")
    for message in history:
        if message["role"] in ("ai", "assistant"):
            st.chat_message("ai").write(message["content"])
        elif message["role"] in ("human", "user"):
            st.chat_message("human").write(message["content"])

    sys_prompt = state["user_settings"]["prompts"]["sys"]
    if human_request := st.chat_input(f"Ask your question here... (current prompt: {sys_prompt})"):
        st.chat_message("human").write(human_request)
        try:
            ai_response = await user_client.completions(message=human_request)
            st.chat_message("ai").write(ai_response.choices[0].message.content)
        except Exception:
            logger.error("Exception:", exc_info=1)
            st.chat_message("ai").write(
                """
                I'm sorry, something's gone wrong.  Please try again.
                If the problem persists, please raise an issue.
                """
            )
            if st.button("Retry", key="reload_chatbot"):
                st_common.clear_state_key("user_client")
                st.rerun()


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    try:
        asyncio.run(main())
    except ValueError as ex:
        logger.exception("Bug detected: %s", ex)
        st.error("It looks like you found a bug; please open an issue", icon="🚨")
        st.stop()
    except IndexError as ex:
        logger.exception("Unable to contact the server: %s", ex)
        st.error("Unable to contact the server, is it running?", icon="🚨")
        if st.button("Retry", key="reload_chatbot"):
            st_common.clear_state_key("user_client")
            st.rerun()
