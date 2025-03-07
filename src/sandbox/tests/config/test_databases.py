"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import os
import time
from streamlit.testing.v1 import AppTest


###################################################
# db_config.initialize_streamlit
###################################################
# def test_initialize_streamlit_no_env(unset_db_env):
#     """Test Init with no Environment"""
#     at = AppTest.from_file("content/db_config.py", default_timeout=30).run()
#     assert at.session_state.db_configured is False
#     assert at.session_state.db_config["user"] is None
#     assert at.session_state.db_config["password"] is None
#     assert at.session_state.db_config["dsn"] is None


# def test_initialize_streamlit_env_bad(set_db_env):
#     """Bad Creds"""
#     at = AppTest.from_file("content/db_config.py", default_timeout=30).run()
#     assert at.session_state.db_configured is False
#     assert at.session_state.db_config["user"] == "TEST_USER"
#     assert at.session_state.db_config["password"] == "TEST_PASS"
#     assert at.session_state.db_config["dsn"] == "TEST_DSN"


# def test_initialize_streamlit_env_good(set_db_env):
#     """Good Creds"""
#     at = AppTest.from_file("content/db_config.py", default_timeout=30).run()
#     assert at.session_state.db_configured is False
#     assert at.session_state.db_config["user"] == "TEST_USER"
#     assert at.session_state.db_config["password"] == "TEST_PASS"
#     assert at.session_state.db_config["dsn"] == "TEST_DSN"
    
###################################################
# db_config.main
###################################################
def test_main_config():
    """Main Database Config"""
    at = AppTest.from_file("oaim_sandbox.py", default_timeout=30)
    time.sleep(30)
    at.switch_page("sandbox/content/config/database.py").run()
    print("==============================")
    if at.header:
        print(f"Header found: {at.header[0].value}")
    else:
        print("Header not found on the page!")
    # assert at.button[0].label == "Save"
    # pg.button[0].click()
    # pg.run()
    # assert pg.error[0].icon == "🛑", "Username, Password and Connect String fields are required."

    # at.session_state.server = {
    #     "url": os.getenv("API_SERVER_URL"),
    #     "port": os.getenv("API_SERVER_PORT"),
    #     "key": os.getenv("API_SERVER_KEY")
    # }
    # at.run()
    # # Test with missing fields
    # at.button[0].click().run()
    
    # Test with bad AuthN
    
    
    # Test with good AuthN
    
    
    # assert at.session_state.db_config["user"] is None
    # assert at.session_state.db_config["password"] is None
    # assert at.session_state.db_config["dsn"] is None
    # assert at.session_state.db_configured is False

    # # Set two values to raise missing fields
    # at.text_input(key="text_input_user").set_value("TEST_USER").run()
    # at.text_input(key="text_input_password").set_value("TEST_PASS").run()
    # at.button[0].click().run()
    # assert at.session_state.db_configured is False
    # assert at.error[0].icon == "❌", "All fields are required."

    # # Add DSN, but mock connection still raises exception
    # at.text_input(key="text_input_dsn").set_value("TEST_DSN").run()
    # at.button[0].click().run()
    # assert at.session_state.db_configured is False
    # assert at.error[0].icon == "🚨", "Connection failed"

    # # Establish the mock connection
    # mock_db_connect.side_effect = None
    # at.button[0].click().run()
    # assert at.success[0].icon == "✅", "Database Connectivity Tested Successfully"
    # assert at.session_state.db_config["user"] == "TEST_USER"
    # assert at.session_state.db_config["password"] == "TEST_PASS"
    # assert at.session_state.db_config["dsn"] == "TEST_DSN"
    # assert at.success[1].icon == "✅", "Database Configuration Saved"
    # assert at.session_state.db_configured is True

# def test_main_vs(unset_db_env, mock_db_connect):
