"""
Copyright (c) 2024-2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes a web interface for model configuration using Streamlit (`st`).

Session States Set:
- ll_model_config: Stores all Language Model Configuration
- embed_model_config: Stores all Embedding Model Configuration

- ll_model_enabled: Stores all Enabled Language Models
- embed_model_enabled: Stores all Enabled Embedding Models
"""
# spell-checker:ignore selectbox

import inspect

import time
from typing import Literal
import urllib.parse

import streamlit as st
from streamlit import session_state as state

import sandbox.utils.st_common as st_common
import sandbox.utils.api_call as api_call

import common.help_text as help_text
from common.schema import Model, ModelTypeType, ModelNameType
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.content.config.models")


###################################
# Functions
###################################
def clear_model_state(model_type: ModelTypeType) -> None:
    """Remove model configuration from session state"""
    state_config_key = f"{model_type}_model_config"
    state_enabled_key = f"{model_type}_model_enabled"
    st_common.clear_state_key(state_config_key)
    st_common.clear_state_key(state_enabled_key)
    time.sleep(2)  # So user can see updates
    st.rerun()


def get_model(model_type: ModelTypeType, only_enabled: bool = False, force: bool = False) -> dict[str, dict]:
    """Get a dictionary of either all Language/Embed Models or only enabled ones."""

    state_key = f"{model_type}_model_enabled" if only_enabled else f"{model_type}_model_config"
    if state_key not in state or state[state_key] == {} or force:
        try:
            api_url = f"{state.server['url']}:{state.server['port']}/v1/models"
            api_params = {"only_enabled": only_enabled, "model_type": model_type}
            response = api_call.get(url=api_url, params=api_params)
            state[state_key] = {item["name"]: {k: v for k, v in item.items() if k != "name"} for item in response}
            logger.info("State created: state['%s']", state_key)
        except api_call.ApiError as ex:
            st.error(f"Unable to retrieve models: {ex}", icon="🚨")
            state[state_key] = {}


def create_model(model: Model) -> None:
    """Add either Language Model or Embed Model"""
    api_url = f"{state.server['url']}:{state.server['port']}/v1/models/create"
    api_call.post(url=api_url, params={"name": model.name}, payload={"json": model.model_dump()})


def patch_model(model: Model) -> None:
    """Update Model Configuration for either Language Models or Embed Models"""
    try:
        api_url = f"{state.server['url']}:{state.server['port']}/v1/models/update"
        api_call.patch(url=api_url, params={"name": model.name}, payload={"json": model.model_dump()})
    except api_call.ApiError:
        create_model(model)


def delete_model(model: Model) -> None:
    """Update Model Configuration for either Language Models or Embed Models"""
    api_url = f"{state.server['url']}:{state.server['port']}/v1/models/delete"
    api_call.patch(url=api_url, params={"name": model.name})


@st.dialog("Model Configuration", width="large")
def edit_model(model_type: ModelTypeType, action: Literal["add", "edit"], model_name: ModelNameType = None) -> None:
    """Model Edit Dialog Box"""
    # Initialize our model request
    if action == "edit":
        name = urllib.parse.quote(model_name, safe="")
        request = api_call.get(url=f"{state.server['url']}:{state.server['port']}/v1/models/{name}")
        model = Model.model_validate(request)
    else:
        model = Model(name="unset", type=model_type, api="unset", status="CUSTOM")
    with st.form("edit_model"):
        model.enabled = st.checkbox("Enabled", value=True if action == "add" else model.enabled)
        model.name = st.text_input(
            "Model Name:",
            help=help_text.help_dict["model_name"],
            value=None if model.name == "unset" else model.name,
            key="add_model_name",
            disabled=action == "edit",
        )
        if model_type == "ll":
            api_values = list({models["api"] for models in state.ll_model_config.values()})
        else:
            api_values = list({models["api"] for models in state.embed_model_config.values()})
        api_index = next((i for i, item in enumerate(api_values) if item == model.api), None)
        model.api = st.selectbox(
            "API:",
            help=help_text.help_dict["model_api"],
            placeholder="-- Choose the Model's API --",
            index=api_index,
            options=api_values,
            key="add_model_api",
            disabled=action == "edit",
        )
        model.url = st.text_input(
            "API URL:", help=help_text.help_dict["model_api_url"], key="add_model_api_url", value=model.url
        )
        model.api_key = st.text_input(
            "API Key:",
            help=help_text.help_dict["model_api_key"],
            key="add_model_api_key",
            type="password",
            value=model.api_key,
        )
        if model_type == "ll":
            model.context_length = st.number_input(
                "Context Length:",
                help=help_text.help_dict["context_length"],
                min_value=0,
                key="add_model_context_length",
                value=model.context_length,
            )
            model.temperature = st.number_input(
                "Default Temperature:",
                help=help_text.help_dict["temperature"],
                min_value=0.00,
                max_value=2.00,
                key="add_model_temperature",
                value=model.temperature,
            )
            model.max_completion_tokens = st.number_input(
                "Max Completion Tokens:",
                help=help_text.help_dict["max_completion_tokens"],
                min_value=1,
                key="add_model_max_completion_tokens",
                value=model.max_completion_tokens,
            )
            model.frequency_penalty = st.number_input(
                "Default Frequency Penalty:",
                help=help_text.help_dict["frequency_penalty"],
                min_value=-2.00,
                max_value=2.00,
                value=model.frequency_penalty,
                key="add_model_frequency_penalty",
            )
        else:
            model.max_chunk_size = st.number_input(
                "Max Chunk Size:",
                help=help_text.help_dict["chunk_size"],
                min_value=0,
                key="add_model_max_chunk_size",
                value=model.max_chunk_size,
            )
        button_col_format = st.columns([1.2, 1.4, 1.4, 5])
        action_button, delete_button, cancel_button, _ = button_col_format
        if action == "add" and action_button.form_submit_button(label="Add", type="primary", use_container_width=True):
            create_model(model=model)
            clear_model_state(model_type)
        if action == "edit" and action_button.form_submit_button(
            label="Save", type="primary", use_container_width=True
        ):
            patch_model(model=model)
            clear_model_state(model_type)
        if delete_button.form_submit_button(label="Delete", type="secondary", use_container_width=True):
            delete_model(model=model)
            clear_model_state(model_type)
        if cancel_button.form_submit_button(label="Cancel", type="secondary"):
            st.rerun()


