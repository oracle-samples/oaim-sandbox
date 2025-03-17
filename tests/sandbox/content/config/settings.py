"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker: disable
# pylint: disable=import-error

import json
import io
import os
import yaml
import zipfile
import pytest
from unittest.mock import patch, MagicMock, mock_open
from streamlit.testing.v1 import AppTest
from streamlit import session_state as state
import sandbox.content.config.settings as settings
from pathlib import Path


#############################################################################
# Test Settings Functions
#############################################################################
# class TestSettings:
#     """Test the utility functions in the settings module"""

#     def test_save_settings(self):
#         """Test the save_settings function"""
#         # Setup test state
#         with patch("sandbox.content.config.settings.state") as mock_state:
#             mock_state.selected_sensitive_settings = False
#             mock_state.user_settings = {"client": "test_client", "ll_model": {"model": "test-model"}}
#             mock_state.database_config = {"DEFAULT": {"name": "DEFAULT", "password": "secret"}}
#             mock_state.oci_config = {"DEFAULT": {"auth_profile": "DEFAULT", "api_key": "secret"}}
#             mock_state.prompts_config = [{"name": "test", "category": "sys", "prompt": "test prompt"}]
#             mock_state.ll_model_config = {"test-model": {"api": "OpenAI"}}
#             mock_state.embed_model_config = {"test-embed": {"api": "OpenAI"}}

#             # Call the function
#             result = settings.save_settings()

#             # Parse the result
#             saved_settings = json.loads(result)

#             # Verify the result
#             assert "user_settings" in saved_settings
#             assert "database_config" in saved_settings
#             assert "oci_config" in saved_settings
#             assert "prompts_config" in saved_settings
#             assert "ll_model_config" in saved_settings
#             assert "embed_model_config" in saved_settings

#             # Check that sensitive data is not included
#             assert saved_settings["database_config"]["DEFAULT"]["password"] == ""
#             assert saved_settings["oci_config"]["DEFAULT"]["api_key"] == ""

#             # Check that client is not included
#             assert saved_settings["user_settings"]["client"] == ""

#     def test_save_settings_with_sensitive(self):
#         """Test the save_settings function with sensitive data included"""
#         # Setup test state
#         with patch("sandbox.content.config.settings.state") as mock_state:
#             mock_state.selected_sensitive_settings = True
#             mock_state.user_settings = {"client": "test_client", "ll_model": {"model": "test-model"}}
#             mock_state.database_config = {"DEFAULT": {"name": "DEFAULT", "password": "secret"}}
#             mock_state.oci_config = {"DEFAULT": {"auth_profile": "DEFAULT", "api_key": "secret"}}

#             # Call the function
#             result = settings.save_settings()

#             # Parse the result
#             saved_settings = json.loads(result)

#             # Verify sensitive data is included
#             assert saved_settings["database_config"]["DEFAULT"]["password"] == "secret"
#             assert saved_settings["oci_config"]["DEFAULT"]["api_key"] == "secret"

#             # Check that client is still not included (it's always excluded)
#             assert saved_settings["user_settings"]["client"] == ""

#     def test_compare_dicts_recursive(self):
#         """Test the compare_dicts_recursive function"""
#         # Test case with differences
#         current = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
#         uploaded = {"a": 1, "b": {"c": 5, "d": 3}, "e": 6}

#         result = settings.compare_dicts_recursive(current, uploaded)

#         # Verify the result
#         assert "b" in result
#         assert "c" in result["b"]
#         assert result["b"]["c"] == {"current": 2, "uploaded": 5}
#         assert "e" in result
#         assert result["e"] == {"current": 4, "uploaded": 6}

#         # Test case with no differences
#         current = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
#         uploaded = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}

#         result = settings.compare_dicts_recursive(current, uploaded)

#         # Verify the result
#         assert result == {}

