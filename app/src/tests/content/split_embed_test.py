"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# pylint: disable=unused-argument, invalid-name

from streamlit.testing.v1 import AppTest


######################################
# Initialise
######################################
def test_db_initialise_streamlit(unset_db_env):
    """DB is not configured"""
    at = AppTest.from_file("content/split_embed.py", default_timeout=30).run()
    assert at.session_state.db_configured is False
    assert at.error[0].icon == "🚨", "Database is not configured, all functionality is disabled"


######################################
# Local Source
######################################
def test_split_embed_local(set_db_env, mock_oracledb, mock_is_url_accessible, set_api_env):
    """A user splits and embeds from a Local File
    Currently there is no way to test this
    """
    at = AppTest.from_file("content/split_embed.py", default_timeout=30).run()
    assert at.session_state.db_configured is True
    at.radio(key="radio_file_source").set_value("Local").run()
    assert at.button(key="button_local_load").disabled is True
    # assert at.button(key="button_local_load").disabled is False
    # at.button(key="button_local_load").click().run()

    # # Capture error message if failure
    # assert len(at.error) == 0, "File Load, Split, Embed Failed"
    # assert len(at.success) == 1, "File Load, Split, Embed Failed"


######################################
# Web Source
######################################
def test_split_embed_web_HuggingFaceEndpointEmbeddings(set_db_env, mock_oracledb, mock_is_url_accessible):
    """A user splits and embeds from a Web URL"""
    test_url = "https://docs.oracle.com/en/cloud/paas/autonomous_database/dedicated/adbau/"
    model_name = "thenlper/gte-base"
    check_box  = f"embed_{model_name}_enabled"
    api_field = f"embed_{model_name}_api_server"

    at = AppTest.from_file("content/model_config.py", default_timeout=30).run()
    at.checkbox(key=check_box).set_value(True).run()
    at.text_input(key=api_field).set_value("http://127.0.0.1:8080").run()
    at.button[0].click().run()
    assert len(at.success) == 1, "Embedding Model Configuration Saved"
    assert at.session_state.embed_model_config[model_name]["enabled"] is True
    assert at.session_state.embed_model_config[model_name]["url"] == ("http://127.0.0.1:8080")

    # The first run initialises the embed_model_config
    at = AppTest.from_file("content/split_embed.py", default_timeout=30).run()
    at.session_state.embed_model_config[model_name]["enabled"] = True
    # The second run ensures the selectbox has enabled models
    at.run()
    assert at.session_state.db_configured is True
    at.selectbox(key="select_box_embed_model").set_value(model_name).run()
    assert at.selectbox(key="select_box_embed_model").value == model_name
    at.session_state.embed_model_config[model_name]["url"] = "http://127.0.0.1:8080"
    at.radio(key="radio_file_source").set_value("Web").run()
    assert at.button(key="button_web_load").disabled is True
    at.text_input(key="text_input_web_url").set_value(test_url).run()
    assert at.button(key="button_web_load").disabled is False
    at.button(key="button_web_load").click().run()

    # TODO(gotsysdba) Should be successful, but DB not being mocked correctly
    assert len(at.error) == 1, "Web Load, Split, Embed Failed"
    assert len(at.success) == 0, "Web Load, Split, Embed Failed"

def test_split_embed_web_OpenAIEmbeddings_not_enabled(unset_api_env, set_db_env, mock_oracledb):
    """A user splits and embeds from a Web URL; OpenAIEmbeddings with No API Key"""
    at = AppTest.from_file("content/split_embed.py", default_timeout=30).run()
    assert at.session_state.db_configured is True
    assert len(at.error) == 1, "No embedding models are are configured and/or enabled."

def test_split_embed_web_OpenAIEmbeddings_no_key(unset_api_env, set_db_env, mock_oracledb):
    """A user splits and embeds from a Web URL; OpenAIEmbeddings with No API Key"""
    at = AppTest.from_file("content/split_embed.py", default_timeout=30).run()
    assert at.session_state.db_configured is True
    at.session_state.embed_model_config["text-embedding-3-small"]["enabled"] = True
    at.selectbox(key="select_box_embed_model").set_value("text-embedding-3-small").run()
    assert len(at.error) == 1, "Please configure the OpenAI API Key"


def test_split_embed_web_OpenAIEmbeddings_manual_key(unset_api_env, set_db_env, mock_oracledb):
    """A user splits and embeds from a Web URL; OpenAIEmbeddings with API Key"""
    test_url = "https://docs.oracle.com/en/cloud/paas/autonomous_database/dedicated/adbau/"
    model_name = "text-embedding-3-small"
    check_box  = f"embed_{model_name}_enabled"
    api_field = f"embed_{model_name}_api_key"

    at = AppTest.from_file("content/model_config.py", default_timeout=30).run()
    at.checkbox(key=check_box).set_value(True).run()
    at.text_input(key=api_field).set_value("testing").run()
    at.button[0].click().run()
    assert len(at.success) == 1, "Embedding Model Configuration Saved"
    assert at.session_state.embed_model_config[model_name]["enabled"] is True
    assert at.session_state.embed_model_config[model_name]["api_key"] == ("testing")

    # The first run initialises the embed_model_config
    at = AppTest.from_file("content/split_embed.py", default_timeout=30).run()
    at.session_state.embed_model_config[model_name]["enabled"] = True
    at.session_state.embed_model_config[model_name]["api_key"] = "testing"
    # The second run ensures the selectbox has enabled models
    at.run()
    assert at.session_state.db_configured is True
    assert at.session_state.embed_model_config[model_name]["enabled"] is True
    assert at.session_state.embed_model_config[model_name]["url"] == ("http://api.openai.com")
    assert at.session_state.embed_model_config[model_name]["api_key"] == ("testing")
    at.selectbox(key="select_box_embed_model").set_value(model_name).run()
    # There should be no errors
    assert len(at.error) == 0, "get_embedding_model exception"
    assert at.selectbox(key="select_box_distance_metric").label == "Distance Metric:"
    assert at.radio(key="radio_file_source").label == "File Source:"
    at.radio(key="radio_file_source").set_value("Web").run()
    assert at.button(key="button_web_load").disabled is True
    at.text_input(key="text_input_web_url").set_value(test_url).run()
    assert at.button(key="button_web_load").disabled is False
    at.button(key="button_web_load").click().run()

    # Capture error message if failure
    assert len(at.error) == 1, "Web Load, Split, Embed Failed"
