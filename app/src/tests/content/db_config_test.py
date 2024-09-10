"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# pylint: disable=unused-argument

from unittest.mock import MagicMock
from streamlit.testing.v1 import AppTest
import modules.db_utils as db_utils


###################################################
# db_config.initialise_streamlit
###################################################
def test_initialise_streamlit_no_env(unset_db_env):
    """Test Init with no Environment"""
    at = AppTest.from_file("content/db_config.py", default_timeout=30).run()
    assert at.session_state.db_configured is False
    assert at.session_state.db_config["user"] is None
    assert at.session_state.db_config["password"] is None
    assert at.session_state.db_config["dsn"] is None


def test_initialise_streamlit_env(set_db_env):
    """Bad Creds"""
    at = AppTest.from_file("content/db_config.py", default_timeout=30).run()
    assert at.session_state.db_configured is False
    assert at.session_state.db_config["user"] == "TEST_USER"
    assert at.session_state.db_config["password"] == "TEST_PASS"
    assert at.session_state.db_config["dsn"] == "TEST_DSN"


def test_initialise_streamlit_env_mock(set_db_env, mock_oracledb):
    """Good Creds - Mock the connection object"""
    mock_connection = MagicMock()
    mock_oracledb.connect.return_value = mock_connection
    at = AppTest.from_file("content/db_config.py", default_timeout=30).run()
    assert at.session_state.db_configured is True
    assert at.session_state.db_config["user"] == "TEST_USER"
    assert at.session_state.db_config["password"] == "TEST_PASS"
    assert at.session_state.db_config["dsn"] == "TEST_DSN"


###################################################
# db_config.main
###################################################
def test_main_no_env_no_db(unset_db_env, mock_db_utils_connect):
    """Main with no DB access"""
    mock_db_utils_connect.side_effect = db_utils.oracledb.DatabaseError("Connection failed")
    print(f"Mock side effect: {mock_db_utils_connect.side_effect}")

    at = AppTest.from_file("content/db_config.py", default_timeout=30).run()
    assert at.session_state.db_config["user"] is None
    assert at.session_state.db_config["password"] is None
    assert at.session_state.db_config["dsn"] is None
    assert at.session_state.db_configured is False

    # Set two values to raise missing fields
    at.text_input(key="text_input_user").set_value("TEST_USER").run()
    at.text_input(key="text_input_password").set_value("TEST_PASS").run()
    at.button[0].click().run()
    assert at.session_state.db_configured is False
    assert at.error[0].icon == "❌", "All fields are required."

    # Add DSN, but mock connection still raises exception
    at.text_input(key="text_input_dsn").set_value("TEST_DSN").run()
    at.button[0].click().run()
    assert at.session_state.db_configured is False
    assert at.error[0].icon == "🚨", "Connection failed"

    # Establish the mock connection
    mock_db_utils_connect.side_effect = None
    at.button[0].click().run()
    assert at.success[0].icon == "✅", "Database Connectivity Tested Successfully"
    assert at.session_state.db_config["user"] == "TEST_USER"
    assert at.session_state.db_config["password"] == "TEST_PASS"
    assert at.session_state.db_config["dsn"] == "TEST_DSN"
    assert at.success[1].icon == "✅", "Database Configuration Saved"
    assert at.session_state.db_configured is True
