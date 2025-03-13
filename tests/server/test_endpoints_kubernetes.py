"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

from fastapi.testclient import TestClient


class TestKubernetesEndpoints:
    """Test Kubernetes endpoints"""

    def test_liveness(self, client: TestClient) -> None:
        """Test liveness endpoint"""
        response = client.get("/v1/liveness")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    def test_readiness(self, client: TestClient) -> None:
        """Test readiness endpoint"""
        response = client.get("/v1/readiness")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
