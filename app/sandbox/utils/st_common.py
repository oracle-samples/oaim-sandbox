"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, selectbox

import streamlit as st
from streamlit import session_state as state

from sandbox.utils.client import gen_client_id

from sandbox.content.config.models import get_model
from sandbox.content.config.database import get_database

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.utils.st_common")


#############################################################################
# Helpers
#############################################################################
def clear_state_key(state_key: str) -> None:
    state.pop(state_key, None)
    logger.info("State cleared: %s", state_key)


def update_user_settings_state(
    user_setting: str,
    setting_key: str,
    setting_value: str = None,
) -> None:
    """Update user chat parameters"""
    widget_key = f"selected_{user_setting}_{setting_key}"
    widget_value = state.get(widget_key, setting_value)
    logger.info("Updating user_settings['%s']['%s'] to %s", user_setting, setting_key, widget_value)
    state.user_settings[user_setting][setting_key] = widget_value

    # Destroying SandboxClient
    clear_state_key("sandbox_client")


#############################################################################
# Sidebar
#############################################################################
def history_sidebar() -> None:
    """History Sidebar"""
    chat_history_enable = st.sidebar.checkbox(
        "Enable History and Context?",
        value=True,
        key="selected_ll_model_chat_history",
        on_change=update_user_settings_state,
        args=("ll_model", "chat_history"),
    )
    if st.sidebar.button("Clear History", disabled=not chat_history_enable):
        # Establish a new thread
        state.user_settings["client"] = gen_client_id()
        clear_state_key("sandbox_client")
    st.sidebar.divider()


def ll_sidebar() -> None:
    """Language Model Sidebar"""
    get_model(model_type="ll", enabled=True)
    available_ll_models = list(state.ll_model_enabled.keys())
    if not available_ll_models:
        st.error("No language models are configured and/or enabled. Disabling Sandbox.", icon="❌")
        st.stop()

    # If no user_settings defined for , set to the first available_ll_model
    if state.user_settings["ll_model"].get("model") is None:
        default_ll_model = list(state.ll_model_enabled.keys())[0]
        defaults = {
            "model": default_ll_model,
            "temperature": state.ll_model_enabled[default_ll_model]["temperature"],
            "max_completion_tokens": state.ll_model_enabled[default_ll_model]["max_completion_tokens"],
        }
        state.user_settings["ll_model"].update(defaults)

    ll_idx = list(state.ll_model_enabled.keys()).index(state.user_settings["ll_model"]["model"])
    selected_model = st.sidebar.selectbox(
        "Chat model:",
        options=list(state.ll_model_enabled.keys()),
        index=ll_idx,
        key="selected_ll_model_model",
        on_change=update_user_settings_state,
        args=("ll_model", "model"),
    )

    # Temperature
    temperature = state.ll_model_enabled[selected_model]["temperature"]
    user_temperature = state.user_settings["ll_model"]["temperature"]
    st.sidebar.slider(
        f"Temperature (Default: {temperature}):",
        value=user_temperature if user_temperature is not None else temperature,
        min_value=0.0,
        max_value=2.0,
        key="selected_ll_model_temperature",
        on_change=update_user_settings_state,
        args=("ll_model", "temperature"),
    )

    # Completion Tokens
    max_completion_tokens = state.ll_model_enabled[selected_model]["max_completion_tokens"]
    user_completion_tokens = state.user_settings["ll_model"]["max_completion_tokens"]
    st.sidebar.slider(
        f"Maximum Tokens (Default: {max_completion_tokens}):",
        value=(
            user_completion_tokens
            if user_completion_tokens is not None and user_completion_tokens <= max_completion_tokens
            else max_completion_tokens
        ),
        min_value=1,
        max_value=max_completion_tokens,
        key="selected_ll_model_max_completion_tokens",
        on_change=update_user_settings_state,
        args=("ll_model", "max_completion_tokens"),
    )

    # Top P
    st.sidebar.slider(
        "Top P (Default: 1.0):",
        value=state.user_settings["ll_model"]["top_p"],
        min_value=0.0,
        max_value=1.0,
        key="selected_ll_model_top_p",
        on_change=update_user_settings_state,
        args=("ll_model", "top_p"),
    )

    # Frequency Penalty
    st.sidebar.slider(
        "Frequency penalty (Default: 0.0):",
        value=state.user_settings["ll_model"]["frequency_penalty"],
        min_value=-1.0,
        max_value=1.0,
        key="selected_ll_model_frequency_penalty",
        on_change=update_user_settings_state,
        args=("ll_model", "frequency_penalty"),
    )

    # Presence Penalty
    st.sidebar.slider(
        "Presence penalty (Default: 0.0):",
        value=state.user_settings["ll_model"]["presence_penalty"],
        min_value=-2.0,
        max_value=2.0,
        key="selected_ll_model_presence_penalty",
        on_change=update_user_settings_state,
        args=("ll_model", "presence_penalty"),
    )
    st.sidebar.divider()


def rag_sidebar() -> None:
    get_model(model_type="embed", enabled=True)
    available_embed_models = list(state.embed_model_enabled.keys())
    if not available_embed_models:
        logger.debug("RAG Disabled (no Embedding Models)")
        st.warning("No embedding models are configured and/or enabled. Disabling RAG.", icon="⚠️")
        db_status = None
    else:
        get_database()
        db_status = state.database_config[state.user_settings["database"]].get("status")

    if db_status != "ACTIVE":
        logger.debug("RAG Disabled (Database not configured)")
        st.warning("Database is not configured. Disabling RAG.", icon="⚠️")

    rag_enable = st.sidebar.checkbox(
        "Enable RAG?",
        value=db_status == "ACTIVE",
        disabled=db_status != "ACTIVE",
    )

    if rag_enable:
        # Get Vector Storage
        pass
