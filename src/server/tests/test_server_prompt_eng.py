"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import pytest
from conftest import HEADERS, API_CLIENT


# All endpoints require AuthN
def test_prompts_list_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.get("/v1/prompts")
    assert response.status_code == 403


def test_prompts_get_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.get("/v1/prompts/sys/Basic")
    assert response.status_code == 403


def test_prompts_update_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.patch("/v1/prompts/sys/Basic")
    assert response.status_code == 403


# Test AuthN
params = [
    ("Basic Example", "sys", 200),
    ("RAG Example", "sys", 200),
    ("Custom", "sys", 200),
    ("Custom Fail", "sys", 404),
    ("Basic Example", "ctx", 200),
    ("Custom", "ctx", 200),
    ("Custom Fail", "ctx", 404),
]


@pytest.mark.parametrize("name, category, status_code", params)
def test_prompts_list_before(name, category, status_code):
    """List boostrapped prompts"""
    response = API_CLIENT.get("/v1/prompts", headers=HEADERS)
    assert response.status_code == 200
    if status_code == 200:
        assert any(r["name"] == name and r["category"] == category for r in response.json())


@pytest.mark.parametrize("name, category, status_code", params)
def test_prompts_get_before(name, category, status_code):
    """Get individual prompts"""
    response = API_CLIENT.get(f"/v1/prompts/{category}/{name}", headers=HEADERS)
    assert response.status_code == status_code


@pytest.mark.parametrize("name, category, status_code", params)
def test_prompts_update(name, category, status_code):
    """Update Prompt"""
    payload = {"prompt": "New prompt instructions"}
    response = API_CLIENT.patch(f"/v1/prompts/{category}/{name}", headers=HEADERS, json=payload)
    assert response.status_code == status_code
    if status_code == 200:
        response_data = response.json()
        assert response_data["prompt"] == "New prompt instructions"
    else:
        assert response.json() == {"detail": f"Prompt: {name} ({category}) not found."}


def test_prompts_list_after():
    """List boostrapped prompts after update"""
    response = API_CLIENT.get("/v1/prompts", headers=HEADERS)
    assert response.status_code == 200
    response_data = response.json()
    assert all(item["prompt"] == "New prompt instructions" for item in response_data)


@pytest.mark.parametrize("name, category, status_code", params)
def test_prompts_get_after(name, category, status_code):
    """Get individual prompts"""
    response = API_CLIENT.get(f"/v1/prompts/{category}/{name}", headers=HEADERS)
    assert response.status_code == status_code
    if status_code == 200:
        response_data = response.json()
        assert response_data["prompt"] == "New prompt instructions"
