"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=unused-argument

import pytest
# from conftest import TEST_CONFIG


class TestOCI:
    """Test OCI"""

    ST_FILE = "../src/sandbox/content/config/oci.py"

    def test_initialise_streamlit_no_env(self, app_test):
        """Initialisation of streamlit without any OCI environment"""
        at = app_test(self.ST_FILE).run()
        user_oci_profile = at.session_state.user_settings["oci"]["auth_profile"]
        assert user_oci_profile == "DEFAULT"
        assert at.session_state.oci_config[user_oci_profile]["namespace"] is None
        assert at.session_state.oci_config[user_oci_profile]["user"] is None
        assert at.session_state.oci_config[user_oci_profile]["security_token_file"] is None
        assert at.session_state.oci_config[user_oci_profile]["tenancy"] is None
        assert at.session_state.oci_config[user_oci_profile]["region"] is None
        assert at.session_state.oci_config[user_oci_profile]["fingerprint"] is None
        assert at.session_state.oci_config[user_oci_profile]["key_file"] is None
        assert at.session_state.oci_config[user_oci_profile]["service_endpoint"] == ""

    test_cases = [
        pytest.param(
            {
                "oci_token_auth": False,
                "expected_error": "Update Failed - OCI: Invalid Config",
            },
            id="oci_profile_1",
        ),
        pytest.param(
            {
                "oci_token_auth": False,
                "oci_user": "ocid1.user.oc1..aaaaaaaa",
                "expected_error": "Update Failed - OCI: Invalid Config",
            },
            id="oci_profile_3",
        ),
        pytest.param(
            {
                "oci_token_auth": False,
                "oci_user": "ocid1.user.oc1..aaaaaaaa",
                "oci_fingerprint": "e8:65:45:4a:85:4b:6c:51:63:b8:84:64:ef:36:16:7b",
                "expected_error": "Update Failed - OCI: Invalid Config",
            },
            id="oci_profile_4",
        ),
        pytest.param(
            {
                "oci_token_auth": False,
                "oci_user": "ocid1.user.oc1..aaaaaaaa",
                "oci_fingerprint": "e8:65:45:4a:85:4b:6c:51:63:b8:84:64:ef:36:16:7b",
                "oci_tenancy": "ocid1.tenancy.oc1..aaaaaaaa",
                "expected_error": "Update Failed - OCI: Invalid Key Path",
            },
            id="oci_profile_5",
        ),
        pytest.param(
            {
                "oci_token_auth": False,
                "oci_user": "ocid1.user.oc1..aaaaaaaa",
                "oci_fingerprint": "e8:65:45:4a:85:4b:6c:51:63:b8:84:64:ef:36:16:7b",
                "oci_tenancy": "ocid1.tenancy.oc1..aaaaaaaa",
                "oci_region": "us-ashburn-1",
                "expected_error": "Update Failed - OCI: Invalid Key Path",
            },
            id="oci_profile_6",
        ),
        pytest.param(
            {
                "oci_token_auth": False,
                "oci_user": "ocid1.user.oc1..aaaaaaaa",
                "oci_fingerprint": "e8:65:45:4a:85:4b:6c:51:63:b8:84:64:ef:36:16:7b",
                "oci_tenancy": "ocid1.tenancy.oc1..aaaaaaaa",
                "oci_region": "us-ashburn-1",
                "oci_key_file": "/dev/null",
                "expected_error": "Update Failed - OCI: The provided key is not a private key, or the provided passphrase is incorrect.",
                "expected_success": True,
            },
            id="oci_profile_7",
        ),
    ]

    def set_patch_oci(self, at, test_case):
        """Set values"""
        at.checkbox(key="oci_token_auth").set_value(test_case["oci_token_auth"]).run()
        at.text_input(key="oci_user").set_value(test_case.get("oci_user", "")).run()
        at.text_input(key="oci_security_token_file").set_value(test_case.get("oci_security_token_file", "")).run()
        at.text_input(key="oci_fingerprint").set_value(test_case.get("oci_fingerprint", "")).run()
        at.text_input(key="oci_tenancy").set_value(test_case.get("oci_tenancy", "")).run()
        at.text_input(key="oci_region").set_value(test_case.get("oci_region", "")).run()
        at.text_input(key="oci_key_file").set_value(test_case.get("oci_key_file", "")).run()

    @pytest.mark.parametrize("test_case", test_cases)
    def test_patch_oci(self, app_test, test_case):
        """Updata OCI Profile Settings"""
        at = app_test(self.ST_FILE).run()
        user_oci_profile = at.session_state.user_settings["oci"]["auth_profile"]
        assert at.selectbox(key="selected_oci_profile").value == user_oci_profile
        self.set_patch_oci(at, test_case)
        at.button[0].click().run()
        assert at.error[0].value == "Current Status: Unverified"
        assert at.error[1].value == test_case["expected_error"]

    @pytest.mark.parametrize("test_case", test_cases)
    def test_patch_oci_mocks(self, app_test, test_case, mock_get_namespace):
        """Updata OCI Profile Settings"""
        assert mock_get_namespace is not None
        at = app_test(self.ST_FILE).run()
        user_oci_profile = at.session_state.user_settings["oci"]["auth_profile"]
        assert at.selectbox(key="selected_oci_profile").value == user_oci_profile
        self.set_patch_oci(at, test_case)
        at.button[0].click().run()
        if test_case.get("expected_success", False):
            assert at.success[0].value == f"Current Status: Validated - Namespace: {mock_get_namespace.return_value}"


