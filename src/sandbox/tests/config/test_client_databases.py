"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import re
from conftest import COMMON_VARS
import pytest


def test_missing_details(app_test):
    """Submits with missing required inputs"""
    at = app_test("sandbox/content/config/databases.py").run()
    assert at.session_state.database_config is not None
    at.button[0].click().run()
    assert at.error[0].value == "Current Status: Disconnected"
    assert (
        at.error[1].value == "Unable to perform update: Not all connection details supplied."
        and at.error[1].icon == "🚨"
    )
    assert at.session_state.database_config["DEFAULT"]["user"] is None
    assert at.session_state.database_config["DEFAULT"]["password"] is None
    assert at.session_state.database_config["DEFAULT"]["dsn"] is None
    assert at.session_state.database_config["DEFAULT"]["wallet_password"] is None
    assert at.session_state.database_config["DEFAULT"]["wallet_location"] is None
    assert at.session_state.database_config["DEFAULT"]["config_dir"] is not None
    assert at.session_state.database_config["DEFAULT"]["tcp_connect_timeout"] is not None
    assert at.session_state.database_config["DEFAULT"]["connected"] is False
    assert at.session_state.database_config["DEFAULT"]["vector_stores"] is None


def test_wrong_details(app_test):
    """Submits with wrong details"""
    at = app_test("sandbox/content/config/databases.py").run()
    assert at.session_state.database_config is not None
    at.text_input(key="database_user").set_value(COMMON_VARS["database_user"]).run()
    at.text_input(key="database_password").set_value(COMMON_VARS["database_password"]).run()
    at.text_input(key="database_dsn").set_value(COMMON_VARS["database_dsn"]).run()
    at.button[0].click().run()
    assert at.error[0].value == "Current Status: Disconnected"
    assert at.error[1].value == "Unable to perform update: Unable to connect to database." and at.error[1].icon == "🚨"
    assert at.session_state.database_config["DEFAULT"]["user"] is None
    assert at.session_state.database_config["DEFAULT"]["password"] is None
    assert at.session_state.database_config["DEFAULT"]["dsn"] is None
    assert at.session_state.database_config["DEFAULT"]["wallet_password"] is None
    assert at.session_state.database_config["DEFAULT"]["wallet_location"] is None
    assert at.session_state.database_config["DEFAULT"]["config_dir"] is not None
    assert at.session_state.database_config["DEFAULT"]["tcp_connect_timeout"] is not None
    assert at.session_state.database_config["DEFAULT"]["connected"] is False
    assert at.session_state.database_config["DEFAULT"]["vector_stores"] is None


def test_connected(app_test, db_container):
    """Sumbits with good DSN"""
    assert db_container is not None
    at = app_test("sandbox/content/config/databases.py").run()
    assert at.session_state.database_config is not None
    at.text_input(key="database_user").set_value(COMMON_VARS["database_user"]).run()
    at.text_input(key="database_password").set_value(COMMON_VARS["database_password"]).run()
    at.text_input(key="database_dsn").set_value(COMMON_VARS["database_dsn"]).run()
    at.button[0].click().run()
    assert at.success[0].value == "Current Status: Connected"
    assert at.toast[0].value == "Update Successful." and at.toast[0].icon == "✅"
    at.button[0].click().run()
    assert at.info[0].value == "DEFAULT Database Configuration - No Changes Detected." and at.info[0].icon == "ℹ️"
    assert at.session_state.database_config["DEFAULT"]["user"] == COMMON_VARS["database_user"]
    assert at.session_state.database_config["DEFAULT"]["password"] == COMMON_VARS["database_password"]
    assert at.session_state.database_config["DEFAULT"]["dsn"] == COMMON_VARS["database_dsn"]
    assert at.session_state.database_config["DEFAULT"]["wallet_password"] is None
    assert at.session_state.database_config["DEFAULT"]["wallet_location"] is None
    assert at.session_state.database_config["DEFAULT"]["config_dir"] is not None
    assert at.session_state.database_config["DEFAULT"]["tcp_connect_timeout"] is not None
    assert at.session_state.database_config["DEFAULT"]["connected"] is True
    assert at.session_state.database_config["DEFAULT"]["vector_stores"] == []


test_disconnected_input = [
    (
        "ADMIN",
        COMMON_VARS["database_password"],
        COMMON_VARS["database_dsn"],
        "Unable to perform update: Invalid database credentials.",
    ),
    (
        COMMON_VARS["database_user"],
        "Wr0ng_P4ssW0rd",
        COMMON_VARS["database_dsn"],
        "Unable to perform update: Invalid database credentials.",
    ),
    (
        COMMON_VARS["database_user"],
        COMMON_VARS["database_password"],
        "//localhost:1521/WRONG_TP",
        "Unable to perform update: Unable to connect to database.",
    ),
    (
        COMMON_VARS["database_user"],
        COMMON_VARS["database_password"],
        "WRONG_TP",
        r"Unable to perform update: DPY-4000: .*",
    ),
]


@pytest.mark.parametrize("username, password, dsn, error_msg", test_disconnected_input)
def test_disconnected(app_test, db_container, username, password, dsn, error_msg):
    """Submits with incorrect details"""
    assert db_container is not None
    at = app_test("sandbox/content/config/databases.py").run()
    assert at.session_state.database_config is not None
    at.text_input(key="database_user").set_value(username).run()
    at.text_input(key="database_password").set_value(password).run()
    at.text_input(key="database_dsn").set_value(dsn).run()
    at.button[0].click().run()
    assert at.error[0].value == "Current Status: Disconnected"
    assert re.match(error_msg, at.error[1].value) and at.error[1].icon == "🚨"
    # Due to the connection error, the settings should NOT be updated and be set
    # to previous successful test connection; connected will be False for error handling
    assert at.session_state.database_config["DEFAULT"]["user"] == COMMON_VARS["database_user"]
    assert at.session_state.database_config["DEFAULT"]["password"] == COMMON_VARS["database_password"]
    assert at.session_state.database_config["DEFAULT"]["dsn"] == COMMON_VARS["database_dsn"]
    assert at.session_state.database_config["DEFAULT"]["wallet_password"] is None
    assert at.session_state.database_config["DEFAULT"]["wallet_location"] is None
    assert at.session_state.database_config["DEFAULT"]["config_dir"] is not None
    assert at.session_state.database_config["DEFAULT"]["tcp_connect_timeout"] is not None
    assert at.session_state.database_config["DEFAULT"]["connected"] is False
    assert at.session_state.database_config["DEFAULT"]["vector_stores"] == []
