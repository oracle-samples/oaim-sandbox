"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, selectbox, mult, iloc

import pandas as pd

import streamlit as st
from streamlit import session_state as state
import common.help_text as help_text
from common.functions import client_gen_id

from sandbox.content.config.models import get_model
from sandbox.content.config.database import get_databases

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.utils.st_common")


#############################################################################
# Helpers
#############################################################################
def clear_state_key(state_key: str) -> None:
    state.pop(state_key, None)
    logger.debug("State cleared: %s", state_key)


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
        state.user_settings["client"] = client_gen_id()
        clear_state_key("sandbox_client")


#####################################################
# Large Language Options
#####################################################
def ll_sidebar() -> None:
    """Language Model Sidebar"""
    st.sidebar.subheader("Language Model Parameters", divider="red")
    get_model(model_type="ll", enabled=True)
    available_ll_models = list(state.ll_model_enabled.keys())
    if not available_ll_models:
        st.error("No language models are configured and/or enabled. Disabling Sandbox.", icon="❌")
        state.enable_sandbox = False

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
        help=help_text.help_dict["temperature"],
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
        help=help_text.help_dict["max_completion_tokens"],
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
        help=help_text.help_dict["top_p"],
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
        help=help_text.help_dict["frequency_penalty"],
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
        help=help_text.help_dict["presence_penalty"],
        value=state.user_settings["ll_model"]["presence_penalty"],
        min_value=-2.0,
        max_value=2.0,
        key="selected_ll_model_presence_penalty",
        on_change=update_user_settings_state,
        args=("ll_model", "presence_penalty"),
    )


