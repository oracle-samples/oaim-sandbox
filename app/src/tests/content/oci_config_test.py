"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# pylint: disable=unused-argument

from streamlit.testing.v1 import AppTest


###################################################
# oci_config.initialise_streamlit
###################################################
def test_initialise_streamlit_no_env(unset_oci_env):
    """Initialisation of streamlit without any OCI environment"""
    at = AppTest.from_file("content/oci_config.py", default_timeout=30).run()
    assert at.session_state.oci_configured is False
    assert at.session_state.oci_config["tenancy"] is None
    assert at.session_state.oci_config["region"] is None
    assert at.session_state.oci_config["fingerprint"] is None
    assert at.session_state.oci_config["key_file"] is None
    assert at.session_state.oci_config["user"] is None
    assert at.session_state.oci_config["security_token_file"] is None


def test_initialise_streamlit_env_user(set_oci_env_user):
    """Initialisation of streamlit with user AuthN OCI environment"""
    at = AppTest.from_file("content/oci_config.py", default_timeout=30).run()
    assert at.session_state.oci_configured is False
    at.radio(key="radio_auth_source").set_value("User").run()
    assert at.radio(key="radio_auth_source").value == "User"
    assert at.session_state.oci_config["tenancy"] == "TEST_TENANCY"
    assert at.session_state.oci_config["region"] == "TEST_REGION"
    assert at.session_state.oci_config["fingerprint"] == "TEST_FINGERPRINT"
    assert at.session_state.oci_config["key_file"] == "TEST_KEY_FILE"
    assert at.session_state.oci_config["user"] == "TEST_USER"
    assert at.session_state.oci_config["security_token_file"] is None


def test_initialise_streamlit_token(set_oci_env_token):
    """Initialisation of streamlit with token AuthN OCI environment"""
    at = AppTest.from_file("content/oci_config.py", default_timeout=30).run()
    assert at.session_state.oci_configured is False
    # Testing that when a security_token_file is found, Token is the default
    assert at.radio(key="radio_auth_source").value == "Token"
    assert at.session_state.oci_config["tenancy"] == "TEST_TENANCY"
    assert at.session_state.oci_config["region"] == "TEST_REGION"
    assert at.session_state.oci_config["fingerprint"] == "TEST_FINGERPRINT"
    assert at.session_state.oci_config["key_file"] == "TEST_KEY_FILE"
    assert at.session_state.oci_config["user"] is None
    assert at.session_state.oci_config["security_token_file"] == "TEST_SECURITY_TOKEN_FILE"


###################################################
# oci_config.main
###################################################
def test_main_no_env_user_failure(unset_oci_env):
    """Main with no User Env - Fail Case"""
    at = AppTest.from_file("content/oci_config.py", default_timeout=30).run()
    assert at.session_state.oci_configured is False
    at.radio(key="radio_auth_source").set_value("User").run()
    at.text_input(key="text_input_fingerprint").set_value("TEST_FINGERPRINT").run()
    at.text_input(key="text_input_tenancy").set_value("TEST_TENANCY").run()
    at.text_input(key="text_input_region").set_value("TEST_REGION").run()
    at.text_input(key="text_input_key_file").set_value("TEST_KEY_FILE").run()
    at.button[0].click().run()
    assert at.error[0].icon == "❌", "All fields are required."
    at.text_input(key="text_input_user").set_value("TEST_USER").run()
    at.button[0].click().run()
    assert at.error[0].icon == "🚨", "All fields are required."
    assert at.session_state.oci_configured is False


def test_main_no_env_user(unset_oci_env, mock_oci_get_namespace):
    """Main with creating User AuthN - Success Case"""
    at = AppTest.from_file("content/oci_config.py", default_timeout=30).run()
    at.radio(key="radio_auth_source").set_value("User").run()
    at.text_input(key="text_input_fingerprint").set_value("TEST_FINGERPRINT").run()
    at.text_input(key="text_input_tenancy").set_value("TEST_TENANCY").run()
    at.text_input(key="text_input_region").set_value("TEST_REGION").run()
    at.text_input(key="text_input_key_file").set_value("TEST_KEY_FILE").run()
    at.text_input(key="text_input_user").set_value("TEST_USER").run()
    at.text_input(key="text_input_security_token_file").set_value("TEST_SECURITY_TOKEN_FILE").run()
    at.button[0].click().run()
    assert at.session_state.oci_configured is True
    assert at.success[0].icon == "✅", "OCI API Authentication Tested Successfully"
    assert at.session_state.oci_config["tenancy"] == "TEST_TENANCY"
    assert at.session_state.oci_config["region"] == "TEST_REGION"
    assert at.session_state.oci_config["fingerprint"] == "TEST_FINGERPRINT"
    assert at.session_state.oci_config["key_file"] == "TEST_KEY_FILE"
    assert at.session_state.oci_config["user"] == "TEST_USER"
    assert at.session_state.oci_config["security_token_file"] is None
    assert at.success[1].icon == "✅", "OCI Configuration Saved"


def test_main_no_env_token(unset_oci_env, mock_oci_get_namespace):
    """Main with creating Token AuthN - Success Case"""
    at = AppTest.from_file("content/oci_config.py", default_timeout=30).run()
    at.radio(key="radio_auth_source").set_value("Token").run()
    at.text_input(key="text_input_fingerprint").set_value("TEST_FINGERPRINT").run()
    at.text_input(key="text_input_tenancy").set_value("TEST_TENANCY").run()
    at.text_input(key="text_input_region").set_value("TEST_REGION").run()
    at.text_input(key="text_input_key_file").set_value("TEST_KEY_FILE").run()
    at.text_input(key="text_input_user").set_value("TEST_USER").run()
    at.text_input(key="text_input_security_token_file").set_value("TEST_SECURITY_TOKEN_FILE").run()
    at.button[0].click().run()
    assert at.session_state.oci_configured is True
    assert at.success[0].icon == "✅", "OCI API Authentication Tested Successfully"
    assert at.session_state.oci_config["tenancy"] == "TEST_TENANCY"
    assert at.session_state.oci_config["region"] == "TEST_REGION"
    assert at.session_state.oci_config["fingerprint"] == "TEST_FINGERPRINT"
    assert at.session_state.oci_config["key_file"] == "TEST_KEY_FILE"
    assert at.session_state.oci_config["user"] is None
    assert at.session_state.oci_config["security_token_file"] == "TEST_SECURITY_TOKEN_FILE"
    assert at.success[1].icon == "✅", "OCI Configuration Saved"
