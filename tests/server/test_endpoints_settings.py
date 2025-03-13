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
class TestSettingsNoAuthEndpoints:
    """Test endpoints without Auth"""

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
# Test AuthN
#############################################################################
# class TestSettingsAuthEndpoints:

#     def test_settings_get(self, client: TestClient) -> None:
#         """Get All"""
#         response = client.get("/v1/settings", headers=TEST_BAD_HEADERS)
#         assert response.status_code == 401
