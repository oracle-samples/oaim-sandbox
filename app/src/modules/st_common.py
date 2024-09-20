"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import json
import copy
import requests

# Streamlit
import streamlit as st
from streamlit import session_state as state

# Utilities
import modules.db_utils as db
import modules.logging_config as logging_config
import modules.metadata as meta
import modules.help as custom_help
import modules.vectorstorage as vectorstorage
import modules.chatbot as chatbot
import modules.chatbot_server as chatbot_server

logger = logging_config.logging.getLogger("modules.st_common")


def clear_initialised():
    """Reset the initialization of the ChatBot"""
    if "user_lm_model" in state:
        state.lm_model = state.user_lm_model
    state.pop("initialised", None)


def set_default_state(key, value):
    """Easy function to set value in state if not exists"""
    if key not in state:
        logger.debug("Setting %s in Session State", key)
        state[key] = value


def is_url_accessible(url):
    """Check that URL is Available"""
    logger.debug("Checking %s is accessible", url)
    try:
        response = requests.get(url, timeout=2)
        logger.info("Checking %s resulted in %s", url, response.status_code)
        # Check if the response status code is 200 (OK) 403 (Forbidden)
        if response.status_code in [200, 403]:
            return True, None
        else:
            err_msg = f"{url} is not accessible. (Status: {response.status_code})"
            logger.warning(err_msg)
            return False, err_msg
    except requests.exceptions.ConnectionError:
        err_msg = f"{url} is not accessible. (Connection Error)"
        logger.warning(err_msg)
        return False, err_msg
    except requests.exceptions.Timeout:
        err_msg = f"{url} is not accessible. (Request Timeout)"
        logger.warning(err_msg)
        return False, err_msg
    except requests.RequestException as ex:
        logger.exception(ex, exc_info=False)
        return False, ex


def update_rag():
    """Update rag_params state"""
    logger.debug("Updating rag_params session state.")
    params_to_set = [
        "search_type",
        "top_k",
        "score_threshold",
        "fetch_k",
        "lambda_mult",
        "rerank",
        "alias",
        "model",
        "chunk_size",
        "chunk_overlap",
        "distance_metric",
    ]
    for param in params_to_set:
        try:
            state.rag_params[param] = getattr(state, f"rag_user_{param}")
        except AttributeError:
            pass


def set_prompt():
    """Switch Prompt Engineering"""
    if state.rag_params["enable"]:
        state.lm_instr_prompt = "RAG Example"
    else:
        state.lm_instr_prompt = "Basic Example"

    if state.lm_instr != state.lm_instr_config[state.lm_instr_prompt]["prompt"]:
        state.lm_instr = state.lm_instr_config[state.lm_instr_prompt]["prompt"]
        st.info(f"Prompt Engineering - {state.lm_instr_prompt} Prompt has been set.")


def reset_rag():
    """Clear RAG values"""
    logger.debug("Resetting RAG Parameters")
    state.rag_user_idx = {}
    state.rag_filter = {}
    params = ["alias", "model", "chunk_size", "chunk_overlap", "distance_metric"]
    for param in params:
        state.pop(f"rag_user_{param}", None)

    try:
        state.rag_params.clear()
        state.rag_params["enable"] = getattr(state, "rag_user_enable", True)
    except AttributeError:
        state.rag_params = {"enable": True}
    state.pop("vs_tables", None)
    state.pop("chat_manager", None)
    clear_initialised()

    # Set the RAG Prompt
    set_prompt()


def initialise_rag():
    """Initialise the RAG LOVs"""
    logger.debug("Initializing RAG")
    try:
        if not state.db_configured:
            st.warning("Database is not configured, RAG functionality is disabled.", icon="⚠️")

        # Look-up Embedding Tables to generate RAG LOVs (don't use function)
        if state.db_configured:
            if "db_conn" not in state or "vs_tables" not in state:
                state.db_conn = db.connect(state.db_config)
                state.vs_tables = json.loads(db.get_vs_tables(state.db_conn))
        else:
            state.vs_tables = {}

        # Extract unique values for each key (if none, disable RAG)
        if not state.vs_tables:
            state.rag_button_disabled = True
            state.rag_params["enable"] = False
        else:
            state.rag_button_disabled = False
            # Iterate over parameters and set values when possible
            params = ["alias", "model", "chunk_size", "chunk_overlap", "distance_metric"]
            for param in params:
                # LOV Filter (stored in rag_filter)
                try:
                    unique_values = state.rag_filter[param]
                except KeyError:
                    unique_values = list({v[param] for v in state.vs_tables.values() if param in v})
                    state.rag_filter[param] = unique_values

                logger.debug("Unique Values for %s: %s (length: %i)", param, unique_values, len(unique_values))
                if len(unique_values) == 1:
                    state.rag_user_idx[param] = 0
                    state.rag_params[param] = unique_values[0]
                    setattr(state, f"rag_user_{param}", unique_values[0])
                else:
                    state.rag_user_idx.setdefault(param, None)
                    state.rag_params.setdefault(param, None)
        set_prompt()
    except AttributeError:
        st.error("Application has not been initialised, please restart.", icon="⛑️")


