"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, langchain

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from langchain_community.chat_message_histories import StreamlitChatMessageHistory

# Utilities
import modules.chatbot as chatbot
import modules.logging_config as logging_config

logger = logging_config.logging.getLogger("modules.api_server")


def get_answer_fn(
    question: str,
    history=None,
    chat_manager=None,
    rag_params=None,
    lm_instr=None,
    context_instr=None,
) -> str:
    """Send for completion"""
    # Format appropriately the history for your RAG agent
    chat_history_api = StreamlitChatMessageHistory(key="empty")
    chat_history_api.clear()
    if history:
        for h in history:
            if h["role"] == "assistant":
                chat_history_api.add_ai_message(h["content"])
            else:
                chat_history_api.add_user_message(h["content"])

    try:
        response = chatbot.generate_response(
            chat_mgr=chat_manager,
            input=question,
            chat_history=chat_history_api,
            enable_history=True,
            rag_params=rag_params,
            chat_instr=lm_instr,
            context_instr=context_instr,
            stream=False,
        )
        logger.info("MSG from Chatbot API: %s", response)
        if rag_params["enable"]:
            return response["answer"]
        else:
            return response.content
    except Exception as ex:
        return f"I'm sorry, something's gone wrong: {ex}"


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


def run_server(port, chat_manager, rag_params, lm_instr, context_instr, api_key):
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

    handler_with_params = create_handler(chat_manager, rag_params, lm_instr, context_instr, api_key)
    server_address = ("", port)
    httpd = HTTPServer(server_address, handler_with_params)

    return httpd