#     def test_compare_with_uploaded_json(self):
#         """Test the compare_with_uploaded_json function"""
#         # Test case with differences
#         current_state = {
#             "user_settings": {"client": "test", "ll_model": {"model": "model1"}},
#             "database_config": {"DEFAULT": {"name": "DEFAULT", "password": "secret"}}
#         }
#         uploaded_json = {
#             "user_settings": {"client": "test", "ll_model": {"model": "model2"}},
#             "database_config": {"DEFAULT": {"name": "DEFAULT", "password": "newsecret"}}
#         }

#         result = settings.compare_with_uploaded_json(current_state, uploaded_json)

#         # Verify the result
#         assert "user_settings" in result
#         assert "ll_model" in result["user_settings"]
#         assert "model" in result["user_settings"]["ll_model"]
#         assert result["user_settings"]["ll_model"]["model"] == {"current": "model1", "uploaded": "model2"}
#         assert "database_config" in result
#         assert "DEFAULT" in result["database_config"]
#         assert "password" in result["database_config"]["DEFAULT"]
#         assert result["database_config"]["DEFAULT"]["password"] == {"current": "secret", "uploaded": "newsecret"}

#     def test_update_session_state_recursive(self):
#         """Test the update_session_state_recursive function"""
#         # Setup test session state
#         session_state = {
#             "user_settings": {
#                 "client": "test",
#                 "ll_model": {"model": "model1", "chat_history": True}
#             }
#         }

#         # Updates to apply
#         updates = {
#             "user_settings": {
#                 "ll_model": {"model": "model2", "chat_history": False}
#             }
#         }

#         # Apply updates
#         settings.update_session_state_recursive(session_state, updates)

#         # Verify the updates were applied
#         assert session_state["user_settings"]["ll_model"]["model"] == "model2"
#         assert session_state["user_settings"]["ll_model"]["chat_history"] is False
#         assert session_state["user_settings"]["client"] == "test"  # Unchanged

#     def test_update_server(self):
#         """Test the update_server function"""
#         # Mock the patch functions
#         with patch("sandbox.content.config.settings.patch_database") as mock_patch_db, \
#              patch("sandbox.content.config.settings.patch_oci") as mock_patch_oci, \
#              patch("sandbox.content.config.settings.patch_prompt") as mock_patch_prompt, \
#              patch("sandbox.content.config.settings.patch_model") as mock_patch_model:

#             # Updates to apply
#             updates = {
#                 "database_config": {
#                     "DEFAULT": {"name": "DEFAULT", "user": "user1", "password": "pass1", "dsn": "dsn1"}
#                 },
#                 "oci_config": {
#                     "DEFAULT": {"auth_profile": "DEFAULT", "user": "ociuser", "fingerprint": "fp"}
#                 },
#                 "prompts_config": [
#                     {"name": "prompt1", "category": "sys", "prompt": "system prompt"}
#                 ],
#                 "ll_model_config": {
#                     "model1": {"api": "OpenAI", "enabled": True}
#                 }
#             }

#             # Call the function
#             settings.update_server(updates)

#             # Verify the patch functions were called with the correct arguments
#             mock_patch_db.assert_called_with(
#                 name="DEFAULT", user="user1", password="pass1", dsn="dsn1"
#             )

#             mock_patch_oci.assert_called_with(
#                 auth_profile="DEFAULT", user="ociuser", fingerprint="fp"
#             )

#             mock_patch_prompt.assert_called_with(
#                 name="prompt1", category="sys", prompt="system prompt"
#             )

#             # The model patch is more complex due to the Model object creation
#             mock_patch_model.assert_called()

#     def test_spring_ai_conf_check(self):
#         """Test the spring_ai_conf_check function"""
#         with patch("sandbox.content.config.settings.state") as mock_state:
#             # Test OpenAI configuration
#             mock_state.__getitem__.return_value = {
#                 "test-ll-model": {"api": "OpenAI"},
#                 "test-embed-model": {"api": "OpenAI"}
#             }

#             result = settings.spring_ai_conf_check("test-ll-model", "test-embed-model")
#             assert result == "openai"

#             # Test Ollama configuration
#             mock_state.__getitem__.return_value = {
#                 "test-ll-model": {"api": "ChatOllama"},
#                 "test-embed-model": {"api": "Ollama"}
#             }

