"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes is used for the splitting and chunking process using Streamlit (`st`).
"""
# spell-checker:ignore selectbox, hnsw, ivf, ocids,iterrows

import inspect
import math
import re

import pandas as pd

import streamlit as st
from streamlit import session_state as state

from sandbox.content.config.oci import get_oci
from sandbox.content.config.models import get_model
import sandbox.utils.api_call as api_call
import sandbox.utils.st_common as st_common
from common.schema import DistanceMetrics, IndexTypes, DatabaseVectorStorage
import common.functions
import common.help_text as help_text
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("config.tools.split_embed")

# Set endpoint if server has been established
OCI_API_ENDPOINT = None
EMBED_API_ENDPOINT = None
if "server" in state:
    OCI_API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/oci"
    EMBED_API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/embed"


#####################################################
# Functions
#####################################################
@st.cache_data
def get_compartments() -> dict:
    """Get OCI Compartments; function for Streamlit caching"""
    api_url = f"{OCI_API_ENDPOINT}/compartments/{state.user_settings['oci_profile']}"
    response = api_call.get(url=api_url)
    return response


@st.cache_data
def get_buckets(compartment: str) -> list:
    """Get OCI Buckets in selected compartment; function for Streamlit caching"""
    api_url = f"{OCI_API_ENDPOINT}/buckets/{compartment}/{state.user_settings['oci_profile']}"
    response = api_call.get(url=api_url)
    return response


@st.cache_data
def get_bucket_objects(bucket: str) -> list:
    """Get OCI Buckets in selected compartment; function for Streamlit caching"""
    api_url = f"{OCI_API_ENDPOINT}/objects/{bucket}/{state.user_settings['oci_profile']}"
    response = api_call.get(url=api_url)
    return response


@st.cache_resource
def files_data_frame(objects, process=False):
    """Produce a data frame of files"""
    files = pd.DataFrame({"File": [], "Process": []})
    if len(objects) >= 1:
        files = pd.DataFrame(
            {"File": [objects[0]], "Process": [process]},
        )
        for file in objects[1:]:
            new_record = pd.DataFrame([{"File": file, "Process": process}])
            files = pd.concat([files, new_record], ignore_index=True)
    return files


def files_data_editor(files, key):
    """Edit data frame"""
    return st.data_editor(
        files,
        key=key,
        use_container_width=True,
        column_config={
            "to process": st.column_config.CheckboxColumn(
                "in",
                help="Select files **to include** into loading process",
                default=False,
            )
        },
        disabled=["File"],
        hide_index=True,
    )


def update_chunk_overlap_slider() -> None:
    """Keep text and slider input aligned"""
    state.selected_chunk_overlap_slider = state.selected_chunk_overlap_input


def update_chunk_overlap_input() -> None:
    """Keep text and slider input aligned"""
    state.selected_chunk_overlap_input = state.selected_chunk_overlap_slider


def update_chunk_size_slider() -> None:
    """Keep text and slider input aligned"""
    state.selected_chunk_size_slider = state.selected_chunk_size_input


def update_chunk_size_input() -> None:
    """Keep text and slider input aligned"""
    state.selected_chunk_size_input = state.selected_chunk_size_slider


#############################################################################
# MAIN
#############################################################################
def main() -> None:
    """Streamlit GUI"""
    db_avail = st_common.is_db_configured()
    if not db_avail:
        logger.debug("Embedding Disabled (Database not configured)")
        st.warning("Database is not configured. Disabling Embedding.", icon="⚠️")

    get_model(model_type="embed", only_enabled=True)
    available_embed_models = list(state.embed_model_enabled.keys())
    if not available_embed_models:
        logger.debug("Embedding Disabled (no Embedding Models)")
        st.warning("No embedding models are configured and/or enabled. Disabling Embedding.", icon="⚠️")

    if not db_avail or not available_embed_models:
        st.stop()

    file_sources = ["OCI", "Local", "Web"]
    get_oci()
    if not state.oci_config[state.user_settings["oci_profile"]]["namespace"]:
        st.warning("OCI is not configured, some functionality is disabled", icon="⚠️")
        file_sources.remove("OCI")

    # Initialize our embedding request
    embed_request = DatabaseVectorStorage()
    #############################################################################
    # GUI
    #############################################################################
    st.header("Embedding Configuration", divider="red")
    embed_request.model = st.selectbox(
        "Embedding models available: ",
        options=available_embed_models,
        index=0,
        key="selected_embed_model",
    )
    embed_url = state.embed_model_enabled[embed_request.model]["url"]
    st.write(f"Embedding Server: {embed_url}")
    is_embed_accessible, embed_err_msg = common.functions.is_url_accessible(embed_url)
    if not is_embed_accessible:
        st.warning(embed_err_msg, icon="⚠️")
        if st.button("Retry"):
            st.rerun()
        st.stop()

    chunk_size_max = state.embed_model_enabled[embed_request.model]["max_chunk_size"]
    col1_1, col1_2 = st.columns([0.8, 0.2])
    with col1_1:
        st.slider(
            "Chunk Size (tokens):",
            min_value=0,
            max_value=chunk_size_max,
            value=chunk_size_max,
            step=1,
            key="selected_chunk_size_slider",
            on_change=update_chunk_size_input,
            help=help_text.help_dict["chunk_size"],
        )
        st.slider(
            "Chunk Overlap (% of Chunk Size)",
            min_value=0,
            max_value=100,
            value=20,
            step=5,
            key="selected_chunk_overlap_slider",
            on_change=update_chunk_overlap_input,
            format="%d%%",
            help=help_text.help_dict["chunk_overlap"],
        )

    with col1_2:
        embed_request.chunk_size = st.number_input(
            "Chunk Size (tokens):",
            label_visibility="hidden",
            min_value=0,
            max_value=chunk_size_max,
            value=chunk_size_max,
            step=1,
            key="selected_chunk_size_input",
            on_change=update_chunk_size_slider,
        )
        chunk_overlap_pct = st.number_input(
            "Chunk Overlap (% of Chunk Size):",
            label_visibility="hidden",
            min_value=0,
            max_value=100,
            value=20,
            step=5,
            key="selected_chunk_overlap_input",
            on_change=update_chunk_overlap_slider,
        )
        embed_request.chunk_overlap = math.ceil((chunk_overlap_pct / 100) * embed_request.chunk_size)

    col2_1, col2_2 = st.columns([0.5, 0.5])
    embed_request.distance_metric = col2_1.selectbox(
        "Distance Metric:",
        list(DistanceMetrics.__args__),
        key="selected_distance_metric",
        help=help_text.help_dict["distance_metric"],
    )
    embed_request.index_type = col2_2.selectbox(
        "Index Type:", list(IndexTypes.__args__), key="selected_index_type", help=help_text.help_dict["index_type"]
    )
    # Create a text input widget
    embed_alias_size, _ = st.columns([0.5, 0.5])
    embed_request.alias = embed_alias_size.text_input(
        "Embedding Alias:",
        max_chars=20,
        help=help_text.help_dict["embed_alias"],
        key="selected_embed_alias",
        placeholder="Optional; press Enter to set.",
    )
    # Define the regex pattern: starts with a letter, followed by alphanumeric characters or underscores
    pattern = r"^[A-Za-z][A-Za-z0-9_]*$"
    # Check if input is valid
    if embed_request.alias and not re.match(pattern, embed_request.alias):
        st.error(
            "Invalid Alias! It must start with a letter and only contain alphanumeric characters and underscores."
        )
    embed_request.vector_store, _ = common.functions.get_vs_table(
        **embed_request.model_dump(exclude={"database", "vector_store"})
    )

    ################################################
    # Splitting
    ################################################
    st.header("Load and Split Documents", divider="red")
    file_source = st.radio("File Source:", file_sources, key="radio_file_source", horizontal=True)
    populate_button_disabled = True
    button_help = None

    ######################################
    # Local Source
    ######################################
    if file_source == "Local":
        button_help = """
            This button is disabled if no local files have been provided.
        """
        st.subheader("Local Files", divider=False)
        embed_files = st.file_uploader(
            "Choose a file:",
            key="local_file_uploader",
            help="Large or many files?  Consider OCI Object Storage or invoking the API directly.",
            accept_multiple_files=True,
        )
        populate_button_disabled = len(embed_files) == 0

    ######################################
    # Web Source
    ######################################
    if file_source == "Web":
        button_help = """
            This button is disabled if there the URL was unable to be validated.  Please check the URL.
        """
        st.subheader("Web Pages", divider=False)
        web_url = st.text_input("URL:", key="selected_web_url")
        is_web_accessible, _ = common.functions.is_url_accessible(web_url)
        populate_button_disabled = not (web_url and is_web_accessible)

    ######################################
    # OCI Source
    ######################################
    if file_source == "OCI":
        button_help = """
            This button is disabled if there are no documents from the source bucket split with
            the current split and embed options.  Please Split and Embed to enable Vector Storage.
        """
        st.text(f"OCI namespace: {state.oci_config[state.user_settings['oci_profile']]['namespace']}")
        oci_compartments = get_compartments()["data"]
        src_bucket_list = []
        col2_1, col2_2 = st.columns([0.5, 0.5])
        with col2_1:
            bucket_compartment = st.selectbox(
                "Bucket compartment:",
                list(oci_compartments.keys()),
                index=None,
                placeholder="Select bucket compartment...",
            )
            if bucket_compartment:
                src_bucket_list = get_buckets(oci_compartments[bucket_compartment])["data"]
        with col2_2:
            src_bucket = st.selectbox(
                "Source bucket:",
                src_bucket_list,
                index=None,
                placeholder="Select source bucket...",
                disabled=not bucket_compartment,
            )
        src_files = []
        if src_bucket:
            src_objects = get_bucket_objects(src_bucket)["data"]
            src_files = files_data_frame(src_objects)
        else:
            src_files = pd.DataFrame({"File": [], "Process": []})

        src_files_selected = files_data_editor(src_files, "source")
        populate_button_disabled = src_files_selected["Process"].sum() == 0

    ######################################
    # Populate Vector Store
    ######################################
    st.header("Populate Vector Store", divider="red")
    st.markdown(f"##### **Vector Store:** `{embed_request.vector_store}`")
    if not populate_button_disabled:
        if "button_populate" in state and state.button_populate is True:
            state.running = True
        else:
            state.running = False
    else:
        state.running = True

    rate_size, _ = st.columns([0.28, 0.72])
    rate_limit = rate_size.number_input(
        "Rate Limit (RPM):",
        value=None,
        help="Leave blank for no rate-limiting - Requests Per Minute",
        step=1,
        max_value=60,
        key="selected_rate_limit",
    )
    if st.button(
        "Populate Vector Store",
        type="primary",
        key="button_populate",
        disabled=state.running,
        help=button_help,
    ):
        try:
            placeholder = st.empty()
            with placeholder:
                st.warning("Populating Vector Store... please be patient.", icon="⚠️")

            api_url = None
            api_params = {"client": state.user_settings["client"]}
            api_payload = []
            # Place files on Server for Embedding
            if file_source == "Local":
                api_url = f"{EMBED_API_ENDPOINT}/local/store"
                seen_file = set()
                files = [
                    ("files", (file.name, file.getvalue(), file.type))
                    for file in state["local_file_uploader"]
                    if file.name not in seen_file and not seen_file.add(file.name)
                ]
                api_payload = {"files": files}

            if file_source == "Web":
                api_url = f"{EMBED_API_ENDPOINT}/web/store"
                api_payload = {"json": [web_url]}

            if file_source == "OCI":
                # Download OCI Objects for Processing
                api_url = f"{OCI_API_ENDPOINT}/objects/download/{src_bucket}/{state.user_settings['oci_profile']}"
                process_list = src_files_selected[src_files_selected["Process"]].reset_index(drop=True)
                api_payload = {"json": process_list["File"].tolist()}

            # Post Files to Server
            response = api_call.post(url=api_url, params=api_params, payload=api_payload)

            # All files are now on Server... Run Embeddings
            embed_params = {"client": state.user_settings["client"], "rate_limit": rate_limit}
            response = api_call.post(
                url=EMBED_API_ENDPOINT,
                params=embed_params,
                payload={"json": embed_request.model_dump()},
                timeout=300,
            )
            placeholder.empty()
            st.success(f"Vector Store Populated: {response['msg']}", icon="✅")
            # Delete database_config state to reflect new vector stores
            st_common.clear_state_key("database_config")
        except api_call.ApiError as ex:
            placeholder.empty()
            st.error(ex, icon="🚨")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
