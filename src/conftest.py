"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error, disable=wrong-import-position

import os
import time
import subprocess
from time import sleep
import docker


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
    time.sleep(15)
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
        at.session_state.user_settings = {"client": COMMON_VARS["api_client_id"]}
        return at

    return _app_test


@pytest.fixture(scope="session", autouse=True)
def start_fastapi_server():
    """Start the FastAPI server for Streamlit"""
    server_process = subprocess.Popen(["python", "oaim_server.py"])
    sleep(10)
    yield
    # Terminate the server after tests
    server_process.terminate()
    server_process.wait()


##### MAIN #####
API_CLIENT = TestClient(app)
HEADERS = {
    "Authorization": f"Bearer {os.getenv('API_SERVER_KEY')}",
    "Client": COMMON_VARS["api_client_id"],
}
