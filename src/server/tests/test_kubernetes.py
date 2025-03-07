"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

from conftest import API_CLIENT

def test_liveness():
    """Test K8s Liveness Probe - No AuthN"""
    response = API_CLIENT.get("v1/liveness")
    assert response.status_code == 200


def test_readiness():
    """Test K8s Readiness Probe - No AuthN"""
    response = API_CLIENT.get("v1/readiness")
    assert response.status_code == 200
