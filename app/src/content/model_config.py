"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes a web interface for model configuration using Streamlit (`st`).
"""

import inspect

import modules.logging_config as logging_config
import modules.metadata as metadata

import streamlit as st
from streamlit import session_state as state

# Distance Metrics
from langchain_community.vectorstores.utils import DistanceStrategy

logger = logging_config.logging.getLogger("model_config")


def initialise_streamlit():
    """Initialise Streamlit Session State"""
    ## Embedding Model
    if "embed_model_config" not in state:
        state.embed_model_config = metadata.embedding_models()
        logger.info("Initialised Embedding Model Config")

    ## Chat Model
    if "lm_model_config" not in state:
        state.lm_model_config = metadata.lm_models()
        state.lm_model = list(state.lm_model_config.keys())[0]
        logger.info("Initialised Language Model Config")

    ## Distance Metrics
    if "distance_metric_config" not in state:
        state.distance_metric_config = {
            "COSINE": [DistanceStrategy.COSINE],
            "EUCLIDEAN_DISTANCE": [DistanceStrategy.DOT_PRODUCT],
            "DOT_PRODUCT": [DistanceStrategy.EUCLIDEAN_DISTANCE],
            "JACCARD": [DistanceStrategy.JACCARD],
            "MAX_INNER_PRODUCT": [DistanceStrategy.MAX_INNER_PRODUCT],
        }
        logger.info("Initialised Distance Metric Config")


def get_class_name(class_ref):
    """Get the class name of the Language Model"""
    # Returns the name of the class
    return class_ref.__name__


def update_embed_model_config():
    """Update Embed Model Configuration"""
    for model_name, _ in state.embed_model_config.items():
        state.embed_model_config[model_name]["enabled"] = state[f"embed_{model_name}_enabled"]
        state.embed_model_config[model_name]["url"] = state[f"embed_{model_name}_api_server"]
        state.embed_model_config[model_name]["api_key"] = state[f"embed_{model_name}_api_key"]
    st.success("Embedding Model Configuration - Updated", icon="✅")


def update_lm_model_config():
    """Update Language Model Configuration"""
    for model_name, _ in state.lm_model_config.items():
        state.lm_model_config[model_name]["enabled"] = state[f"lm_{model_name}_enabled"]
        state.lm_model_config[model_name]["url"] = state[f"lm_{model_name}_api_server"]
        state.lm_model_config[model_name]["api_key"] = state[f"lm_{model_name}_api_key"]
    # Re-init the chatbot
    state.pop("initialised", None)
    st.success("Language Model Configuration - Updated", icon="✅")


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    initialise_streamlit()
    st.header("Embedding Models")
    
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
                value=get_class_name(config["api"]),
                label_visibility="collapsed",
                key=f"embed_{model_name}_api",
                disabled=True,
            )
            col4_1.text_input(
                "Server",
                value=config["url"],
                key=f"embed_{model_name}_api_server",
                label_visibility="collapsed",
            )
            col5_1.text_input(
                "Key",
                value=str(config["api_key"]),
                key=f"embed_{model_name}_api_key",
                type="password",
                label_visibility="collapsed",
            )
        st.form_submit_button(label="Save", on_click=update_embed_model_config)

    st.header("Language Models")
    with st.form("update_lm_model_config"):
        # Create table header
        table2_col_format = st.columns([0.08, 0.3, 0.2, 0.2, 0.2])
        col1_2, col2_2, col3_2, col4_2, col5_2 = table2_col_format
        col1_2.markdown("**<u>Enabled</u>**", unsafe_allow_html=True)
        col2_2.markdown("**<u>Model Name</u>**", unsafe_allow_html=True)
        col3_2.markdown("**<u>API</u>**", unsafe_allow_html=True)
        col4_2.markdown("**<u>API Server</u>**", unsafe_allow_html=True)
        col5_2.markdown("**<u>API Key</u>**", unsafe_allow_html=True)

        # Create table rows
        for model_name, config in state.lm_model_config.items():
            col1_2, col2_2, col3_2, col4_2, col5_2 = table2_col_format
            col1_2.checkbox(
                "Enabled",
                value=config["enabled"],
                label_visibility="collapsed",
                key=f"lm_{model_name}_enabled",
                disabled=False,               
            )
            col2_2.text_input(
                "Model",
                value=model_name,
                label_visibility="collapsed",
                key=f"lm_{model_name}",
                disabled=True,
            )
            col3_2.text_input(
                "API",
                value=config["api"],
                label_visibility="collapsed",
                key=f"lm_{model_name}_api",
                disabled=True,
            )
            col4_2.text_input(
                "Server",
                value=config["url"],
                key=f"lm_{model_name}_api_server",
                label_visibility="collapsed",
            )
            col5_2.text_input(
                "Key",
                value=str(config["api_key"]),
                key=f"lm_{model_name}_api_key",
                type="password",
                label_visibility="collapsed",
            )
        st.form_submit_button(label="Save", on_click=update_lm_model_config)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
