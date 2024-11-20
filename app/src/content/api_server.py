"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# spell-checker:ignore streamlit, langchain, llms

import inspect
import time
import threading

# Streamlit
import streamlit as st
from streamlit import session_state as state

# Utilities
import modules.st_common as st_common
import modules.api_server as api_server
import modules.logging_config as logging_config

# History
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

logger = logging_config.logging.getLogger("api_server")


#############################################################################
# Functions
#############################################################################
def initialize_streamlit():
    """initialize Streamlit Session State"""
    if "api_server_config" not in state:
        state.api_server_config = api_server.config()
        logger.info("initialized API Server Config")


def display_logs():
    try:
        while "server_thread" in st.session_state:
            try:
                # Retrieve log from queue (non-blocking)
                msg = api_server.log_queue.get_nowait()
                logger.info("API Msg: %s", msg)
                if "message" in msg:
                    st.chat_message("human").write(msg["message"])
                else:
                    if state.rag_params["enable"]:
                        logger.info("msg[\"answer\"]")
                        logger.info(msg)
                        st.chat_message("ai").write(msg)
                        if "context" in msg and msg["context"]:
                            st_common.show_rag_refs(msg["context"])
                    else:
                        st.chat_message("ai").write(msg.content)
            except api_server.queue.Empty:
                time.sleep(0.1)  # Avoid busy-waiting
    finally:
        logger.info("API Server events display has stopped.")


def api_server_start():
    chat_history = StreamlitChatMessageHistory(key="api_chat_history")
    if "user_api_server_port" in state:
        state.api_server_config["port"] = state.user_api_server_port
    if "user_api_server_key" in state:
        state.api_server_config["key"] = state.user_api_server_key
    if "user_chat_history" not in state:
        state.user_chat_history = True
    if "initialized" in state and state.initialized:
        if "server_thread" not in state:
            try:
                state.httpd = api_server.run_server(
                    state.api_server_config["port"],
                    state.chat_manager,
                    state.rag_params,
                    state.lm_instr,
                    state.context_instr,
                    state.api_server_config["key"],
                    chat_history,
                    state.user_chat_history,
                )

                # Start the server in the thread
                def api_server_process(httpd):
                    httpd.serve_forever()

                state.server_thread = threading.Thread(
                    target=api_server_process,
                    # Trailing , ensures tuple is passed
                    args=(state.httpd,),
                    daemon=True,
                )
                state.server_thread.start()
                logger.info("Started API Server on port: %i", state.api_server_config["port"])
            except OSError:
                if not state.api_server_config["auto_start"]:
                    st.error("Port is already in use.")
        else:
            st.warning("API Server is already running.")
    else:
        logger.warning("Unable to start API Server; ChatMgr not configured")
        st.warning("Failed to start API Server: Chatbot not initialized.")


def api_server_stop():
    if "server_thread" in state:
        if state.server_thread.is_alive():
            state.httpd.shutdown()  # Shut down the server
            state.server_thread.join()  # Wait for the thread to exit

            del state.server_thread  # Clean up the thread reference
            del state.httpd  # Clean up the server reference

            logger.info("API Server stopped successfully.")
            st.success("API Server stopped successfully.")
        else:
            logger.warning("API Server thread is not running - cleaning up.")
            st.warning("API Server thread is not running.")
            del state.server_thread
    else:
        logger.info("Unable to stop API Server - not running.")


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    st.header("API Server")
    # Initialize RAG
    st_common.initialize_rag()
    # Setup History
    chat_history = StreamlitChatMessageHistory(key="api_chat_history")

    #########################################################################
    # Sidebar Settings
    #########################################################################
    enabled_llms = sum(model_info["enabled"] for model_info in state.ll_model_config.values())
    if enabled_llms > 0:
        initialize_streamlit()
        enable_history = st.sidebar.checkbox(
            "Enable History and Context?",
            value=True,
            key="user_chat_history",
        )
        if st.sidebar.button("Clear History", disabled=not enable_history):
            chat_history.clear()
        st.sidebar.divider()
        ll_model = st_common.lm_sidebar()
        st_common.rag_sidebar()
    else:
        st.error("No chat models are configured and/or enabled.", icon="🚨")
        st.stop()

    #########################################################################
    # Main
    #########################################################################
    if "initialized" not in state:
        api_server_stop()
        if not state.rag_params["enable"] or all(
            state.rag_params[key] for key in ["model", "chunk_size", "chunk_overlap", "distance_metric"]
        ):
            try:
                state.chat_manager = st_common.initialize_chatbot(ll_model)
                state.initialized = True
                st_common.update_rag()
                logger.debug("Force rerun to save state")
                st.rerun()
            except Exception as ex:
                logger.exception(ex, exc_info=False)
                st.error(f"Failed to initialize the chat client: {ex}")
                st_common.clear_initialized()
                if st.button("Retry", key="retry_initialize"):
                    st.rerun()
                st.stop()
        else:
            st.error("Not all required RAG options are set, please review or disable RAG.")
            st.stop()

    server_running = False
    if "server_thread" in state:
        server_running = True
    elif state.api_server_config["auto_start"]:
        server_running = True

    left, right = st.columns([0.2, 0.8])
    left.number_input(
        "API Server Port:",
        value=state.api_server_config["port"],
        min_value=1,
        max_value=65535,
        key="user_api_server_port",
        disabled=server_running,
    )

    right.text_input(
        "API Server Key:",
        type="password",
        value=state.api_server_config["key"],
        key="user_api_server_key",
        disabled=server_running,
    )

    if state.api_server_config["auto_start"]:
        api_server_start()
        st.success("API Server automatically started.")
    else:
        if server_running:
            st.button("Stop Server", type="primary", on_click=api_server_stop)
        else:
            st.button("Start Server", type="primary", on_click=api_server_start)

    #########################################################################
    # API Server Centre
    #########################################################################
    if "server_thread" in state:
        st.subheader("Activity")
        with st.container(border=True):
            display_logs()


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
