## Copyright (c) 2024, 2025, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
# spell-checker:disable

from fastapi.testclient import TestClient
from src import oaim_server

client = TestClient(oaim_server)

def test_liveness():
    response = client.get("v1/liveness")
    assert response.status_code == 200


def test_readiness():
    response = client.post("v1/readiness")
    assert response.status_code == 200