#############################################################################
# MAIN
#############################################################################
def main() -> None:
    """Streamlit GUI"""
    st.html(
        """
        <style>
            div[data-testid="stElementContainer"] .stCheckbox {
                min-height: 2.5em !important;
            }
        </style>
        """,
    )

    st.header("Models", divider="red")
    st.write("Update model configuration parameters.")
    data_col_widths = [0.25, 0.2, 0.28, 0.05, 0.12]

    st.divider()
    st.subheader("Language Models")
    get_model(model_type="ll")
    # Table Headers

    table_col_format = st.columns(data_col_widths, vertical_alignment="center")
    ll_col1, ll_col2, ll_col3, ll_col4, ll_col5 = table_col_format
    ll_col1.markdown("**<u>Model Name</u>**", unsafe_allow_html=True)
    ll_col2.markdown("**<u>API</u>**", unsafe_allow_html=True)
    ll_col3.markdown("**<u>API Server</u>**", unsafe_allow_html=True)
    ll_col4.markdown("&#x200B;", help="Active", unsafe_allow_html=True)
    ll_col5.markdown("&#x200B;")
    for model_name, config in state.ll_model_config.items():
        ll_col1.text_input(
            "Model",
            value=model_name,
            label_visibility="collapsed",
            key=f"ll_{model_name}",
            disabled=True,
        )
        ll_col2.text_input(
            "API",
            value=config["api"],
            label_visibility="collapsed",
            key=f"ll_{model_name}_api",
            disabled=True,
        )
        ll_col3.text_input(
            "Server",
            value=config["url"],
            key=f"ll_{model_name}_url",
            label_visibility="collapsed",
            disabled=True,
        )
        ll_col4.checkbox(
            "Enabled",
            value=config["enabled"],
            key=f"ll_{model_name}_enabled",
            label_visibility="collapsed",
            disabled=True,
        )
        ll_col5.button(
            "Edit",
            key=f"ll_{model_name}_edit",
            on_click=edit_model,
            kwargs=dict(model_type="ll", action="edit", model_name=model_name),
        )
    if st.button(label="Add", type="primary", key="add_ll_model"):
        edit_model(model_type="ll", action="add")

    st.divider()
    st.subheader("Embedding Models")
    get_model(model_type="embed")
    # Create table rows
    table_col_format = st.columns(data_col_widths, vertical_alignment="center")
    embed_col1, embed_col2, embed_col3, embed_col4, embed_col5 = table_col_format
    embed_col1.markdown("**<u>Model Name</u>**", unsafe_allow_html=True)
    embed_col2.markdown("**<u>API</u>**", unsafe_allow_html=True)
    embed_col3.markdown("**<u>API Server</u>**", unsafe_allow_html=True)
    embed_col4.markdown("&#x200B;", help="Active", unsafe_allow_html=True)
    embed_col5.markdown("&#x200B;", unsafe_allow_html=True)
    for model_name, config in state.embed_model_config.items():
        embed_col1.text_input(
            "Model",
            value=model_name,
            label_visibility="collapsed",
            key=f"embed_{model_name}",
            disabled=True,
        )
        embed_col2.text_input(
            "API",
            value=config["api"],
            label_visibility="collapsed",
            key=f"embed_{model_name}_api",
            disabled=True,
        )
        embed_col3.text_input(
            "Server",
            value=config["url"],
            key=f"embed_{model_name}_url",
            label_visibility="collapsed",
            disabled=True,
        )
        embed_col4.checkbox(
            "Enabled",
            value=config["enabled"],
            key=f"embed_{model_name}_enabled",
            label_visibility="collapsed",
            disabled=True,
        )
        embed_col5.button(
            "Edit",
            key=f"embed_{model_name}_edit",
            on_click=edit_model,
            kwargs=dict(model_type="embed", action="edit", model_name=model_name),
        )
    if st.button(label="Add", type="primary", key="add_embed_model"):
        edit_model(model_type="embed", action="add")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
