"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import pytest
from conftest import HEADERS, API_CLIENT, COMMON_VARS


# All endpoints require AuthN
def test_databases_list_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.get("/v1/databases")
    assert response.status_code == 403


def test_databases_get_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.get("/v1/databases/DEFAULT")
    assert response.status_code == 403


def test_databases_update_noauth():
    """Testing for required AuthN"""
    response = API_CLIENT.patch("/v1/databases/DEFAULT")
    assert response.status_code == 403


# Test AuthN
def test_databases_get_before(db_container):
    """Get DEFAULT database before update"""
    assert db_container is not None
    response = API_CLIENT.get("/v1/databases/DEFAULT", headers=HEADERS)
    assert response.status_code == 406
    assert response.json() == {"detail": "Database: DEFAULT - Not all connection details supplied."}


def test_databases_list_before(db_container):
    """List databases before update"""
    assert db_container is not None
    response = API_CLIENT.get("/v1/databases", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data[0]["connected"] is False
    assert data[0]["dsn"] is None
    assert data[0]["name"] == "DEFAULT"
    assert data[0]["password"] is None
    assert data[0]["tcp_connect_timeout"] == 5
    assert data[0]["user"] is None
    assert data[0]["vector_stores"] is None
    assert data[0]["wallet_location"] is None
    assert data[0]["wallet_password"] is None


params = [
    (
        COMMON_VARS["database_name"],
        404,
        {
            "user": COMMON_VARS["database_user"],
            "password": COMMON_VARS["database_password"],
            "dsn": COMMON_VARS["database_dsn"],
        },
        {"detail": f"Database: {COMMON_VARS['database_name']} not found."},
    ),
    (
        "DEFAULT",
        422,
        "",
        {
            "detail": [
                {
                    "type": "model_attributes_type",
                    "loc": ["body"],
                    "msg": "Input should be a valid dictionary or object to extract fields from",
                    "input": "",
                }
            ]
        },
    ),
    (
        "DEFAULT",
        400,
        {},
        {"detail": "Not all connection details supplied."},
    ),
    (
        "DEFAULT",
        503,
        {"user": "user", "password": "password", "dsn": "//localhost:1521/dsn"},
        {"detail": "Unable to connect to database."},
    ),
    (
        "DEFAULT",
        401,
        {
            "user": COMMON_VARS["database_user"],
            "password": "Wr0ng_P4sswOrd",
            "dsn": COMMON_VARS["database_dsn"],
        },
        {"detail": "Invalid database credentials."},
    ),
    (
        "DEFAULT",
        200,
        {
            "user": COMMON_VARS["database_user"],
            "password": COMMON_VARS["database_password"],
            "dsn": COMMON_VARS["database_dsn"],
        },
        {
            "user": COMMON_VARS["database_user"],
            "password": COMMON_VARS["database_password"],
            "dsn": COMMON_VARS["database_dsn"],
        },
    ),
]


@pytest.mark.parametrize("database, status_code, payload, details", params)
def test_databases_update(db_container, database, payload, status_code, details):
    """Update with Payload"""
    assert db_container is not None
    response = API_CLIENT.patch(f"/v1/databases/{database}", headers=HEADERS, json=payload)
    assert response.status_code == status_code
    if response.status_code != 200:
        assert response.json() == details
    else:
        data = response.json()  # Get the dictionary from response
        data.pop("config_dir", None)  # Remove "config_dir" if it exists
        assert data == {
            "connected": True,
            "dsn": COMMON_VARS["database_dsn"],
            "name": "DEFAULT",
            "password": COMMON_VARS["database_password"],
            "tcp_connect_timeout": 5,
            "user": COMMON_VARS["database_user"],
            "vector_stores": [],
            "wallet_location": None,
            "wallet_password": None,
        }


def test_databases_get_after(db_container):
    """Get DEFAULT database after update"""
    assert db_container is not None
    response = API_CLIENT.get("/v1/databases/DEFAULT", headers=HEADERS)
    assert response.status_code == 200
    assert response.json().get("config_dir")
    data = response.json()  # Get the dictionary from response
    data.pop("config_dir", None)  # Remove "config_dir" if it exists
    assert data == {
        "connected": True,
        "dsn": COMMON_VARS["database_dsn"],
        "name": "DEFAULT",
        "password": COMMON_VARS["database_password"],
        "tcp_connect_timeout": 5,
        "user": COMMON_VARS["database_user"],
        "vector_stores": [],
        "wallet_location": None,
        "wallet_password": None,
    }


def test_databases_list_after(db_container):
    """List databases after update"""
    assert db_container is not None
    response = API_CLIENT.get("/v1/databases", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data[0]["connected"] is True
    assert data[0]["dsn"] == COMMON_VARS["database_dsn"]
    assert data[0]["name"] == "DEFAULT"
    assert data[0]["password"] == COMMON_VARS["database_password"]
    assert data[0]["user"] == COMMON_VARS["database_user"]
    assert data[0]["vector_stores"] == []