#             result = settings.spring_ai_conf_check("test-ll-model", "test-embed-model")
#             assert result == "ollama"

#             # Test hybrid configuration
#             mock_state.__getitem__.return_value = {
#                 "test-ll-model": {"api": "OpenAI"},
#                 "test-embed-model": {"api": "Ollama"}
#             }

#             result = settings.spring_ai_conf_check("test-ll-model", "test-embed-model")
#             assert result == "hybrid"

#             # Test None values
#             result = settings.spring_ai_conf_check(None, "test-embed-model")
#             assert result == "hybrid"

#     def test_spring_ai_obaas(self):
#         """Test the spring_ai_obaas function"""
#         # Mock the state and file operations
#         with patch("sandbox.content.config.settings.state") as mock_state, \
#              patch("builtins.open", mock_open(read_data="provider={provider}\nctx_prompt={ctx_prompt}\n")) as mock_file:

#             # Setup state
#             mock_state.__getitem__.side_effect = lambda key: {
#                 "prompts_config": [
#                     {"name": "test_ctx", "category": "ctx", "prompt": "test context prompt"}
#                 ],
#                 "user_settings": {
#                     "prompts": {"ctx": "test_ctx"},
#                     "ll_model": {"model": "test-model", "temperature": 0.7},
#                     "rag": {"database": "DEFAULT", "rag_enabled": True}
#                 },
#                 "ll_model_enabled": {
#                     "test-model": {"api": "OpenAI", "api_key": "test-key"}
#                 },
#                 "database_config": {
#                     "DEFAULT": {"name": "DEFAULT", "user": "test-user", "password": "test-pass"}
#                 }
#             }.get(key, {})

#             # Create a mock Path
#             mock_src_dir = MagicMock()
#             mock_templates_dir = MagicMock()
#             mock_src_dir.__truediv__.return_value = mock_templates_dir

#             # Call the function for a regular file
#             result = settings.spring_ai_obaas(mock_src_dir, "env.sh", "openai", "test-model")

#             # Verify the result
#             assert "provider=openai" in result
#             assert "ctx_prompt=test context prompt" in result

#             # Test with YAML file
#             mock_file.return_value.read.return_value = "spring:\n  ai:\n    {provider}:\n      ctx_prompt: {ctx_prompt}"

#             # Call the function for a YAML file
#             result = settings.spring_ai_obaas(mock_src_dir, "obaas.yaml", "openai", "test-model")

#             # Verify the result is valid YAML
#             yaml_data = yaml.safe_load(result)
#             assert "spring" in yaml_data
#             assert "ai" in yaml_data["spring"]
#             assert "openai" in yaml_data["spring"]["ai"]
#             assert "ctx_prompt" in yaml_data["spring"]["ai"]["openai"]

#     def test_spring_ai_zip(self):
#         """Test the spring_ai_zip function"""
#         # Mock the necessary functions and objects
#         with patch("sandbox.content.config.settings.Path") as mock_path, \
#              patch("sandbox.content.config.settings.tempfile.TemporaryDirectory") as mock_temp_dir, \
#              patch("sandbox.content.config.settings.shutil.copytree") as mock_copytree, \
#              patch("sandbox.content.config.settings.shutil.copy") as mock_copy, \
#              patch("sandbox.content.config.settings.os.walk") as mock_walk, \
#              patch("sandbox.content.config.settings.spring_ai_obaas") as mock_spring_ai_obaas, \
#              patch("sandbox.content.config.settings.os.path.join", return_value="/mock/path"), \
#              patch("sandbox.content.config.settings.os.path.relpath", return_value="relative/path"):

#             # Setup mocks
#             mock_temp_dir.return_value.__enter__.return_value = "/tmp/mock"
#             mock_path.return_value.resolve.return_value.parents.__getitem__.return_value = "/mock/src"
#             mock_walk.return_value = [
#                 ("/mock/path", [], ["file1.txt", "file2.txt"])
#             ]
#             mock_spring_ai_obaas.side_effect = ["env content", "yaml content"]

