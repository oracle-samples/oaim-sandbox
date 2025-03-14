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
class TestNoAuthEndpoints:
    """Test endpoints without AuthN"""

    test_cases = [
        pytest.param(
            {"endpoint": "/v1/embed/vs", "method": "delete"},
            id="embed_drop_vs",
        ),
        pytest.param(
            {"endpoint": "/v1/embed/web/store", "method": "post"},
            id="store_web_file",
        ),
        pytest.param(
            {"endpoint": "/v1/embed/local/store", "method": "post"},
            id="store_local_file",
        ),
        pytest.param(
            {"endpoint": "/v1/embed", "method": "post"},
            id="split_embed",
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
# Test AuthN required and Valid
#############################################################################
class TestAuthEndpoints:
    """Test endpoints with AuthN"""