"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient
from conftest import TEST_HEADERS, TEST_BAD_HEADERS, TEST_CONFIG
from common.schema import Settings, LargeLanguageSettings, PromptSettings, RagSettings, OciSettings


#############################################################################
# Test AuthN required and Valid
#############################################################################
class TestNoAuthEndpoints:
    """Test endpoints without AuthN"""

    test_cases = [
        pytest.param(
            {"endpoint": "/v1/settings", "method": "get"},
            id="settings_get",
        ),
        pytest.param(
            {"endpoint": "/v1/settings", "method": "patch"},
            id="settings_update",
        ),
        pytest.param(
            {"endpoint": "/v1/settings", "method": "post"},
            id="settings_create",
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
# Test Settings Endpoints
#############################################################################
class TestEndpoints:
    """Test endpoints with AuthN"""

    def test_settings_get(self, client: TestClient) -> None:
        """Test getting settings for a client"""
        # Test getting settings for the test client
        response = client.get("/v1/settings", headers=TEST_HEADERS)
        assert response.status_code == 200
        settings = response.json()

        # Verify the response contains the expected structure
        assert settings["client"] == TEST_CONFIG["test_client"]
        assert "ll_model" in settings
        assert "prompts" in settings
        assert "rag" in settings
        assert "oci" in settings

    def test_settings_get_nonexistent_client(self, client: TestClient) -> None:
        """Test getting settings for a non-existent client"""
        headers = TEST_HEADERS.copy()
        headers["client"] = "nonexistent_client"
        response = client.get("/v1/settings", headers=headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_settings_create(self, client: TestClient) -> None:
        """Test creating settings for a new client"""
        new_client = "new_test_client"

        # Create new client settings
        response = client.post("/v1/settings", params={"client": new_client}, headers=TEST_HEADERS)
        assert response.status_code == 200
        settings = response.json()

        # Verify the new settings
        assert settings["client"] == new_client
        assert "ll_model" in settings
        assert "prompts" in settings
        assert "rag" in settings
        assert "oci" in settings

        # Verify we can retrieve the settings
        headers = TEST_HEADERS.copy()
        headers["client"] = new_client
        response = client.get("/v1/settings", headers=headers)
        assert response.status_code == 200
        assert response.json()["client"] == new_client

    def test_settings_create_existing_client(self, client: TestClient) -> None:
        """Test creating settings for an existing client"""
        # Try to create settings for the test client that already exists
        response = client.post(
            "/v1/settings",
            params={"client": TEST_CONFIG["test_client"]},
            headers=TEST_HEADERS,
        )
        assert response.status_code == 409
        assert response.json() == {"detail": f"Client: {TEST_CONFIG['test_client']} already exists."}

    def test_settings_update(self, client: TestClient) -> None:
        """Test updating settings for a client"""
        # First get the current settings
        response = client.get("/v1/settings", headers=TEST_HEADERS)
        assert response.status_code == 200
        _ = response.json()

        # Modify some settings
        updated_settings = Settings(
            client=TEST_CONFIG["test_client"],
            ll_model=LargeLanguageSettings(model="updated-model", chat_history=False),
            prompts=PromptSettings(ctx="Updated Context", sys="Updated System"),
            rag=RagSettings(rag_enabled=True, grading=False, search_type="Similarity", top_k=5),
            oci=OciSettings(auth_profile="UPDATED"),
        )

        # Update the settings
        response = client.patch("/v1/settings", headers=TEST_HEADERS, json=updated_settings.model_dump())
        assert response.status_code == 200
        updated = response.json()

        # Check that the values were updated
        assert updated["ll_model"]["model"] == "updated-model"
        assert updated["ll_model"]["chat_history"] is False
        assert updated["prompts"]["ctx"] == "Updated Context"
        assert updated["prompts"]["sys"] == "Updated System"
        assert updated["rag"]["rag_enabled"] is True
        assert updated["rag"]["grading"] is False
        assert updated["rag"]["top_k"] == 5
        assert updated["oci"]["auth_profile"] == "UPDATED"

    def test_settings_update_nonexistent_client(self, client: TestClient) -> None:
        """Test updating settings for a non-existent client"""
        headers = TEST_HEADERS.copy()
        headers["client"] = "nonexistent_client"

        updated_settings = Settings(client="nonexistent_client", ll_model=LargeLanguageSettings(model="test-model"))

        response = client.patch("/v1/settings", headers=headers, json=updated_settings.model_dump())
        assert response.status_code == 404
        assert response.json() == {"detail": "Client: nonexistent_client not found."}