#     def test_main_no_env_user_failure(self, unset_oci_env):
#         """Main with no User Env - Fail Case"""
#         at = app_test(self.ST_FILE).run()
#         assert at.session_state.oci_configured is False
#         at.radio(key="radio_auth_source").set_value("User").run()
#         at.text_input(key="text_input_fingerprint").set_value("TEST_FINGERPRINT").run()
#         at.text_input(key="text_input_tenancy").set_value("TEST_TENANCY").run()
#         at.text_input(key="text_input_region").set_value("TEST_REGION").run()
#         at.text_input(key="text_input_key_file").set_value("TEST_KEY_FILE").run()
#         at.button[0].click().run()
#         assert at.error[0].icon == "❌", "All fields are required."
#         at.text_input(key="text_input_user").set_value("TEST_USER").run()
#         at.button[0].click().run()
#         assert at.error[0].icon == "🚨", "All fields are required."
#         assert at.session_state.oci_configured is False

#     def test_main_no_env_user(self, unset_oci_env, mock_oci_get_namespace):
#         """Main with creating User AuthN - Success Case"""
#         at = app_test(self.ST_FILE).run()
#         at.radio(key="radio_auth_source").set_value("User").run()
#         at.text_input(key="text_input_fingerprint").set_value("TEST_FINGERPRINT").run()
#         at.text_input(key="text_input_tenancy").set_value("TEST_TENANCY").run()
#         at.text_input(key="text_input_region").set_value("TEST_REGION").run()
#         at.text_input(key="text_input_key_file").set_value("TEST_KEY_FILE").run()
#         at.text_input(key="text_input_user").set_value("TEST_USER").run()
#         at.text_input(key="text_input_security_token_file").set_value("TEST_SECURITY_TOKEN_FILE").run()
#         at.button[0].click().run()
#         assert at.session_state.oci_configured is True
#         assert at.success[0].icon == "✅", "OCI API Authentication Tested Successfully"
#         assert at.session_state.oci_config["tenancy"] == "TEST_TENANCY"
#         assert at.session_state.oci_config["region"] == "TEST_REGION"
#         assert at.session_state.oci_config["fingerprint"] == "TEST_FINGERPRINT"
#         assert at.session_state.oci_config["key_file"] == "TEST_KEY_FILE"
#         assert at.session_state.oci_config["user"] == "TEST_USER"
#         assert at.session_state.oci_config["security_token_file"] is None
#         assert at.success[1].icon == "✅", "OCI Configuration Saved"

#     def test_main_no_env_token(self, unset_oci_env, mock_oci_get_namespace):
#         """Main with creating Token AuthN - Success Case"""
#         at = app_test(self.ST_FILE).run()
#         at.radio(key="radio_auth_source").set_value("Token").run()
#         at.text_input(key="text_input_fingerprint").set_value("TEST_FINGERPRINT").run()
#         at.text_input(key="text_input_tenancy").set_value("TEST_TENANCY").run()
#         at.text_input(key="text_input_region").set_value("TEST_REGION").run()
#         at.text_input(key="text_input_key_file").set_value("TEST_KEY_FILE").run()
#         at.text_input(key="text_input_user").set_value("TEST_USER").run()
#         at.text_input(key="text_input_security_token_file").set_value("TEST_SECURITY_TOKEN_FILE").run()
#         at.button[0].click().run()
#         assert at.session_state.oci_configured is True
#         assert at.success[0].icon == "✅", "OCI API Authentication Tested Successfully"
#         assert at.session_state.oci_config["tenancy"] == "TEST_TENANCY"
#         assert at.session_state.oci_config["region"] == "TEST_REGION"
#         assert at.session_state.oci_config["fingerprint"] == "TEST_FINGERPRINT"
#         assert at.session_state.oci_config["key_file"] == "TEST_KEY_FILE"
#         assert at.session_state.oci_config["user"] is None
#         assert at.session_state.oci_config["security_token_file"] == "TEST_SECURITY_TOKEN_FILE"
#         assert at.success[1].icon == "✅", "OCI Configuration Saved"
