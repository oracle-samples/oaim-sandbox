"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# pylint: disable=unused-argument

from unittest.mock import patch, MagicMock, ANY
import pytest
from modules import oci_utils


###################################################
# db_utils.initialise
###################################################
@pytest.mark.parametrize(
    "tenancy, region, fingerprint, key_file, user, security_token_file, expected_result",
    [
        (
            None,
            None,
            None,
            None,
            None,
            None,
            {
                "tenancy": None,
                "region": None,
                "fingerprint": None,
                "key_file": None,
                "user": None,
                "security_token_file": None,
                "additional_user_agent": "",
                "log_requests": False,
                "pass_phrase": None,
            },
        ),
        (
            "TEST_TENANCY",
            "TEST_REGION",
            "TEST_FINGERPRINT",
            "TEST_KEY_FILE",
            "TEST_USER",
            None,
            {
                "tenancy": "TEST_TENANCY",
                "region": "TEST_REGION",
                "fingerprint": "TEST_FINGERPRINT",
                "key_file": "TEST_KEY_FILE",
                "user": "TEST_USER",
                "security_token_file": None,
                "additional_user_agent": "",
                "log_requests": False,
                "pass_phrase": None,
            },
        ),
        (
            "TEST_TENANCY",
            "TEST_REGION",
            "TEST_FINGERPRINT",
            "TEST_KEY_FILE",
            None,
            "TEST_SECURITY_TOKEN_FILE",
            {
                "tenancy": "TEST_TENANCY",
                "region": "TEST_REGION",
                "fingerprint": "TEST_FINGERPRINT",
                "key_file": "TEST_KEY_FILE",
                "user": None,
                "security_token_file": "TEST_SECURITY_TOKEN_FILE",
                "additional_user_agent": "",
                "log_requests": False,
                "pass_phrase": None,
            },
        ),
    ],
)
def test_initialise_manual(
    unset_oci_env,
    tenancy,
    region,
    fingerprint,
    key_file,
    user,
    security_token_file,
    expected_result,
):
    """Initialise with User Input"""
    assert (
        oci_utils.initialise(
            tenancy=tenancy,
            region=region,
            fingerprint=fingerprint,
            key_file=key_file,
            user=user,
            security_token_file=security_token_file,
        )
        == expected_result
    )


def test_initialise_env_user(set_oci_env_user):
    """Initialise with User Environment"""
    assert oci_utils.initialise() == (
        {
            "tenancy": "TEST_TENANCY",
            "region": "TEST_REGION",
            "fingerprint": "TEST_FINGERPRINT",
            "key_file": "TEST_KEY_FILE",
            "user": "TEST_USER",
            "security_token_file": ANY,
            "additional_user_agent": "",
            "log_requests": False,
            "pass_phrase": None,
        }
    )


def test_initialise_env_security_token(set_oci_env_token):
    """Initialise with Token Environment"""
    assert oci_utils.initialise() == (
        {
            "tenancy": "TEST_TENANCY",
            "region": "TEST_REGION",
            "fingerprint": "TEST_FINGERPRINT",
            "key_file": "TEST_KEY_FILE",
            "user": ANY,
            "security_token_file": "TEST_SECURITY_TOKEN_FILE",
            "additional_user_agent": "",
            "log_requests": False,
            "pass_phrase": None,
        }
    )


def test_init_client_no_env_user(unset_oci_env):
    """Initialise Client without User Environment"""
    mock_client_type = MagicMock()
    mock_config = oci_utils.initialise(
        "TEST_TENANCY", "TEST_REGION", "TEST_FINGERPRINT", "TEST_KEY_FILE", "TEST_USER", None
    )
    with patch("oci.retry.NoneRetryStrategy") as mocknoneretrystrategy:
        mock_none_retry_strategy_instance = mocknoneretrystrategy.return_value
        client = oci_utils.init_client(mock_client_type, mock_config, retries=False)

        mock_client_type.assert_called_once_with(mock_config, retry_strategy=mock_none_retry_strategy_instance)
        assert client == mock_client_type()

    assert mock_none_retry_strategy_instance == ANY


def test_init_client_env_user(set_oci_env_user, mock_oci):
    """Initialise Client with User Environment"""
    mock_client_type = MagicMock()
    mock_config = oci_utils.initialise()

    with patch("oci.retry.NoneRetryStrategy") as mocknoneretrystrategy:
        mock_none_retry_strategy_instance = mocknoneretrystrategy.return_value
        client = oci_utils.init_client(mock_client_type, mock_config, retries=False)

        mock_client_type.assert_called_once_with(mock_config, retry_strategy=mock_none_retry_strategy_instance)
        assert client == mock_client_type()

    assert mock_none_retry_strategy_instance == ANY


def test_get_namespace_env_user(set_oci_env_user, mock_oci_init_client, mock_oci_object_storage_client):
    """Test AuthN with User Environment"""
    config = oci_utils.initialise()
    mock_namespace = "test_namespace"

    mock_client = MagicMock()
    mock_client.get_namespace.return_value.data = mock_namespace
    mock_oci_init_client.return_value = mock_client

    namespace = oci_utils.get_namespace(config)

    mock_oci_init_client.assert_called_once_with(mock_oci_object_storage_client, config, True)
    mock_client.get_namespace.assert_called_once()
    assert namespace == mock_namespace