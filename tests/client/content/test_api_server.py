"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import os
from unittest.mock import patch, MagicMock
import pytest
from conftest import TEST_CONFIG


# Create a custom Exception class for ApiError
class MockApiError(Exception):
    """Mock API Error class"""

    pass


#############################################################################
# Test Server Functions
#############################################################################
class TestServerFunctions:
    """Test the utility functions in launch_server.py"""

    def test_copy_user_settings_success(self, monkeypatch, app_test):
        """Test the copy_user_settings function with a successful API call"""
        # Import the function to test
        from client.content.api_server import copy_user_settings

        # Initialize app_test to get the session state
        at = app_test("../src/client/content/launch_server.py")

        # Mock the API call to ensure a successful response
        mock_api_call = MagicMock()

        # Mock the streamlit UI components
        mock_st = MagicMock()
        mock_st_common = MagicMock()

        monkeypatch.setattr("client.content.api_server.api_call", mock_api_call)
        monkeypatch.setattr("client.content.api_server.st", mock_st)
        monkeypatch.setattr("client.content.api_server.st_common", mock_st_common)
        monkeypatch.setattr("client.content.api_server.logger", MagicMock())

        # Use the actual session state instead of mocking
        # We only need to modify .user_settings for this test
        at.session_state.user_settings = {"key": "value"}
        monkeypatch.setattr("client.content.api_server.state", at.session_state)

        # Call the function
        copy_user_settings("test_client")

        # Verify patch was called with correct parameters
        mock_api_call.patch.assert_called_once_with(
            endpoint="v1/settings",
            payload={"json": {"key": "value"}},
        )

        # Verify success message was shown
        mock_st.success.assert_called_once_with("Settings for test_client - Updated", icon="✅")
        # Verify state was cleared
        mock_st_common.clear_state_key.assert_called_once_with("test_client_settings")

    def test_copy_user_settings_error(self, monkeypatch, app_test):
        """Test the copy_user_settings function when an error occurs"""
        # Import the function to test
        from client.content.api_server import copy_user_settings

        # Initialize app_test to get the session state
        at = app_test("../src/client/content/launch_server.py")

        # Still need to mock API for error testing
        mock_api_call = MagicMock()
        mock_api_call.ApiError = MockApiError  # Set the ApiError class
        mock_api_call.patch.side_effect = MockApiError("API Error")

        mock_st = MagicMock()
        mock_logger = MagicMock()

        monkeypatch.setattr("client.content.api_server.api_call", mock_api_call)
        monkeypatch.setattr("client.content.api_server.st", mock_st)
        monkeypatch.setattr("client.content.api_server.st_common", MagicMock())
        monkeypatch.setattr("client.content.api_server.logger", mock_logger)

        # Use the actual session state - only need to modify user_settings
        at.session_state.user_settings = {"key": "value"}
        monkeypatch.setattr("client.content.api_server.state", at.session_state)

        # Call the function
        copy_user_settings("test_client")

        # Verify error message was shown
        mock_st.success.assert_called_once_with("Settings for test_client - Update Failed", icon="❌")
        # Verify error was logged
        mock_logger.error.assert_called_once()

    def test_copy_user_settings_real_api(self, monkeypatch, app_test):
        """Test the copy_user_settings function with real API call - just verify it doesn't crash"""
        # Import the function to test
        from client.content.api_server import copy_user_settings

        # Use app_test to get the properly initialized session state
        at = app_test("../src/client/content/launch_server.py")

        # Mock only the streamlit UI components
        mock_st = MagicMock()
        mock_st_common = MagicMock()

        monkeypatch.setattr("client.content.api_server.st", mock_st)
        monkeypatch.setattr("client.content.api_server.st_common", mock_st_common)
        monkeypatch.setattr("client.content.api_server.logger", MagicMock())

        # Use the actual session state directly - no need to create a MockState class
        monkeypatch.setattr("client.content.api_server.state", at.session_state)
        monkeypatch.setattr("client.utils.api_call.state", at.session_state)

        # Call the function
        copy_user_settings(TEST_CONFIG["test_client"])

        # Assert that st.success was called (don't check the exact message)
        assert mock_st.success.called

    @patch("launch_server.stop_server")
    @patch("launch_server.start_server")
    @patch("time.sleep")
    def test_server_restart(self, mock_sleep, mock_start_server, mock_stop_server, monkeypatch, app_test):
        """Test the server_restart function using the conftest environment variables"""
        # Import the function to test
        from client.content.api_server import server_restart

        # Initialize app_test to get session state
        at = app_test("../src/client/content/api_server.py")

        # Get the environment variables already set by conftest.py
        server_key = os.environ["API_SERVER_KEY"]
        server_port = int(os.environ["API_SERVER_PORT"])

        # Need to modify session state for specific test values
        # For server_restart we need to set specific values to check functionality
        at.session_state.user_server_key = server_key
        at.session_state.user_server_port = server_port

        # Need to set a specific PID to verify it's used for stopping the server
        at.session_state.server["pid"] = 12345

        # Mock a method that might not be present in the actual session state
        original_pop = getattr(at.session_state, "pop", None)

        def mock_pop(key, default=None):
            """Mock the pop method if it doesn't exist"""
            if original_pop:
                return original_pop(key, default)
            return None

        at.session_state.pop = mock_pop

        # Use the actual session state
        monkeypatch.setattr("client.content.api_server.state", at.session_state)
        monkeypatch.setattr("client.content.api_server.logger", MagicMock())

        # Call the function - no need to mock os since conftest.py sets environment variables
        server_restart()

        # Verify the server state was updated
        assert os.environ["API_SERVER_KEY"] == server_key

        # Verify the server was stopped and restarted
        mock_stop_server.assert_called_once_with(12345)
        mock_start_server.assert_called_once_with(server_port)
        mock_sleep.assert_called_once_with(10)
