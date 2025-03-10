"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import os
from conftest import HEADERS, API_CLIENT


# All endpoints require AuthN
def test_models_list_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.get("/v1/models")
    assert response.status_code == 403


def test_models_get_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.get("/v1/models/model_name")
    assert response.status_code == 403


def test_models_update_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.patch("/v1/models/model_name")
    assert response.status_code == 403


def test_models_delete_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.delete("/v1/models/model_name")
    assert response.status_code == 403


def test_model_create_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.post("/v1/models")
    assert response.status_code == 403


# Test AuthN
allowed_keys = [
    "max_chunk_size",
    "context_length",
    "frequency_penalty",
    "max_completion_tokens",
    "presence_penalty",
    "temperature",
    "top_p",
    "streaming",
    "enabled",
    "url",
    "api_key",
    "name",
    "type",
    "api",
    "openai_compat",
    "status",
]

new_ll_model = {
    "name": "test_ll_model",
    "enabled": os.getenv("OPENAI_API_KEY") is not None,
    "type": "ll",
    "api": "OpenAI",
    "api_key": os.environ.get("OPENAI_API_KEY", default=""),
    "openai_compat": True,
    "url": "https://api.openai.com",
    "context_length": 127072,
    "temperature": 1.0,
    "max_completion_tokens": 4096,
    "frequency_penalty": 0.0,
}
ll_model_defaults = {
    "max_chunk_size": None,
    "presence_penalty": 0.0,
    "status": "UNVERIFIED",
    "streaming": False,
    "top_p": 1.0,
}
new_embed_model = {
    "name": "test_embed_model",
    "enabled": os.getenv("ON_PREM_HF_URL") is not None,
    "type": "embed",
    "api": "HuggingFaceEndpointEmbeddings",
    "url": os.environ.get("ON_PREM_HF_URL", default="http://127.0.0.1:8080"),
    "api_key": "",
    "openai_compat": True,
    "max_chunk_size": 512,
}
embed_model_defaults = {
    "context_length": None,
    "frequency_penalty": 0.0,
    "max_completion_tokens": 256,
    "presence_penalty": 0.0,
    "status": "UNVERIFIED",
    "streaming": False,
    "temperature": 1.0,
    "top_p": 1.0,
}


def models_list():
    """Get a list of bootstrapped models to use with tests"""
    response = API_CLIENT.get("/v1/models", headers=HEADERS)
    return response.json()


def test_models_get_before():
    """Retreive each individual model"""
    all_models = models_list()
    assert len(all_models) > 0
    for model in all_models:
        response = API_CLIENT.get(f"/v1/models/{model['name']}", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        for key in allowed_keys:
            assert data[key] == model[key]
        assert set(data.keys()) == set(allowed_keys), f"Unexpected keys: {set(data.keys()) - set(allowed_keys)}"


def test_model_create():
    """Create Models"""
    all_models = models_list()
    assert len(all_models) > 0
    # Create existing models
    for model in all_models:
        payload = model
        response = API_CLIENT.post("/v1/models", json=payload, headers=HEADERS)
        assert response.status_code == 409
        assert response.json() == {"detail": f"Model: {payload['name']} already exists."}

    # Create new LL model
    response = API_CLIENT.post("/v1/models", json=new_ll_model, headers=HEADERS)
    assert response.status_code == 200
    expected_model = new_ll_model | ll_model_defaults
    assert response.json() == expected_model
    print(f"New Model: {response.json()}")

    # Create new embed model
    response = API_CLIENT.post("/v1/models", json=new_embed_model, headers=HEADERS)
    assert response.status_code == 200
    expected_model = new_embed_model | embed_model_defaults
    assert response.json() == expected_model

    # Create model with missing params
    bad_embed_model = new_embed_model.copy()
    bad_embed_model.pop("name", None)
    response = API_CLIENT.post("/v1/models", json=bad_embed_model, headers=HEADERS)
    assert response.status_code == 422

    # Create model with missing params
    bad_ll_model = new_ll_model.copy()
    bad_ll_model.pop("api", None)
    response = API_CLIENT.post("/v1/models", json=bad_ll_model, headers=HEADERS)
    assert response.status_code == 422


def test_models_update():
    """Update Model"""
    response = API_CLIENT.patch("/v1/models/test_model", json=new_embed_model, headers=HEADERS)
    assert response.status_code == 404
    assert response.json() == {"detail": "Model: test_model not found."}

    # Update Parameter
    new_ll_model["enabled"] = True
    response = API_CLIENT.patch(f"/v1/models/{new_ll_model['name']}", json=new_ll_model, headers=HEADERS)
    assert response.status_code == 200
    expected_model = new_ll_model | ll_model_defaults
    assert response.json() == expected_model


def test_models_delete():
    """Delete and Re-Add Models"""
    all_models = models_list()
    assert len(all_models) > 0
    print(f"All models: {all_models}")

    # Delete a all models
    for model in all_models:
        response = API_CLIENT.delete(f"/v1/models/{model['name']}", headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == {"message": f"Model: {model['name']} deleted."}
    # Check that no models exists
    deleted_models = models_list()
    assert len(deleted_models) == 0

    # Delete a non-existent model
    response = API_CLIENT.delete("/v1/models/test_model", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"message": "Model: test_model deleted."}

    # Add all models back
    print(f"All models: {all_models}")
    for model in all_models:
        payload = model
        response = API_CLIENT.post("/v1/models", json=payload, headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == payload
