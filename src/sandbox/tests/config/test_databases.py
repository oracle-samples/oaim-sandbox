"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable

COMMON_VARS = {
    "database_user": "SYSTEM",
    "database_password": "T35t_D4t4-B4s3",
    "database_dsn": "//localhost:1521/FREEPDB1",
    "database_name": "FREEPDB1",
}


###################################################
# db_config.main
###################################################
def test_main_missing_details(app_test):
    """Main Database Config"""
    at = app_test("sandbox/content/config/database.py").run()
    assert at.session_state.database_config is not None
    at.button[0].click().run()
    assert at.error[0].value == "Current Status: Disconnected"
    assert (
        at.error[1].value == "Unable to perform update: Not all connection details supplied."
        and at.error[1].icon == "🚨"
    )


def test_main_wrong_details(app_test):
    """Main Database Config"""
    at = app_test("sandbox/content/config/database.py").run()
    assert at.session_state.database_config is not None
    at.text_input(key="database_user").set_value(COMMON_VARS["database_user"]).run()
    at.text_input(key="database_password").set_value(COMMON_VARS["database_password"]).run()
    at.text_input(key="database_dsn").set_value(COMMON_VARS["database_dsn"]).run()
    at.button[0].click().run()
    assert at.error[0].value == "Current Status: Disconnected"
    assert at.error[1].value == "Unable to perform update: Unable to connect to database." and at.error[1].icon == "🚨"


def test_main_dsn(app_test, db_container):
    """Main Database Config"""
    assert db_container is not None
    at = app_test("sandbox/content/config/database.py").run()
    assert at.session_state.database_config is not None
    at.text_input(key="database_user").set_value(COMMON_VARS["database_user"]).run()
    at.text_input(key="database_password").set_value(COMMON_VARS["database_password"]).run()
    at.text_input(key="database_dsn").set_value(COMMON_VARS["database_dsn"]).run()
    at.button[0].click().run()
    assert at.success[0].value == "Current Status: Connected"
    assert at.toast[0].value == "Update Successful." and at.toast[0].icon == "✅"
    at.button[0].click().run()
    assert at.info[0].value == "DEFAULT Database Configuration - No Changes Detected." and at.info[0].icon == "ℹ️"


def test_main_bad_auth(app_test, db_container):
    """Main Database Config"""
    assert db_container is not None
    at = app_test("sandbox/content/config/database.py").run()
    assert at.session_state.database_config is not None
    at.text_input(key="database_user").set_value(COMMON_VARS["database_user"]).run()
    at.text_input(key="database_password").set_value("Wr0ng_P4ssWord").run()
    at.text_input(key="database_dsn").set_value(COMMON_VARS["database_dsn"]).run()
    at.button[0].click().run()
    assert at.error[0].value == "Current Status: Disconnected"
    assert at.error[1].value == "Unable to perform update: Invalid database credentials." and at.error[1].icon == "🚨"
