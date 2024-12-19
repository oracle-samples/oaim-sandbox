"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore fastapi, laddr, checkpointer, langgraph, oaim
# pylint: disable=redefined-outer-name

import os
import queue
import secrets
import socket
import subprocess
import threading
from typing import Annotated

import psutil

# from langgraph.store.memory import InMemoryStore
import common.logging_config as logging_config

# Endpoints
from server.endpoints import register_endpoints

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


logger = logging_config.logging.getLogger("oaim_server")


##########################################
# Process Control
##########################################
def start_server(port: int = 8000) -> int:
    """Start the uvicorn server for FastAPI"""
    logger.info("Starting Oracle AI Microservices Server")

    def find_available_port() -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("0.0.0.0", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    def get_pid_using_port(port: int) -> int:
        """Find the PID of the process using the specified port."""
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                for conn in proc.net_connections(kind="inet"):
                    if conn.status == "LISTEN" and conn.laddr.port == port:
                        return proc.info["pid"]
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        return None

    def start_subprocess(port: int) -> subprocess.Popen:
        """Start the uvicorn server as a subprocess."""
        logger.info("API server starting on port: %i", port)
        process = subprocess.Popen(
            [
                "uvicorn",
                "oaim_server:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info("API server started on Port: %i; PID: %i", port, process.pid)
        return process

    port = port or find_available_port()
    existing_pid = get_pid_using_port(port)
    if existing_pid:
        logger.info("API server already running on port: %i (PID: %i)", port, existing_pid)
        return existing_pid

    popen_queue = queue.Queue()
    thread = threading.Thread(
        target=lambda: popen_queue.put(start_subprocess(port)),
        daemon=True,
    )
    thread.start()

    return popen_queue.get().pid


def stop_server(pid: int) -> None:
    """Stop the uvicorn server for FastAPI."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait()
    except (psutil.NoSuchProcess, psutil.AccessDenied) as ex:
        logger.error("Failed to terminate process with PID: %i - %s", pid, ex)

    logger.info("API server stopped.")


##########################################
# Server App and API Key
##########################################
def generate_auth_key(length: int = 32) -> None:
    """Generates a URL-safe, base64-encoded random string with the given length"""
    os.environ["API_SERVER_KEY"] = secrets.token_urlsafe(length)


def verify_key(
    http_auth: Annotated[
        HTTPAuthorizationCredentials,
        Depends(HTTPBearer(description="Please provide API_SERVER_KEY.")),
    ],
) -> None:
    if http_auth.credentials != os.getenv("API_SERVER_KEY"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


#############################################################################
# MAIN
#############################################################################
_ = os.getenv("API_SERVER_KEY") or generate_auth_key()
logger.info("Auth Key: %s", os.getenv("API_SERVER_KEY"))

app = FastAPI(title="Oracle AI Microservices Server", dependencies=[Depends(verify_key)])

# Register Endpoints
register_endpoints(app)