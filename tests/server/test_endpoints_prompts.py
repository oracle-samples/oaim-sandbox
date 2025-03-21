"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient
from conftest import TEST_HEADERS, TEST_BAD_HEADERS


#############################################################################
# Test AuthN required and Valid
#############################################################################
class TestNoAuthEndpoints:
    """Test endpoints without AuthN"""

    test_cases = [
        pytest.param(
            {"endpoint": "/v1/prompts", "method": "get"},
            id="prompts_list",
        ),
        pytest.param(
            {"endpoint": "/v1/prompts/sys/Basic", "method": "get"},
            id="prompts_get",
        ),
        pytest.param(
            {"endpoint": "/v1/prompts/sys/Basic", "method": "patch"},
            id="prompts_update",
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
class TestEndpoints:
    """Test endpoints with AuthN"""

    test_cases = [
        pytest.param(
            {"name": "Basic Example", "category": "sys", "status_code": 200},
            id="basic_example_sys_prompt",
        ),
        pytest.param(
            {"name": "RAG Example", "category": "sys", "status_code": 200},
            id="rag_example_sys_prompt",
        ),
        pytest.param(
            {"name": "Custom", "category": "sys", "status_code": 200},
            id="basic_sys_prompt",
        ),
        pytest.param(
            {"name": "NONEXISTANT", "category": "sys", "status_code": 404},
            id="nonexistant_sys_prompt",
        ),
        pytest.param(
            {"name": "Basic Example", "category": "ctx", "status_code": 200},
            id="basic_example_ctx_prompt",
        ),
        pytest.param(
            {"name": "Custom", "category": "ctx", "status_code": 200},
            id="custom_ctx_prompt",
        ),
        pytest.param(
            {"name": "NONEXISTANT", "category": "ctx", "status_code": 404},
            id="nonexistant_ctx_prompt",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases)
    def test_prompts_list_before(self, client: TestClient, test_case: Dict[str, Any]):
        """List boostrapped prompts"""
        response = client.get("/v1/prompts", headers=TEST_HEADERS)
        assert response.status_code == 200
        if test_case["status_code"] == 200:
            assert any(
                r["name"] == test_case["name"] and r["category"] == test_case["category"] for r in response.json()
            )

    @pytest.mark.parametrize("test_case", test_cases)
    def test_prompts_get_before(self, client: TestClient, test_case: Dict[str, Any]):
        """Get individual prompts"""
        response = client.get(f"/v1/prompts/{test_case['category']}/{test_case['name']}", headers=TEST_HEADERS)
        assert response.status_code == test_case["status_code"]
        if test_case["status_code"] == 200:
            data = response.json()
            assert data["name"] == test_case["name"]
            assert data["category"] == test_case["category"]
            assert data["prompt"] is not None
        else:
            assert response.json() == {"detail": f"Prompt: {test_case['name']} ({test_case['category']}) not found."}

    @pytest.mark.parametrize("test_case", test_cases)
    def test_prompts_update(self, client: TestClient, test_case: Dict[str, Any]):
        """Update Prompt"""
        payload = {"prompt": "New prompt instructions"}
        response = client.patch(
            f"/v1/prompts/{test_case['category']}/{test_case['name']}", headers=TEST_HEADERS, json=payload
        )
        assert response.status_code == test_case["status_code"]
        if test_case["status_code"] == 200:
            data = response.json()
            assert data["name"] == test_case["name"]
            assert data["category"] == test_case["category"]
            assert data["prompt"] == "New prompt instructions"
        else:
            assert response.json() == {"detail": f"Prompt: {test_case['name']} ({test_case['category']}) not found."}

    @pytest.mark.parametrize("test_case", test_cases)
    def test_prompts_get_after(self, client: TestClient, test_case: Dict[str, Any]):
        """Get individual prompts"""
        response = client.get(f"/v1/prompts/{test_case['category']}/{test_case['name']}", headers=TEST_HEADERS)
        assert response.status_code == test_case["status_code"]
        if test_case["status_code"] == 200:
            response_data = response.json()
            assert response_data["prompt"] == "New prompt instructions"

    def test_prompts_list_after(self, client: TestClient):
        """List boostrapped prompts"""
        response = client.get("/v1/prompts", headers=TEST_HEADERS)
        assert response.status_code == 200
        response_data = response.json()
        assert all(item["prompt"] == "New prompt instructions" for item in response_data)
