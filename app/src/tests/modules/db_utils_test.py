"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:disable
# pylint: disable=unused-argument

from unittest.mock import MagicMock
import pytest
import modules.utilities as utilities


###################################################
# utilities.db_initialize
###################################################
@pytest.mark.parametrize(
    "user, password, dsn, wallet_password, expected_result",
    [
        (
            None,
            None,
            None,
            None,
            {
                "user": None,
                "password": None,
                "dsn": None,
                "wallet_password": None,
                "config_dir": "tns_admin",
                "tcp_connect_timeout": 5,
            },
        ),
        (
            "TEST_USER",
            None,
            None,
            None,
            {
                "user": "TEST_USER",
                "password": None,
                "dsn": None,
                "wallet_password": None,
                "config_dir": "tns_admin",
                "tcp_connect_timeout": 5,
            },
        ),
        (
            "TEST_USER",
            "TEST_PASS",
            None,
            None,
            {
                "user": "TEST_USER",
                "password": "TEST_PASS",
                "dsn": None,
                "wallet_password": None,
                "config_dir": "tns_admin",
                "tcp_connect_timeout": 5,
            },
        ),
        (
            "TEST_USER",
            "TEST_PASS",
            "TEST_DSN",
            None,
            {
                "user": "TEST_USER",
                "password": "TEST_PASS",
                "dsn": "TEST_DSN",
                "wallet_password": None,
                "config_dir": "tns_admin",
                "tcp_connect_timeout": 5,
            },
        ),
        (
            "TEST_USER",
            "TEST_PASS",
            "TEST_DSN",
            "TEST_WALLET",
            {
                "user": "TEST_USER",
                "password": "TEST_PASS",
                "dsn": "TEST_DSN",
                "wallet_password": "TEST_WALLET",
                "config_dir": "tns_admin",
                "wallet_location": "tns_admin",
                "tcp_connect_timeout": 5,
            },
        ),
    ],
)
def test_initialize_manual(unset_db_env, user, password, dsn, wallet_password, expected_result):
    """Test initialize DB Config without Environment"""
    assert (
        utilities.db_initialize(user=user, password=password, dsn=dsn, wallet_password=wallet_password)
        == expected_result
    )


def test_initialize_env(set_db_env):
    """Test initialize DB Config with Environment"""
    assert utilities.db_initialize() == (
        {
            "user": "TEST_USER",
            "password": "TEST_PASS",
            "dsn": "TEST_DSN",
            "wallet_password": None,
            "config_dir": "tns_admin",
            "tcp_connect_timeout": 5,
        }
    )


def test_initialize_env_wallet(set_db_env_wallet):
    """Test initialize DB Config with Environment"""
    assert utilities.db_initialize() == (
        {
            "user": "TEST_USER",
            "password": "TEST_PASS",
            "dsn": "TEST_DSN",
            "wallet_password": "TEST_WALLET",
            "config_dir": "tns_admin",
            "wallet_location": "tns_admin",
            "tcp_connect_timeout": 5,
        }
    )


###################################################
# utilities.db_connect
###################################################
@pytest.mark.parametrize(
    "user, password, dsn, expected_result",
    [
        # Expected (result, success)
        (None, None, None, (False, False)),
        ("TEST_USER", None, None, (False, False)),
        ("TEST_USER", "TEST_PASS", None, (False, False)),
        ("TEST_USER", "TEST_PASS", "TEST_DSN", (True, True)),
    ],
)
def test_connect(mock_oracledb, user, password, dsn, expected_result):
    """Test DB Connection - Success"""
    # Mock configuration
    config = {
        "user": user,
        "password": password,
        "dsn": dsn,
    }

    # Mock the connection object
    mock_connection = MagicMock()
    mock_oracledb.connect.return_value = mock_connection if expected_result[1] else None

    # Call the connect function
    conn = utilities.db_connect(config)

    # Assertions
    mock_oracledb.connect.assert_called_once_with(
        user=config["user"],
        password=config["password"],
        dsn=config["dsn"],
    )
    assert (conn is not None, isinstance(conn, MagicMock)) == expected_result


###################################################
# utilities.get_vs_tables
###################################################
def test_get_vs_tables(mock_oracledb):
    """Get Vector Store Tables Test"""
    assert utilities.get_vs_tables(mock_oracledb, enabled_embed=list()) == ("{}")


###################################################
# utilities.execute_sql
###################################################
def test_execute_sql():
    """Test Execute SQL - Success"""
    # Arrange
    mock_connection = MagicMock()
    mock_cursor = mock_connection.cursor.return_value
    run_sql = "SELECT * FROM dual"

    # Act
    utilities.execute_sql(mock_connection, run_sql)

    # Assert
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once_with(run_sql)
    mock_cursor.close.assert_called_once()
