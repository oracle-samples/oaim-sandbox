"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, langchain

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from urllib.parse import urlparse
import streamlit as st
from streamlit import session_state as state

# Utilities
import modules.logging_config as logging_config
import modules.chatbot as chatbot

from langchain_community.chat_message_histories import StreamlitChatMessageHistory

logger = logging_config.logging.getLogger("modules.chatbot_server")


def get_answer_fn(
    question: str, history=None, chat_manager=None, rag_params=None, lm_instr=None, context_instr=None
) -> str:
    """Send for completion"""
    # Format appropriately the history for your RAG agent
    chat_history_empty = StreamlitChatMessageHistory(key="empty")
    chat_history_empty.clear()
    if history:
        for h in history:
            if h["role"] == "assistant":
                chat_history_empty.add_ai_message(h["content"])
            else:
                chat_history_empty.add_user_message(h["content"])

    answer = chatbot.generate_response(
        chat_manager,
        question,
        chat_history_empty,
        False,
        rag_params,
        lm_instr,
        context_instr,
    )
    return answer["answer"]


class ChatbotHTTPRequestHandler(BaseHTTPRequestHandler):
    """Handler for mini-chatbot"""

    def __init__(
        self, *args, chat_manager=None, rag_params=None, lm_instr=None, context_instr=None, api_key=None, **kwargs
    ):
        self.chat_manager = chat_manager
        self.rag_params = rag_params
        self.lm_instr = lm_instr
        self.context_instr = context_instr
        self.api_key = api_key
        super().__init__(*args, **kwargs)

    def do_OPTIONS(self):  # pylint: disable=invalid-name
        # Send a 200 OK response for the OPTIONS request
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_POST(self):  # pylint: disable=invalid-name
        expected_api_key = "Bearer " + self.api_key
        # Parse query parameters
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/v1/chat/completions":
            auth_header = self.headers.get("Authorization")

            logger.info("Request Method: %s", self.command)
            logger.info("Path: %s", self.path)
            logger.info("HTTP Version: %s", self.request_version)
            logger.info("Authorization Header: %s", auth_header)

            if expected_api_key == auth_header:
                for header, value in self.headers.items():
                    logger.info("Header: %s = %s", header, value)

                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length).decode("utf-8")
                # Log the raw body
                logger.info("Raw Body: %s", post_data)
                try:
                    # Parse the POST data as JSON
                    post_json = json.loads(post_data)

                    # Extract the 'message' field from the JSON
                    message = post_json.get("message")

                    if message:
                        # Log the incoming message
                        logger.info("MSG to Chatbot API: %s", message)

                        # Call your function to get the chatbot response
                        answer = get_answer_fn(
                            message, None, self.chat_manager, self.rag_params, self.lm_instr, self.context_instr
                        )

                        logger.info("MSG from Chatbot API: %s", answer)

                        # Prepare the response as JSON
                        response = {"choices": [{"message": {"content": answer}}]}
                        self.send_response(200)
                    else:
                        # If no message is provided, return an error
                        response = {"error": "No 'message' field found in request."}
                        self.send_response(400)  # Bad request
                except json.JSONDecodeError:
                    # If JSON parsing fails, return an error
                    response = {"error": "Invalid JSON in request."}
                    self.send_response(400)  # Bad request
            else:
                # Invalid or missing API Key
                logger.error("Invalid or missing API Key.")
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "Unauthorized. Invalid API Key."}')
                return
        else:
            # Return a 404 response for unknown paths
            self.send_response(404)
            response = {"error": "Path not found."}

        # Send the response
        self.send_header("Access-Control-Allow-Origin", "*")  # Add CORS header
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))


def create_handler(chat_manager, rag_params, lm_instr, context_instr, api_key):
    def handler(*args, **kwargs):
        ChatbotHTTPRequestHandler(
            *args,
            chat_manager=chat_manager,
            rag_params=rag_params,
            lm_instr=lm_instr,
            context_instr=context_instr,
            api_key=api_key,
            **kwargs,
        )

    return handler


def run_server(port, chat_manager, rag_params, lm_instr, context_instr, api_key):
    logger.info("run_server:server started on port %i", port)
    logger.info("run_server: rag_params")
    logger.info(rag_params)
    logger.info("run_server: api_key")
    logger.info(api_key)
    handler_with_params = create_handler(chat_manager, rag_params, lm_instr, context_instr, api_key)
    server_address = ("", port)
    httpd = HTTPServer(server_address, handler_with_params)
    httpd.serve_forever()


def gui_start():
    logger.info("GUI start: log for state")
    if "chat_manager" in st.session_state:
        logger.info(state.chat_manager)
    if "rag_params" in st.session_state:
        logger.info(state.rag_params)
    if "lm_instr" in st.session_state:
        logger.info(state.lm_instr)
    if "context_instr" in st.session_state:
        logger.info(state.context_instr)
    if "api_key" in st.session_state:
        logger.info(state.api_key)

    if "initialized" in st.session_state:
        if st.session_state.initialized:
            if "server_thread" not in st.session_state:
                st.session_state.server_thread = threading.Thread(
                    target=run_server,
                    args=(
                        st.session_state["port"],  # port
                        state.chat_manager,  # chat_manager
                        state.rag_params,  # rag_params
                        state.lm_instr,  # lm_instr
                        state.context_instr,  # context_instr
                        st.session_state["api_key"],  # api_key
                    ),
                    daemon=True,
                )
                st.session_state.server_thread.start()
                port = st.session_state["port"]
                st.success(f"Chatbot server started on port {port}.")
            else:
                st.warning("Server is already running.")
    else:
        st.warning("Chatbot not yet configured.")


def sidebar_start_server():
    st.session_state["port"] = st.sidebar.number_input(
        "Enter the port number for the chatbot server:", value=8000, min_value=1, max_value=65535
    )
    st.session_state["api_key"] = st.sidebar.text_input("API_KEY", type="password", value="abc")
    st.sidebar.button("Start server", type="primary", on_click=gui_start)
