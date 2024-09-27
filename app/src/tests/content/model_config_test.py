"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# pylint: disable=unused-argument

from streamlit.testing.v1 import AppTest


def test_initialise_streamlit_no_env(unset_api_env):
    """Init without Environment"""
    at = AppTest.from_file("content/model_config.py", default_timeout=30).run()
    assert len(at.session_state.embed_model_config) > 0
    assert len(at.session_state.ll_model_config) > 0
    assert len(at.session_state.distance_metric_config) > 0
    for key, value in at.session_state.ll_model_config.items():
        assert value["api_key"] == "", f"Assertion failed for key '{key}'"
    for key, value in at.session_state.embed_model_config.items():
        assert value["api_key"] == "", f"Assertion failed for key '{key}'"


def test_initialise_streamlit_env(set_api_env):
    """Init with Environment"""
    at = AppTest.from_file("content/model_config.py", default_timeout=30).run()
    assert len(at.session_state.embed_model_config) > 0
    assert len(at.session_state.ll_model_config) > 0
    assert len(at.session_state.distance_metric_config) > 0
    for key, value in at.session_state.ll_model_config.items():
        if value.get("api") == "OpenAI":
            assert value.get("api_key") == "TEST_API_KEY", f"Assertion failed for key '{key}'"
    for key, value in at.session_state.embed_model_config.items():
        if value.get("api").__name__ == "OpenAIEmbeddings":
            assert value.get("api_key") == "TEST_API_KEY", f"Assertion failed for key '{key}'"


def test_main_lm_no_env(unset_api_env):
    """Main without Environment"""
    model_name = "gpt-4o-mini"
    at = AppTest.from_file("content/model_config.py", default_timeout=30).run()
    assert len(at.session_state.embed_model_config) > 0
    assert len(at.session_state.ll_model_config) > 0
    assert len(at.session_state.distance_metric_config) > 0

    assert at.session_state.ll_model_config[model_name]["api_key"] == ""
    at.text_input(key=f"lm_{model_name}_api_key").set_value("NEW_TEST_API_KEY").run()
    at.button[0].click().run()
    assert at.session_state.ll_model_config[model_name]["api_key"] == "NEW_TEST_API_KEY"
    assert at.success[0].icon == "✅", "Language Model Configuration - Updated"


def test_main_lm_env(set_api_env):
    """Main with Environment"""
    model_name = "gpt-4o-mini"
    at = AppTest.from_file("content/model_config.py", default_timeout=30).run()
    assert len(at.session_state.embed_model_config) > 0
    assert len(at.session_state.ll_model_config) > 0
    assert len(at.session_state.distance_metric_config) > 0

    assert at.session_state.ll_model_config[model_name]["api_key"] == "TEST_API_KEY"
    at.text_input(key=f"lm_{model_name}_api_key").set_value("NEW_TEST_API_KEY").run()
    at.button[0].click().run()
    assert at.session_state.ll_model_config[model_name]["api_key"] == "NEW_TEST_API_KEY"
    assert at.success[0].icon == "✅", "Language Model Configuration - Updated"


def test_main_embed_no_env(unset_api_env):
    """Main without Environment"""
    model_name = "text-embedding-3-small"
    at = AppTest.from_file("content/model_config.py", default_timeout=30).run()
    assert len(at.session_state.embed_model_config) > 0
    assert len(at.session_state.ll_model_config) > 0
    assert len(at.session_state.distance_metric_config) > 0

    assert at.session_state.embed_model_config[model_name]["api_key"] == ""
    at.text_input(key=f"embed_{model_name}_api_key").set_value("NEW_TEST_API_KEY").run()
    at.button[1].click().run()
    assert at.session_state.embed_model_config[model_name]["api_key"] == "NEW_TEST_API_KEY"
    assert at.success[0].icon == "✅", "Embedding Model Configuration  - Updated"


def test_main_embed_env(set_api_env):
    """Main with Environment"""
    model_name = "text-embedding-3-small"
    at = AppTest.from_file("content/model_config.py", default_timeout=30).run()
    assert len(at.session_state.embed_model_config) > 0
    assert len(at.session_state.ll_model_config) > 0
    assert len(at.session_state.distance_metric_config) > 0

    assert at.session_state.embed_model_config[model_name]["api_key"] == "TEST_API_KEY"
    at.text_input(key=f"embed_{model_name}_api_key").set_value("NEW_TEST_API_KEY").run()
    at.button[1].click().run()
    assert at.session_state.embed_model_config[model_name]["api_key"] == "NEW_TEST_API_KEY"
    assert at.success[0].icon == "✅", "Embedding Model Configuration  - Updated"
