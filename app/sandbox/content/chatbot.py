"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

Session States Set:
- sandbox_client: Stores the SandboxClient
"""
# spell-checker:ignore streamlit

import asyncio
import inspect

import streamlit as st
from streamlit import session_state as state

import sandbox.utils.st_common as st_common
import sandbox.utils.client as client
import common.logging_config as logging_config

from sandbox.content.config.models import get as get_model_data
from sandbox.content.tools.prompt_eng import get_prompt_text

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
    get_model_data(model_type="ll", enabled=True)
    available_models = list(state.ll_model_enabled.keys())
    if not available_models:
        st.error("No language models are configured and/or enabled. Disabling Chatbot.", icon="❌")
        st.stop()

    st_common.history_sidebar()
    st_common.ll_sidebar()

    #########################################################################
    # Chatty-Bot Centre
    #########################################################################
    # Establish the SandboxClient
    if "sandbox_client" not in state:
        state.sandbox_client = client.SandboxClient(
            server=state.server,
            settings=state["user_settings"],
            sys_prompt=get_prompt_text("sys", state["user_settings"]["prompts"]["sys"]),
            ctx_prompt=get_prompt_text("ctx", state["user_settings"]["prompts"]["ctx"]),
            timeout=10
            )
    sandbox_client: client.SandboxClient = state.sandbox_client

    history = await sandbox_client.get_history()
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
            ai_response = await sandbox_client.completions(message=human_request)
            st.chat_message("ai").write(ai_response.choices[0].message.content)
        except Exception as ex:
            logger.error("Exception:", exc_info=1)
            st.chat_message("ai").write(f"I'm sorry, something's gone wrong: {ex}")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    asyncio.run(main())