def initialise_chatbot(lm_model):
    """Initialise the Chatbot"""
    logger.info("Initializing ChatBot using %s; RAG: %s", lm_model, state.rag_params["enable"])
    vectorstore = None
    ## RAG
    if state.rag_params["enable"]:
        try:
            model, api_accessible, err_msg = vectorstorage.get_embedding_model(
                state.rag_params["model"], state.embed_model_config
            )
        except ValueError:
            st.error(
                "Configure the API Key for embedding model %s",
                state.rag_params["model"],
                icon="🚨",
            )
            st.stop()

        if not api_accessible:
            st.warning(f"{err_msg}.  Disable RAG or resolve.", icon="⚠️")
            if st.button("Retry", key="retry_chatbot_api_accessible"):
                st.rerun()
            st.stop()

        # Get the Store Table
        rag_store_table, _ = vectorstorage.get_vs_table(
            state.rag_params["model"],
            state.rag_params["chunk_size"],
            state.rag_params["chunk_overlap"],
            state.rag_params["distance_metric"],
            state.rag_params["alias"],
        )
        # Initialise Retriever
        vectorstore = vectorstorage.init_vs(
            state.db_conn,
            model,
            rag_store_table,
            state.rag_params["distance_metric"],
        )

    # Chatbot
    lm_model_state = state.lm_model_config[lm_model]
    if lm_model_state["api"] == "" or lm_model_state["url"] == "":
        raise ValueError(f"{lm_model} not fully configured")
    url_accessible, err_msg = is_url_accessible(lm_model_state["url"])
    if not url_accessible:
        raise ValueError(f"Unable to access {lm_model}: {err_msg}")
    cmd = chatbot.ChatCmd(
        lm_model,
        lm_model_state,
        vectorstore,
    )
    logger.info("Initialised ChatBot!")
    return cmd


###################################
# Language Model Sidebar
###################################
def lm_sidebar():
    """Language Model Sidebar
    Used in the Chatbot and Testing Framework
    """

    def update_chat_param():
        """Update user chat parameters"""
        for key in [k for k in state.keys() if k.startswith(f"user_{state.user_lm_model}")]:
            state.lm_model_config[state.user_lm_model][key.split("~")[1]][0] = state[key]
        # Discard the chat_mgr
        clear_initialised()

    lm_parameters = meta.lm_parameters()
    st.sidebar.divider()
    enabled_llms = list(key for key, value in state.lm_model_config.items() if value.get("enabled"))
    logger.debug("Enabled LLMs: %s", enabled_llms)
    try:
        llm_idx = enabled_llms.index(state.lm_model)
    except ValueError:
        llm_idx = 0
    lm_model = st.sidebar.selectbox(
        "Chat model:",
        options=enabled_llms,
        index=llm_idx,
        on_change=clear_initialised,
        key="user_lm_model",
    )
    parameters = [
        "temperature",
        "max_tokens",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
    ]
    for param in parameters:
        if param in state.lm_model_config[lm_model]:
            label = lm_parameters[param]["label"]
            default = state.lm_model_config[lm_model][param][1]
            st.sidebar.slider(
                f"{label} (Default: {default}):",
                value=state.lm_model_config[lm_model][param][0],
                min_value=state.lm_model_config[lm_model][param][2],
                max_value=state.lm_model_config[lm_model][param][3],
                help=lm_parameters[param]["desc_en"],
                key=f"user_{lm_model}~{param}",
                on_change=update_chat_param,
            )
    return lm_model