#             # Call the function
#             result = settings.spring_ai_zip("openai", "test-model")

#             # Verify the result is a BytesIO object
#             assert isinstance(result, io.BytesIO)

#             # Verify the mocks were called correctly
#             mock_copytree.assert_called_once()
#             assert mock_copy.call_count > 0
#             mock_spring_ai_obaas.assert_any_call("/mock/src", "env.sh", "openai", "test-model")
#             mock_spring_ai_obaas.assert_any_call("/mock/src", "obaas.yaml", "openai", "test-model")


#############################################################################
# Test Streamlit UI
#############################################################################
class TestSettingsUI:
    """Test the Streamlit UI for settings"""

    # Streamlit File
    ST_FILE = "../src/sandbox/content/config/settings.py"

    def test_settings_download(self, app_test):
        """Test the settings download functionality"""
        at = app_test(self.ST_FILE).run()
        # Check the Download Button
        download_button = at.get("download_button")
        print(download_button)
        assert download_button is not None
        assert download_button.label == "Download Settings"
        assert download_button.file_name == "sandbox_settings.json"
        print(download_button.data)
        # Click the Download Button
        at.download_button.click().run()

        # assert download_button.data == '{"test": "data"}'

        # # Mock save_settings to return a known value
        # with patch("sandbox.content.config.settings.save_settings", return_value='{"test": "data"}'):
        #     # Initialize the app
        #     at = app_test("src/sandbox/content/config/settings.py")

        #     # Verify the download button is present

    # def test_settings_upload(self, app_test):
    #     """Test the settings upload functionality"""
    #     at = app_test(self.ST_FILE).run()

    #     # Toggle to upload mode
    #     at.toggle("Upload").set_value(True)

    #     # Verify the file uploader is present
    #     file_uploader = at.get_file_uploader("Upload the Settings file")
    #     assert file_uploader is not None

    #     # Mock the file upload
    #     with patch("sandbox.content.config.settings.compare_with_uploaded_json", return_value={"test": "diff"}), \
    #          patch("sandbox.content.config.settings.update_server") as mock_update_server, \
    #          patch("sandbox.content.config.settings.update_session_state_recursive") as mock_update_session, \
    #          patch("streamlit.success") as mock_success, \
    #          patch("time.sleep"):

    #         # Create a mock file
    #         mock_file = io.BytesIO(b'{"test": "data"}')
    #         mock_file.name = "test_settings.json"

    #         # Upload the file
    #         file_uploader.upload(mock_file)

    #         # Verify the differences are displayed
    #         assert at.get_subheader("Differences found:") is not None

    #         # Click the apply button
    #         at.button("Apply New Settings").click()

    #         # Verify the update functions were called
    #         mock_update_server.assert_called_once()
    #         mock_update_session.assert_called_once()
    #         mock_success.assert_called_once()

    # def test_spring_ai_settings(self, app_test):
    #     """Test the SpringAI settings section"""
    #     # Mock the spring_ai_conf_check and spring_ai_zip functions
    #     with patch("sandbox.content.config.settings.spring_ai_conf_check", return_value="openai"), \
    #          patch("sandbox.content.config.settings.spring_ai_zip", return_value=io.BytesIO(b"test data")), \
    #          patch("sandbox.content.config.settings.state") as mock_state:

    #         # Setup state
    #         mock_state.__getitem__.return_value = {"ll_model": {"model": "test-model"}, "rag": {"model": "test-embed"}}

    #         # Initialize the app
    #         at = app_test("src/sandbox/content/config/settings.py")

    #         # Verify the SpringAI header is present
    #         assert at.get_header("SpringAI Settings") is not None

    #         # Verify the download button is present
    #         download_button = at.get_download_button("Download SpringAI")
    #         assert download_button is not None
    #         assert download_button.label == "Download SpringAI"
    #         assert download_button.file_name == "spring_ai.zip"
    #         assert download_button.mime == "application/zip"
    #         assert download_button.disabled is False
