"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error, disable=wrong-import-position

import os
import time
import subprocess
import docker
import requests


COMMON_VARS = {
    "api_server_key": "testing-token",
    "api_server_url": "http://localhost",
    "aoi_server_port": "8012",
    "api_client_id": "test-user",
    "database_user": "PDBADMIN",
    "database_password": "T35t_D4t4-B4s3",
    "database_dsn": "//localhost:1521/FREEPDB1",
    "database_name": "FREEPDB1",
}

os.environ["API_SERVER_KEY"] = COMMON_VARS["api_server_key"]
os.environ["API_SERVER_URL"] = COMMON_VARS["api_server_url"]
os.environ["API_SERVER_PORT"] = COMMON_VARS["aoi_server_port"]

# Imported after setting environment
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from oaim_server import app

API_CLIENT = TestClient(app)
HEADERS = {
    "Authorization": f"Bearer {os.getenv('API_SERVER_KEY')}",
    "Client": COMMON_VARS["api_client_id"],
}

def wait_for_container(container, timeout=60):
    """Wait for the container to be in the 'running' state"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        container.reload()
        if container.status == 'running':
            return
        time.sleep(5)
    raise TimeoutError("Timed out waiting for container to be 'running'.")

def wait_for_db(container, timeout=60):
    """Wait for the Oracle DB container to be ready to accept connections"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        logs = container.logs(tail=100).decode('utf-8')
        if "DATABASE IS READY TO USE!" in logs:
            return
        time.sleep(5)
    raise TimeoutError("Timed out waiting for database to be ready.")

############ Fixtures ############
@pytest.fixture(scope="session")
def db_container():
    """Establish an Oracle DB Test Container"""
    db_client = docker.from_env()
    container = db_client.containers.run(
        "container-registry.oracle.com/database/free:latest-lite",
        environment={
            "ORACLE_PWD": COMMON_VARS["database_password"],
            "ORACLE_PDB": COMMON_VARS["database_name"],
        },
        ports={"1521/tcp": 1521},
        detach=True,
    )
    wait_for_container(container)
    wait_for_db(container)
    yield container

    # Cleanup: After session
    container.stop()
    container.remove()


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
        response = requests.get(
            url=f"{at.session_state.server['url']}:{at.session_state.server['port']}/v1/settings",
            headers=HEADERS,
            params={"client": COMMON_VARS["api_client_id"]},
            timeout=10,
        )
        if response.status_code == 404:
            response = requests.post(
                url=f"{at.session_state.server['url']}:{at.session_state.server['port']}/v1/settings",
                headers=HEADERS,
                params={"client": COMMON_VARS["api_client_id"]},
                timeout=10,
            )
        at.session_state.user_settings = response.json()

        return at

    return _app_test


@pytest.fixture(scope="session", autouse=True)
def start_fastapi_server():
    """Start the FastAPI server for Streamlit"""
    server_process = subprocess.Popen(["python", "oaim_server.py"])
    time.sleep(10)
    yield
    # Terminate the server after tests
    server_process.terminate()
    server_process.wait()
