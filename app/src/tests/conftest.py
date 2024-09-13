"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# Setup Modules
import sys
import os
from unittest.mock import patch
import pytest

path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, path)

######################################
# Monkey Patches
######################################
@pytest.fixture
def unset_api_env(monkeypatch):
    """Clear API Environment"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PPLX_API_KEY", raising=False)


@pytest.fixture
def set_api_env(monkeypatch):
    """Mock API Environment"""
    monkeypatch.setenv("OPENAI_API_KEY", "TEST_API_KEY")
    monkeypatch.setenv("PPLX_API_KEY", "TEST_API_KEY")


@pytest.fixture
def unset_db_env(monkeypatch):
    """Clear DB Environment"""
    monkeypatch.delenv("DB_USERNAME", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.delenv("DB_DSN", raising=False)


@pytest.fixture
def set_db_env(monkeypatch):
    """Mock DB Environment"""
    monkeypatch.setenv("DB_USERNAME", "TEST_USER")
    monkeypatch.setenv("DB_PASSWORD", "TEST_PASS")
    monkeypatch.setenv("DB_DSN", "TEST_DSN")

@pytest.fixture
def set_db_env_wallet(monkeypatch):
    """Mock DB Environment"""
    monkeypatch.setenv("DB_USERNAME", "TEST_USER")
    monkeypatch.setenv("DB_PASSWORD", "TEST_PASS")
    monkeypatch.setenv("DB_DSN", "TEST_DSN")
    monkeypatch.setenv("DB_WALLET_PASSWORD", "TEST_WALLET")

@pytest.fixture
def set_oci_env_user(monkeypatch):
    """Mock OCI Environment for User AuthN"""
    monkeypatch.setenv("OCI_CLI_TENANCY", "TEST_TENANCY")
    monkeypatch.setenv("OCI_CLI_REGION", "TEST_REGION")
    monkeypatch.setenv("OCI_CLI_FINGERPRINT", "TEST_FINGERPRINT")
    monkeypatch.setenv("OCI_CLI_KEY_FILE", "TEST_KEY_FILE")
    monkeypatch.setenv("OCI_CLI_USER", "TEST_USER")
    monkeypatch.setenv("OCI_CLI_SECURITY_TOKEN_FILE", "")


@pytest.fixture
def set_oci_env_token(monkeypatch):
    """Mock OCI Environment for Token AuthN"""
    monkeypatch.setenv("OCI_CLI_TENANCY", "TEST_TENANCY")
    monkeypatch.setenv("OCI_CLI_REGION", "TEST_REGION")
    monkeypatch.setenv("OCI_CLI_FINGERPRINT", "TEST_FINGERPRINT")
    monkeypatch.setenv("OCI_CLI_KEY_FILE", "TEST_KEY_FILE")
    monkeypatch.setenv("OCI_CLI_USER", "")
    monkeypatch.setenv("OCI_CLI_SECURITY_TOKEN_FILE", "TEST_SECURITY_TOKEN_FILE")


@pytest.fixture
def unset_oci_env(monkeypatch):
    """Unset OCI Environment; prevent OCI Config file ingest"""
    monkeypatch.setenv("OCI_CLI_CONFIG_FILE", "/non/existent/path/config")
    monkeypatch.delenv("OCI_CLI_PROFILE", raising=False)
    monkeypatch.delenv("OCI_CLI_SECURITY_TOKEN_FILE", raising=False)
    monkeypatch.delenv("OCI_CLI_USER", raising=False)
    monkeypatch.delenv("OCI_CLI_FINGERPRINT", raising=False)
    monkeypatch.delenv("OCI_CLI_TENANCY", raising=False)
    monkeypatch.delenv("OCI_CLI_REGION", raising=False)
    monkeypatch.delenv("OCI_CLI_KEY_FILE", raising=False)


######################################
# Mocks
######################################
@pytest.fixture
def mock_is_url_accessible():
    """Mock API Accessible"""
    with patch("modules.st_common.is_url_accessible") as mock:
        mock.return_value = (True, None)
        yield mock


@pytest.fixture
def mock_oracledb():
    """Mock Oracle DB Connection"""
    with patch("modules.db_utils.oracledb") as mock_oracledb_patch:
        yield mock_oracledb_patch


@pytest.fixture
def mock_db_utils_connect():
    """Mock the connect method in db_utils"""
    with patch("modules.db_utils.connect") as mock_connect:
        yield mock_connect

@pytest.fixture
def mock_oci():
    """Mock OCI Connection"""
    with patch("modules.oci_utils") as mock_oci_patch:
        yield mock_oci_patch


@pytest.fixture
def mock_oci_init_client():
    """Mock OCI Client"""
    with patch("modules.oci_utils.init_client") as mock_oci_init_client_patch:
        yield mock_oci_init_client_patch


@pytest.fixture
def mock_oci_object_storage_client():
    """Mock OCI ObjectStore Client"""
    with patch(
        "modules.oci_utils.oci.object_storage.ObjectStorageClient"
    ) as mock_oci_object_storage_client_patch:
        yield mock_oci_object_storage_client_patch


@pytest.fixture
def mock_oci_get_namespace():
    """Mock OCI Get Namespace"""
    with patch("modules.oci_utils.get_namespace") as mock_oci_get_namespace_patch:
        yield mock_oci_get_namespace_patch
