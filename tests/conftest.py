"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import os
import time
import docker
import pytest
from fastapi.testclient import TestClient

os.environ["API_SERVER_KEY"] = "testing-token"
os.environ["API_SERVER_URL"] = "http://localhost"
os.environ["API_SERVER_PORT"] = "8001"

# Import the API Server
from oaim_server import app

@pytest.fixture(scope="session")
def db_container():
    """Establish an Oracle DB Test Container"""
    db_client = docker.from_env()
    container = db_client.containers.run(
        "container-registry.oracle.com/database/free:latest-lite",
        environment={"ORACLE_PWD": "T35t_D4t4-B4s3", "ORACLE_PDB": "FREEPDB1"},
        ports={"1521/tcp": 1521},
        detach=True,
    )
    time.sleep(15)
    yield container

    # Cleanup: After session
    container.stop()
    container.remove()

API_CLIENT = TestClient(app)
HEADERS = {
    "Authorization": f"Bearer {os.getenv('API_SERVER_KEY')}",
    "Client": "test-client",
}
