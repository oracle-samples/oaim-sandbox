"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient
from conftest import TEST_CONFIG, TEST_HEADERS, TEST_BAD_HEADERS


#############################################################################
# Test AuthN required and Valid
#############################################################################
class TestTestbedNoAuthEndpoints:
    """Test endpoints without Auth"""

    test_cases = [
        pytest.param(
            {"endpoint": "/v1/testbed/testsets", "method": "get"},
            id="testbed_testsets",
        ),
        pytest.param(
            {"endpoint": "/v1/testbed/evaluations", "method": "get"},
            id="testbed_evaluations",
        ),
        pytest.param(
            {"endpoint": "/v1/testbed/evaluation", "method": "get"},
            id="testbed_evaluation",
        ),
        pytest.param(
            {"endpoint": "/v1/testbed/testset_qa", "method": "get"},
            id="testbed_testset_qa",
        ),
        pytest.param(
            {"endpoint": "/v1/testbed/testset_delete/1234", "method": "delete"},
            id="testbed_delete_testset",
        ),
        pytest.param(
            {"endpoint": "/v1/testbed/testset_load", "method": "post"},
            id="testbed_upsert_testsets",
        ),
        pytest.param(
            {"endpoint": "/v1/testbed/testset_generate", "method": "post"},
            id="testbed_generate_qa",
        ),
        pytest.param(
            {"endpoint": "/v1/testbed/evaluate", "method": "post"},
            id="testbed_evaluate_qa",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases)
    def test_no_auth(self, client: TestClient, test_case: Dict[str, Any]) -> None:
        """Testing for required AuthN"""
        response = getattr(client, test_case["method"])(test_case["endpoint"])
        assert response.status_code == 403
        response = getattr(client, test_case["method"])(test_case["endpoint"], headers=TEST_BAD_HEADERS)
        assert response.status_code == 401


#############################################################################
# Test AuthN
#############################################################################
class TestTestbedAuthEndpoints:
    """Test endpoints with Auth"""

    def test_testbed_delete_testset(self, client: TestClient, db_container):
        """Delete Testset"""
        assert db_container is not None
        payload = {
            "user": TEST_CONFIG["db_username"],
            "password": TEST_CONFIG["db_password"],
            "dsn": TEST_CONFIG["db_dsn"],
        }
        response = client.patch("/v1/databases/DEFAULT", headers=TEST_HEADERS, json=payload)
        assert response.status_code == 200
        response = client.delete("/v1/testbed/testset_delete/1234", headers=TEST_HEADERS)
        print(response.json())
        assert response.status_code == 200
        assert response.json() == {"message": "TestSet: 1234 deleted."}