###################################
# RAG Sidebar
###################################
def rag_sidebar():
    """RAG Sidebar"""

    def refresh_rag_filtered():
        """Refresh the RAG LOVs"""
        # Get the current selected values
        user_alias, user_model, user_chunk_size, user_chunk_overlap, user_distance_metric = (
            state.get(f"rag_user_{param}", None)
            for param in ["alias", "model", "chunk_size", "chunk_overlap", "distance_metric"]
        )
        logger.debug(
            "Filtering on - Alias: %s; Model: %s; Chunk Size: %s; Chunk Overlap: %s; Distance Metric: %s",
            user_alias,
            user_model,
            user_chunk_size,
            user_chunk_overlap,
            user_distance_metric,
        )
        # Filter the vector storage table based on selected values
        if user_alias:
            rag_filt_alias = [user_alias]
        else:
            rag_filt_alias = [
                v.get("alias", None)
                for v in state.vs_tables.values()
                if (user_model is None or v["model"] == user_model)
                and (user_chunk_size is None or v["chunk_size"] == user_chunk_size)
                and (user_chunk_overlap is None or v["chunk_overlap"] == user_chunk_overlap)
                and (user_distance_metric is None or v["distance_metric"] == user_distance_metric)
            ]

        if user_model:
            rag_filt_model = [user_model]
        else:
            rag_filt_model = [
                v["model"]
                for v in state.vs_tables.values()
                if (user_alias is None or v.get("alias", None) == user_alias)
                and (user_chunk_size is None or v["chunk_size"] == user_chunk_size)
                and (user_chunk_overlap is None or v["chunk_overlap"] == user_chunk_overlap)
                and (user_distance_metric is None or v["distance_metric"] == user_distance_metric)
            ]

        if user_chunk_size:
            rag_filt_chunk_size = [user_chunk_size]
        else:
            rag_filt_chunk_size = [
                v["chunk_size"]
                for v in state.vs_tables.values()
                if (user_alias is None or v.get("alias", None) == user_alias)
                and (user_model is None or v["model"] == user_model)
                and (user_chunk_overlap is None or v["chunk_overlap"] == user_chunk_overlap)
                and (user_distance_metric is None or v["distance_metric"] == user_distance_metric)
            ]

        if user_chunk_overlap:
            rag_filt_chunk_overlap = [user_chunk_overlap]
        else:
            rag_filt_chunk_overlap = [
                v["chunk_overlap"]
                for v in state.vs_tables.values()
                if (user_alias is None or v.get("alias", None) == user_alias)
                and (user_model is None or v["model"] == user_model)
                and (user_chunk_size is None or v["chunk_size"] == user_chunk_size)
                and (user_distance_metric is None or v["distance_metric"] == user_distance_metric)
            ]

        if user_distance_metric:
            rag_filt_distance_metric = [user_distance_metric]
        else:
            rag_filt_distance_metric = [
                v["distance_metric"]
                for v in state.vs_tables.values()
                if (user_alias is None or v.get("alias", None) == user_alias)
                and (user_model is None or v["model"] == user_model)
                and (user_chunk_size is None or v["chunk_size"] == user_chunk_size)
                and (user_chunk_overlap is None or v["chunk_overlap"] == user_chunk_overlap)
            ]

        # Remove duplicates and sort
        state.rag_filter["alias"] = sorted(set(rag_filt_alias))
        state.rag_filter["model"] = sorted(set(rag_filt_model))
        state.rag_filter["chunk_size"] = sorted(set(rag_filt_chunk_size))
        state.rag_filter["chunk_overlap"] = sorted(set(rag_filt_chunk_overlap))
        state.rag_filter["distance_metric"] = sorted(set(rag_filt_distance_metric))

        # (Re)set the index to previously selected option
        attributes = ["alias", "model", "chunk_size", "chunk_overlap", "distance_metric"]
        for attr in attributes:
            filtered_list = state.rag_filter[attr]
            user_value = getattr(state, f"rag_user_{attr}")
            try:
                idx = 0 if len(filtered_list) == 1 else filtered_list.index(user_value)
            except ValueError:
                idx = None

            state.rag_user_idx[attr] = idx

    st.sidebar.divider()
    st.sidebar.subheader("RAG Embeddings")
    rag_enable = st.sidebar.checkbox(
        "RAG?",
        value=state.rag_params["enable"],
        key="rag_user_enable",
        disabled=state.rag_button_disabled,
        help=custom_help.gui_help["rag"]["english"],
        on_change=reset_rag,
    )

    if rag_enable:
        set_default_state("rag_user_rerank", False)
        st.sidebar.checkbox(
            "Enable Re-Ranking?",
            value=False,
            key="rag_user_rerank",
            help=custom_help.gui_help["rerank"]["english"],
            on_change=update_rag,
            disabled=True,
        )
        # TODO(gotsysdba) "Similarity Score Threshold" currently raises NotImplementedError
        # rag_search_type_list =
        # ["Similarity", "Similarity Score Threshold", "Maximal Marginal Relevance"]
        rag_search_type_list = ["Similarity", "Maximal Marginal Relevance"]
        set_default_state("rag_user_rerank", rag_search_type_list[0])
        rag_search_type = st.sidebar.selectbox(
            "Search Type",
            rag_search_type_list,
            key="rag_user_search_type",
            on_change=update_rag,
        )
        set_default_state("rag_user_top_k", 4)
        st.sidebar.number_input(
            "Top K",
            min_value=1,
            max_value=10000,
            step=1,
            key="rag_user_top_k",
            help=custom_help.gui_help["rag_top_k"]["english"],
            on_change=update_rag,
        )
        if rag_search_type == "Similarity Score Threshold":
            set_default_state("rag_user_score_threshold", 0.0)
            st.sidebar.slider(
                "Minimum Relevance Threshold",
                min_value=0.0,
                max_value=1.0,
                step=0.1,
                key="rag_user_score_threshold",
                on_change=update_rag,
            )
        if rag_search_type == "Maximal Marginal Relevance":
            set_default_state("rag_user_fetch_k", 20)
            st.sidebar.number_input(
                "Fetch K",
                min_value=1,
                max_value=10000,
                step=1,
                key="rag_user_fetch_k",
                help=custom_help.gui_help["rag_fetch_k"]["english"],
                on_change=update_rag,
            )
            set_default_state("rag_user_lambda_mult", 0.5)
            st.sidebar.slider(
                "Degree of Diversity",
                min_value=0.0,
                max_value=1.0,
                step=0.1,
                key="rag_user_lambda_mult",
                help=custom_help.gui_help["rag_lambda_mult"]["english"],
                on_change=update_rag,
            )
        st.sidebar.divider()
        if any(state.rag_filter["alias"]):
            st.sidebar.selectbox(
                "Embedding Alias: ",
                state.rag_filter["alias"],
                index=state.rag_user_idx["alias"],
                key="rag_user_alias",
                placeholder="Choose and option or leave blank.",
                help="""
                If an alias was specified during embedding, you can use it to set the remaining values.
                It can be left blank.
                """,
                on_change=refresh_rag_filtered,
            )
        st.sidebar.selectbox(
            "Embedding Model: ",
            state.rag_filter["model"],
            index=state.rag_user_idx["model"],
            key="rag_user_model",
            on_change=refresh_rag_filtered,
        )
        st.sidebar.selectbox(
            "Chunk Size: ",
            state.rag_filter["chunk_size"],
            index=state.rag_user_idx["chunk_size"],
            key="rag_user_chunk_size",
            on_change=refresh_rag_filtered,
        )
        st.sidebar.selectbox(
            "Chunk Overlap: ",
            state.rag_filter["chunk_overlap"],
            index=state.rag_user_idx["chunk_overlap"],
            key="rag_user_chunk_overlap",
            on_change=refresh_rag_filtered,
        )
        st.sidebar.selectbox(
            "Distance Strategy: ",
            state.rag_filter["distance_metric"],
            index=state.rag_user_idx["distance_metric"],
            key="rag_user_distance_metric",
            on_change=refresh_rag_filtered,
        )

        st.sidebar.button("Reset RAG", type="primary", on_click=reset_rag)
        st.sidebar.divider()
        chatbot_server.sidebar_start_server()