#####################################################
# RAG Options
#####################################################
def rag_sidebar() -> None:
    st.sidebar.subheader("Retrieval Augmented Generation", divider="red")
    get_model(model_type="embed", enabled=True)
    available_embed_models = list(state.embed_model_enabled.keys())
    if not available_embed_models:
        logger.debug("RAG Disabled (no Embedding Models)")
        st.warning("No embedding models are configured and/or enabled. Disabling RAG.", icon="⚠️")
        db_avail = False
    else:
        get_databases()
        db_avail = state.database_config[state.user_settings["rag"]["database"]].get("connected")

    if not db_avail:
        logger.debug("RAG Disabled (Database not configured)")
        st.warning("Database is not configured. Disabling RAG.", icon="⚠️")
        update_user_settings_state("rag", "rag_enabled", False)
    elif not state.database_config[state.user_settings["rag"]["database"]].get("vector_stores"):
        logger.debug("RAG Disabled (Database has no vector stores.)")
        st.warning("Database has no Vector Stores. Disabling RAG.", icon="⚠️")
        update_user_settings_state("rag", "rag_enabled", False)

    rag_enabled = st.sidebar.checkbox(
        "Enable RAG?",
        help=help_text.help_dict["rag"],
        value=state.user_settings["rag"]["rag_enabled"],
        disabled=not db_avail,
        key="selected_rag_rag_enabled",
        on_change=update_user_settings_state,
        args=("rag", "rag_enabled"),
    )

    if rag_enabled:
        ##########################
        # Search
        ##########################
        # TODO(gotsysdba) "Similarity Score Threshold" currently raises NotImplementedError
        # rag_search_type_list =
        # ["Similarity", "Similarity Score Threshold", "Maximal Marginal Relevance"]
        rag_search_type_list = ["Similarity", "Maximal Marginal Relevance"]
        rag_search_type = st.sidebar.selectbox(
            "Search Type:",
            rag_search_type_list,
            index=rag_search_type_list.index(state.user_settings["rag"]["search_type"]),
            key="selected_rag_search_type",
            on_change=update_user_settings_state,
            args=("rag", "search_type"),
        )
        st.sidebar.number_input(
            "Top K:",
            help=help_text.help_dict["top_k"],
            value=state.user_settings["rag"]["top_k"],
            min_value=1,
            max_value=10000,
            step=1,
            key="selected_rag_top_k",
            on_change=update_user_settings_state,
            args=("rag", "top_k"),
        )
        if rag_search_type == "Similarity Score Threshold":
            st.sidebar.slider(
                "Minimum Relevance Threshold:",
                help=help_text.help_dict["score_threshold"],
                value=state.user_settings["rag"]["score_threshold"],
                min_value=0.0,
                max_value=1.0,
                step=0.1,
                on_change=update_user_settings_state,
                args=("rag", "score_threshold"),
            )
        if rag_search_type == "Maximal Marginal Relevance":
            st.sidebar.number_input(
                "Fetch K:",
                help=help_text.help_dict["fetch_k"],
                value=state.user_settings["rag"]["fetch_k"],
                min_value=1,
                max_value=10000,
                step=1,
                key="selected_rag_fetch_k",
                on_change=update_user_settings_state,
                args=("rag", "fetch_k"),
            )
            st.sidebar.slider(
                "Degree of Diversity:",
                help=help_text.help_dict["lambda_mult"],
                value=state.user_settings["rag"]["lambda_mult"],
                min_value=0.0,
                max_value=1.0,
                step=0.1,
                key="selected_rag_lambda_mult",
                on_change=update_user_settings_state,
                args=("rag", "lambda_mult"),
            )

        ##########################
        # Vector Store
        ##########################
        st.sidebar.subheader("Vector Store", divider="red")
        # Create a DataFrame of all database vector storage tables
        vs_df = pd.DataFrame(state.database_config[state.user_settings["rag"]["database"]].get("vector_stores"))

        def vs_reset() -> None:
            # Reset Vector Store Selections
            for key in state["user_settings"]["rag"]:
                if key in ("model", "chunk_size", "chunk_overlap", "distance_metric", "vector_store", "alias"):
                    clear_state_key(f"selected_rag_{key}")
                    update_user_settings_state("rag", key)

        # Function to handle selectbox with auto-setting for a single unique value
        def vs_gen_selectbox(label, options, key):
            valid_options = [option for option in options if option != ""]
            if not valid_options:  # Disable the selectbox if no valid options are available
                disabled = True
                selected_value = ""
            else:
                disabled = False
                if len(valid_options) == 1:  # Pre-select if only one unique option
                    selected_value = valid_options[0]
                else:
                    selected_value = state["user_settings"]["rag"][key.removeprefix("selected_rag_")] or ""

            return st.sidebar.selectbox(
                label,
                options=[""] + valid_options,
                key=key,
                index=([""] + valid_options).index(selected_value),
                disabled=disabled,
            )

        # Dynamically update filtered_df based on selected filters
        def update_filtered_df():
            filtered = vs_df.copy()
            if st.session_state.get("selected_rag_alias"):
                filtered = filtered[filtered["alias"] == st.session_state["selected_rag_alias"]]
            if st.session_state.get("selected_rag_model"):
                filtered = filtered[filtered["model"] == st.session_state["selected_rag_model"]]
            if st.session_state.get("selected_rag_chunk_size"):
                filtered = filtered[filtered["chunk_size"] == st.session_state["selected_rag_chunk_size"]]
            if st.session_state.get("selected_rag_chunk_overlap"):
                filtered = filtered[filtered["chunk_overlap"] == st.session_state["selected_rag_chunk_overlap"]]
            if st.session_state.get("selected_rag_distance_metric"):
                filtered = filtered[filtered["distance_metric"] == st.session_state["selected_rag_distance_metric"]]
            return filtered

        # Initialize filtered options
        filtered_df = update_filtered_df()

        # Render selectbox with updated options
        alias = vs_gen_selectbox("Select Alias:", filtered_df["alias"].unique().tolist(), "selected_rag_alias")
        embed_model = vs_gen_selectbox("Select Model:", filtered_df["model"].unique().tolist(), "selected_rag_model")
        chunk_size = vs_gen_selectbox(
            "Select Chunk Size:", filtered_df["chunk_size"].unique().tolist(), "selected_rag_chunk_size"
        )
        chunk_overlap = vs_gen_selectbox(
            "Select Chunk Overlap:", filtered_df["chunk_overlap"].unique().tolist(), "selected_rag_chunk_overlap"
        )
        distance_metric = vs_gen_selectbox(
            "Select Distance Metric:", filtered_df["distance_metric"].unique().tolist(), "selected_rag_distance_metric"
        )

        if all([embed_model, chunk_size, chunk_overlap, distance_metric]):
            vs = filtered_df["vector_store"].iloc[0]
            update_user_settings_state("rag", "vector_store", vs)
            update_user_settings_state("rag", "alias", alias)
            update_user_settings_state("rag", "model", embed_model)
            update_user_settings_state("rag", "chunk_size", chunk_size)
            update_user_settings_state("rag", "chunk_overlap", chunk_overlap)
            update_user_settings_state("rag", "distance_metric", distance_metric)
        else:
            st.error("Please select Embedding options or disable RAG to continue.", icon="❌")
            state.enable_sandbox = False

        # Reset button
        st.sidebar.button("Reset", type="primary", on_click=vs_reset)