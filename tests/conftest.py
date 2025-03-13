"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import os
import time
import subprocess
import socket
from typing import Generator
from unittest.mock import patch, MagicMock
from pathlib import Path
from streamlit.testing.v1 import AppTest
import docker
from docker.errors import DockerException
from docker.models.containers import Container
import requests
import pytest
from fastapi.testclient import TestClient


# This contains all the environment variables we consume on startup (add as required)
# Used to clear testing environment
API_VARS = [
    "API_SERVER_KEY",
    "API_SERVER_URL",
    "API_SERVER_PORT",
]
DB_VARS = [
    "DB_USERNAME",
    "DB_PASSWORD",
    "DB_DSN",
    "DB_WALLET_PASSWORD",
    "TNS_ADMIN",
]
MODEL_VARS = [
    "ON_PREM_OLLAMA_URL",
    "ON_PREM_HF_URL",
    "OPENAI_API_KEY",
    "PPLX_API_KEY",
    "COHERE_API_KEY",
]
OCI_VARS = [
    "OCI_CLI_CONFIG_FILE",
    "OCI_CLI_TENANCY",
    "OCI_CLI_REGION",
    "OCI_CLI_USER",
    "OCI_CLI_FINGERPRINT",
    "OCI_CLI_KEY_FILE",
    "OCI_CLI_SECURITY_TOKEN_FILE",
    "OCI_GENAI_SERVICE_ENDPOINT",
    "OCI_GENAI_COMPARTMENT_ID",
]
for env_var in [*DB_VARS, *MODEL_VARS, *OCI_VARS]:
    os.environ.pop(env_var, None)

# Setup API Server Defaults
os.environ["API_SERVER_KEY"] = "testing-token"
os.environ["API_SERVER_URL"] = "http://localhost"
os.environ["API_SERVER_PORT"] = "8012"

# Test constants
TEST_CONFIG = {
    # Database configuration
    "db_username": "PDBADMIN",
    "db_password": "Welcome12345#",
    "db_name": "FREEPDB1",
    "db_port": "1525",
    "db_dsn": "//localhost:1525/FREEPDB1",
    # Test client configuration
    "test_client": "test_client",
}
TEST_HEADERS = {"Authorization": f"Bearer {os.getenv('API_SERVER_KEY')}", "client": TEST_CONFIG["test_client"]}
TEST_BAD_HEADERS = {"Authorization": "Bearer bad-testing-token", "client": TEST_CONFIG["test_client"]}

# Constants for helper processes/container
TIMEOUT = 300  # 5 minutes timeout
CHECK_DELAY = 10  # 10 seconds between checks


#####################################################
# Mocks
#####################################################
@pytest.fixture(name="mock_get_temp_directory")
def _mock_get_temp_directory():
    """Mock get_temp_directory to return a fake path"""
    fake_path = Path("/mock/tmp/client/function")

    with patch("server.endpoints.get_temp_directory", return_value=fake_path) as mock:
        yield mock

#####################################################
# Fixtures
#####################################################
@pytest.fixture(scope="session", name="client")
def _client() -> Generator[TestClient, None, None]:
    """Create test client with auth"""
    # Prevent picking up default OCI config file
    os.environ["OCI_CLI_CONFIG_FILE"] = "/non/existant/path"

    # Lazy import to for OS env
    import oaim_server  # pylint: disable=import-outside-toplevel

    app = oaim_server.create_app()
    with TestClient(app) as client:
        # Bootstrap Settings
        client.post("/v1/settings", headers=TEST_HEADERS, params={"client": TEST_CONFIG["test_client"]})
        yield client


@pytest.fixture(scope="session")
def db_container() -> Generator[Container, None, None]:
    """
    This fixture creates and manages an Oracle database container for testing.
    The container is created at the start of the test session and removed after all tests complete.
    """
    db_client = docker.from_env()
    container = None

    try:
        # Start the container
        container = db_client.containers.run(
            "container-registry.oracle.com/database/free:latest-lite",
            environment={
                "ORACLE_PWD": TEST_CONFIG["db_password"],
                "ORACLE_PDB": TEST_CONFIG["db_name"],
            },
            ports={"1521/tcp": int(TEST_CONFIG["db_port"])},
            detach=True,
        )

        # Wait for database to be ready
        start_time = time.time()
        while time.time() - start_time < TIMEOUT:
            try:
                logs = container.logs(tail=100).decode("utf-8")
                if "DATABASE IS READY TO USE!" in logs:
                    break
            except DockerException as e:
                container.remove(force=True)
                raise DockerException(f"Failed to get container logs: {str(e)}") from e
            time.sleep(CHECK_DELAY)
        else:
            if container:
                container.remove(force=True)
            raise TimeoutError(f"Database did not become ready within {TIMEOUT} seconds")

        yield container

    except DockerException as e:
        if container:
            container.remove(force=True)
        raise DockerException(f"Docker operation failed: {str(e)}") from e

    finally:
        # Cleanup: After session
        if container:
            try:
                container.stop(timeout=30)  # Give 30 seconds for graceful shutdown
                container.remove()
            except DockerException as e:
                # Log error but don't fail tests if cleanup has issues
                print(f"Warning: Failed to cleanup database container: {str(e)}")


def wait_for_server():
    """Wait until the server to be accessible"""
    start_time = time.time()
    while time.time() - start_time < TIMEOUT:
        try:
            # Try to establish a socket connection to the host and port
            with socket.create_connection(("127.0.0.1", os.environ.get("API_SERVER_PORT")), timeout=CHECK_DELAY):
                return True  # Port is accessible
        except (socket.timeout, socket.error):
            print("Server not accessible. Retrying...")
            time.sleep(CHECK_DELAY)  # Wait before retrying

    raise TimeoutError("Server is not accessible within the timeout period.")


@pytest.fixture
def app_test():
    """Establish Streamlit State for Client to Operate"""

    def _app_test(page):
        at = AppTest.from_file(page)
        at.session_state.server = {
            "key": os.environ.get("API_SERVER_KEY"),
            "url": os.environ.get("API_SERVER_URL"),
            "port": os.environ.get("API_SERVER_PORT"),
        }
        wait_for_server()
        response = requests.get(
            url=f"{at.session_state.server['url']}:{at.session_state.server['port']}/v1/settings",
            headers=TEST_HEADERS,
            params={"client": TEST_CONFIG["test_client"]},
            timeout=120,
        )
        if response.status_code == 404:
            response = requests.post(
                url=f"{at.session_state.server['url']}:{at.session_state.server['port']}/v1/settings",
                headers=TEST_HEADERS,
                params={"client": TEST_CONFIG["test_client"]},
                timeout=120,
            )
        at.session_state.user_settings = response.json()

        return at

    return _app_test


@pytest.fixture(scope="session", autouse=True)
def start_fastapi_server():
    """Start the FastAPI server for Streamlit"""

    # Prevent picking up default OCI config file
    os.environ["OCI_CLI_CONFIG_FILE"] = "/non/existant/path"

    server_process = subprocess.Popen(["python", "oaim_server.py"], cwd="src")
    wait_for_server()
    yield
    # Terminate the server after tests
    server_process.terminate()
    server_process.wait()
