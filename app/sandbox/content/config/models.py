"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes a web interface for model configuration using Streamlit (`st`).

Session States Set:
- ll_model_config: Stores all Language Model Configuration
- embed_model_config: Stores all Embedding Model Configuration

- ll_model_enabled: Stores all Enabled Language Models
- embed_model_enabled: Stores all Enabled Embedding Models
"""

import inspect
import streamlit as st
from streamlit import session_state as state

import sandbox.utils.st_common as st_common
import sandbox.utils.api_call as api_call

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("config.models")


# Set endpoint if server has been established
MODEL_API_ENDPOINT = None
if "server" in state:
    MODEL_API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/models"


###################################
# Functions
###################################
def get_model(model_type: str, enabled: bool = None) -> dict[str, dict]:
    """Get a dictionary of either all Language/Embed Models or only enabled ones."""

    state_key = f"{model_type}_model_config"
    params = {"model_type": model_type}
    logger.debug("Processing state: %s (%s):", state_key, params)

    if enabled is not None:
        state_key = f"{model_type}_model_enabled"
        params["enabled"] = enabled

    if state_key not in state or state[state_key] == {}:
        try:
            response = api_call.get(url=MODEL_API_ENDPOINT, params=params)["data"]
            state[state_key] = {item["name"]: {k: v for k, v in item.items() if k != "name"} for item in response}
            logger.info("State created: state['%s']", state_key)
        except api_call.ApiError as ex:
            st.error(f"Unable to retrieve models: {ex}", icon="🚨")
            state[state_key] = {}


def patch_model(model_type: str) -> None:
    """Update Model Configuration for either Language Models or Embed Models"""
    state_key = f"{model_type}_model_config"

    model_changes = 0
    for model_name, _ in state[state_key].items():
        if (
            state[state_key][model_name]["enabled"] != state[f"{model_type}_{model_name}_enabled"]
            or state[state_key][model_name]["url"] != state[f"{model_type}_{model_name}_url"]
            or state[state_key][model_name]["api_key"] != state[f"{model_type}_{model_name}_api_key"]
        ):
            model_changes += 1
            try:
                api_call.patch(
                    url=MODEL_API_ENDPOINT + "/" + model_name,
                    body={
                        "enabled": state[f"{model_type}_{model_name}_enabled"],
                        "url": state[f"{model_type}_{model_name}_url"],
                        "api_key": state[f"{model_type}_{model_name}_api_key"],
                    },
                )
                # Success
                st.success(f"{model_name} Model Configuration - Updated", icon="✅")
                st_common.clear_state_key(f"{model_type}_{model_name}_enabled")
                st_common.clear_state_key(f"{model_type}_{model_name}_url")
                st_common.clear_state_key(f"{model_type}_{model_name}_api_key")
            except api_call.ApiError as ex:
                st.error(f"Unable to perform update: {ex}", icon="🚨")
                break

    if model_changes == 0:
        st.info("Model Configuration - No Changes Detected.", icon="ℹ️")
    else:
        st_common.clear_state_key(state_key)
        get_model(model_type)


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

    st.header("Models")
    st.write("Update model configuration parameters.")

    st.subheader("Language Models")
    get_model(model_type="ll")
    with st.form("update_ll_model_config"):
        # Create table header
        table2_col_format = st.columns([0.08, 0.3, 0.2, 0.2, 0.2])
        col1_2, col2_2, col3_2, col4_2, col5_2 = table2_col_format
        col1_2.markdown("**<u>Enabled</u>**", unsafe_allow_html=True)
        col2_2.markdown("**<u>Model Name</u>**", unsafe_allow_html=True)
        col3_2.markdown("**<u>API</u>**", unsafe_allow_html=True)
        col4_2.markdown("**<u>API Server</u>**", unsafe_allow_html=True)
        col5_2.markdown("**<u>API Key</u>**", unsafe_allow_html=True)

        # Create table rows
        for model_name, config in state.ll_model_config.items():
            col1_2, col2_2, col3_2, col4_2, col5_2 = table2_col_format
            col1_2.checkbox(
                "Enabled",
                value=config["enabled"],
                label_visibility="collapsed",
                key=f"ll_{model_name}_enabled",
                disabled=False,
            )
            col2_2.text_input(
                "Model",
                value=model_name,
                label_visibility="collapsed",
                key=f"ll_{model_name}",
                disabled=True,
            )
            col3_2.text_input(
                "API",
                value=config["api"],
                label_visibility="collapsed",
                key=f"ll_{model_name}_api",
                disabled=True,
            )
            col4_2.text_input(
                "Server",
                value=config["url"],
                key=f"ll_{model_name}_url",
                label_visibility="collapsed",
            )
            col5_2.text_input(
                "Key",
                value=str(config["api_key"]),
                key=f"ll_{model_name}_api_key",
                type="password",
                label_visibility="collapsed",
            )
        update_ll_model = st.form_submit_button(label="Save")
        if update_ll_model:
            patch_model("ll")

    st.subheader("Embedding Models")
    get_model(model_type="embed")
    with st.form("update_embed_model_config"):
        # Create table header
        table1_col_format = st.columns([0.08, 0.3, 0.2, 0.2, 0.2])
        col1_1, col2_1, col3_1, col4_1, col5_1 = table1_col_format
        col1_1.markdown("**<u>Enabled</u>**", unsafe_allow_html=True)
        col2_1.markdown("**<u>Model Name</u>**", unsafe_allow_html=True)
        col3_1.markdown("**<u>API</u>**", unsafe_allow_html=True)
        col4_1.markdown("**<u>API Server</u>**", unsafe_allow_html=True)
        col5_1.markdown("**<u>API Key</u>**", unsafe_allow_html=True)

        # Create table rows
        for model_name, config in state.embed_model_config.items():
            col1_1, col2_1, col3_1, col4_1, col5_1 = table1_col_format
            col1_1.checkbox(
                "Enabled",
                value=config["enabled"],
                label_visibility="collapsed",
                key=f"embed_{model_name}_enabled",
                disabled=False,
            )
            col2_1.text_input(
                "Model",
                value=model_name,
                label_visibility="collapsed",
                key=f"embed_{model_name}",
                disabled=True,
            )
            col3_1.text_input(
                "API",
                value=config["api"],
                label_visibility="collapsed",
                key=f"embed_{model_name}_api",
                disabled=True,
            )
            col4_1.text_input(
                "Server",
                value=config["url"],
                key=f"embed_{model_name}_url",
                label_visibility="collapsed",
            )
            col5_1.text_input(
                "Key",
                value=str(config["api_key"]),
                key=f"embed_{model_name}_api_key",
                type="password",
                label_visibility="collapsed",
            )
        update_embed_model = st.form_submit_button(label="Save")
        if update_embed_model:
            patch_model("embed")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