###################################
# Save Settings Sidebar
###################################
def save_settings_sidebar():
    """Sidebar Button to Export Settings"""

    def empty_key(obj):
        """Return a new object with excluded keys set to empty strings"""
        exclude_keys = ["password", "wallet_password", "api", "api_key", "additional_user_agent"]

        if isinstance(obj, dict):
            # Create a new dictionary to hold the modified keys
            new_dict = {}
            for key, value in obj.items():
                if key in exclude_keys:
                    new_dict[key] = ""
                else:
                    # Recursively handle nested dictionaries or lists
                    new_dict[key] = empty_key(value)
            return new_dict

        elif isinstance(obj, list):
            # Create a new list to hold the modified items
            return [empty_key(item) for item in obj]

        # If the object is neither a dict nor a list, return it unchanged
        return obj

    # This is set for inclusion so that exported state is intentional
    include_keys = [
        "embed_model_config",
        "lm_model_config",
        "lm_instr_config",
        "oci_config",
        "db_config",
        "context_instr",
        "lm_model",
        "lm_instr_prompt",
        "rag_params",
    ]
    state_dict = copy.deepcopy(state)
    state_dict_filt = {key: state_dict[key] for key in include_keys if key in state_dict}
    state_dict_filt = empty_key(state_dict_filt)
    session_state_json = json.dumps(state_dict_filt, indent=4)
    st.sidebar.divider()
    st.sidebar.download_button(
        label="Download Settings", data=session_state_json, file_name="sandbox_settings.json", use_container_width=True
    )
