"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# spell-checker:ignore streamlit, langchain

import os
import socket
import secrets
import json
import queue
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Utilities
import modules.chatbot as chatbot
import modules.logging_config as logging_config

logger = logging_config.logging.getLogger("modules.api_server")

# Create a queue to store the requests and responses
log_queue = queue.Queue()


def config():
    """Define API Server Config"""

    def find_available_port():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("0.0.0.0", 0))
        port = sock.getsockname()[1]
        sock.close()

        return port

    def generate_api_key(length=32):
        # Generates a URL-safe, base64-encoded random string with the given length
        return secrets.token_urlsafe(length)

    api_server_port = os.environ.get("API_SERVER_PORT")
    api_server_key = os.environ.get("API_SERVER_KEY")

    auto_start = bool(api_server_port and api_server_key)

    return {
        "port": int(api_server_port) if api_server_port else find_available_port(),
        "key": api_server_key if api_server_key else generate_api_key(),
        "auto_start": auto_start
    }

class ChatbotHTTPRequestHandler(BaseHTTPRequestHandler):
    """Handler for mini-chatbot"""

    def __init__(
        self,
        *args,
        chat_manager=None,
        rag_params=None,
        lm_instr=None,
        context_instr=None,
        api_key=None,
        chat_history=None,
        enable_history=False,
        **kwargs
    ):
        self.chat_manager = chat_manager
        self.rag_params = rag_params
        self.lm_instr = lm_instr
        self.context_instr = context_instr
        self.api_key = api_key
        self.chat_history = chat_history
        self.enable_history = enable_history
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
                try:
                    # Parse the POST data as JSON
                    post_json = json.loads(post_data)

                    # Extract the 'message' field from the JSON
                    message = post_json.get("message")
                    response = None
                    if message:
                        # Log the incoming message
                        logger.info("MSG to Chatbot API: %s", message)

                        # Call your function to get the chatbot response
                        response = chatbot.generate_response(
                            chat_mgr=self.chat_manager,
                            input=message,
                            chat_history=self.chat_history,
                            enable_history=self.enable_history,
                            rag_params=self.rag_params,
                            chat_instr=self.lm_instr,
                            context_instr=self.context_instr,
                            stream=False,
                        )
                        self.send_response(200)
                        # Process response to JSON
                    else:
                        self.send_response(400)  # Bad request

                    # Add request/response to the queue for output
                    log_queue.put(post_json)
                    log_queue.put(response)
                except json.JSONDecodeError:
                    self.send_response(400)  # Bad request
            else:
                # Invalid or missing API Key
                logger.error("Invalid or missing API Key.")
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                return
        else:
            # Return a 404 response for unknown paths
            self.send_response(404)

        # Send the response
        self.send_header("Access-Control-Allow-Origin", "*")  # Add CORS header
        self.send_header("Content-Type", "application/json")
        self.end_headers()


def run_server(port, chat_manager, rag_params, lm_instr, context_instr, api_key, chat_history, enable_history):
    # Define the request handler function
    def handler(*args, **kwargs):
        return ChatbotHTTPRequestHandler(
            *args,
            chat_manager=chat_manager,
            rag_params=rag_params,
            lm_instr=lm_instr,
            context_instr=context_instr,
            api_key=api_key,
            chat_history=chat_history,
            enable_history=enable_history,
            **kwargs,
        )

    server_address = ("", port)
    httpd = HTTPServer(server_address, handler)

    return httpd
