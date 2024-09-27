"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, vectorstorage, selectbox, docos, iterrows

import math
import tempfile
import inspect
import os
import re
import requests

# Streamlit
import streamlit as st
from streamlit import session_state as state

import pandas as pd

# Configuration
from content.oci_config import initialize_streamlit as oci_initialize_streamlit
from content.db_config import initialize_streamlit as db_initialize_streamlit
from content.model_config import initialize_streamlit as model_initialize

# Modules
import modules.logging_config as logging_config
import modules.split as split
import modules.utilities as utilities
import modules.st_common as st_common

logger = logging_config.logging.getLogger("chunk_embed")


#####################################################
# Functions
#####################################################
@st.cache_data
def get_compartments():
    """Get OCI Compartments; function for Streamlit caching"""
    return utilities.oci_get_compartments(state.oci_config)


@st.cache_data
def get_buckets(compartment):
    return utilities.oci_get_buckets(
        state.oci_config,
        state.oci_namespace,
        compartment,
    )


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


def update_chunk_overlap_slider():
    """Keep text and slider input aligned"""
    state.chunk_overlap_slider = state.chunk_overlap_input


def update_chunk_overlap_input():
    """Keep text and slider input aligned"""
    state.chunk_overlap_input = state.chunk_overlap_slider


def update_chunk_size_slider():
    """Keep text and slider input aligned"""
    state.chunk_size_slider = state.chunk_size_input


def update_chunk_size_input():
    """Keep text and slider input aligned"""
    state.chunk_size_input = state.chunk_size_slider


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    db_initialize_streamlit()
    if not state.db_configured:
        st.error("Database is not configured, all functionality is disabled", icon="🚨")
        st.stop()

    model_initialize()

    file_sources = ["OCI", "Local", "Web"]
    oci_initialize_streamlit()
    if not state.oci_configured:
        st.warning("OCI is not configured, some functionality is disabled", icon="⚠️")
        file_sources.remove("OCI")
    #############################################################################
    # GUI
    #############################################################################
    st.header("Embedding Configuration", divider="rainbow")
    selected_embed_model = st.selectbox(
        "Embedding models available: ",
        options=state.enabled_embed,
        index=0,
        key="select_box_embed_model",
    )
    try:
        model, api_accessible, err_msg = utilities.get_embedding_model(selected_embed_model, state.embed_model_config)
        embed_url = state.embed_model_config[selected_embed_model]["url"]
        st.write(f"Embedding Server: {embed_url}")
    except KeyError:
        st.error(
            "No embedding models are are configured and/or enabled.",
            icon="⚠️",
        )
        st.stop()
    except ValueError:
        st.error(
            f"Configure the API Key for embedding model {selected_embed_model}.",
            icon="🚨",
        )
        st.stop()

    # Check access to embedding server
    if not api_accessible:
        st.warning(err_msg, icon="⚠️")
        if st.button("Retry"):
            st.rerun()
        st.stop()

    chunk_size_max = state.embed_model_config[selected_embed_model]["chunk_max"]
    col1_1, col1_2 = st.columns([0.8, 0.2])
    with col1_1:
        st.slider(
            "Chunk Size (tokens):",
            min_value=0,
            max_value=chunk_size_max,
            value=chunk_size_max,
            step=1,
            key="chunk_size_slider",
            on_change=update_chunk_size_input,
            help="Defines the length of each chunk",
        )
        st.slider(
            "Chunk Overlap (% of Chunk Size)",
            min_value=0,
            max_value=100,
            value=20,
            step=5,
            key="chunk_overlap_slider",
            on_change=update_chunk_overlap_input,
            format="%d%%",
            help="Defines the amount of consecutive chunks' overlap as percentage of chunk size",
        )

    with col1_2:
        st.number_input(
            "Chunk Size (tokens):",
            label_visibility="hidden",
            min_value=0,
            max_value=chunk_size_max,
            value=chunk_size_max,
            step=1,
            key="chunk_size_input",
            on_change=update_chunk_size_slider,
        )
        st.number_input(
            "Chunk Overlap (% of Chunk Size):",
            label_visibility="hidden",
            min_value=0,
            max_value=100,
            value=20,
            step=5,
            key="chunk_overlap_input",
            on_change=update_chunk_overlap_slider,
        )

    distance_metric = st.selectbox(
        "Distance Metric:",
        list(state.distance_metric_config.keys()),
        key="select_box_distance_metric",
    )
    # Create a text input widget
    embed_alias = st.text_input(
        "Embedding Alias:",
        max_chars=20,
        help="""
            (Optional) Provide an alias to help identify the embedding during RAG experimentation.
            It must start with a character and only contain alphanumerics and underscores.
            Max Characters: 20
            """,
        key="text_input_embed_alias",
        placeholder="Optional; press Enter to set.",
    )
    # Define the regex pattern: starts with a letter, followed by alphanumeric characters or underscores
    pattern = r"^[A-Za-z][A-Za-z0-9_]*$"
    # Check if input is valid
    if embed_alias and not re.match(pattern, embed_alias):
        st.error(
            "Invalid Alias! It must start with a letter and only contain alphanumeric characters and underscores."
        )

    chunk_overlap_size = math.ceil((state.chunk_overlap_input / 100) * state.chunk_size_input)
    store_table, store_comment = utilities.get_vs_table(
        selected_embed_model, state.chunk_size_input, chunk_overlap_size, distance_metric, embed_alias
    )

    ######################################
    # Splitting
    ######################################
    st.header("Load and Split Documents", divider="rainbow")
    file_source = st.radio("File Source:", file_sources, key="radio_file_source", horizontal=True)
    populate_button_disabled = True

    ######################################
    # Local Source
    ######################################
    if file_source == "Local":
        button_help = """
            This button is disabled if no local files have been provided.
        """
        st.subheader("Local Files", divider=False)
        local_files = st.file_uploader("Choose a file:", key="local_file_uploader", accept_multiple_files=True)
        populate_button_disabled = len(local_files) == 0

    ######################################
    # Web Source
    ######################################
    if file_source == "Web":
        button_help = """
            This button is disabled if there the URL was unable to be validated.  Please check the URL.
        """
        st.subheader("Web Pages", divider=False)
        web_url = st.text_input("URL:", key="text_input_web_url")
        populate_button_disabled = not (web_url and utilities.is_url_accessible(web_url)[0])

    ######################################
    # OCI Source
    ######################################
    if file_source == "OCI":
        button_help = """
            This button is disabled if there are no documents from the source bucket split with
            the current split and embed options.  Please Split and Embed to enable Vector Storage.
        """
        if "oci_namespace" not in state:
            state.oci_namespace = utilities.oci_get_namespace(state.oci_config)
        oci_compartments = get_compartments()

        st.subheader("OCI Buckets", divider=False)

        src_bucket_list = []
        dst_bucket = None
        st.text(f"OCI namespace: {state.oci_namespace}")
        col2_1, col2_2 = st.columns([0.5, 0.5])
        with col2_1:
            bucket_compartment = st.selectbox(
                "Bucket compartment:",
                list(oci_compartments.keys()),
                index=None,
                placeholder="Select bucket compartment...",
            )
            if bucket_compartment:
                src_bucket_list = get_buckets(oci_compartments[bucket_compartment])
        with col2_2:
            src_bucket = st.selectbox(
                "Source bucket:",
                src_bucket_list,
                index=None,
                placeholder="Select source bucket...",
                disabled=not bucket_compartment,
            )

        if src_bucket:
            dst_bucket = src_bucket + "_" + store_table.lower()
            st.text(f"Destination Bucket: {dst_bucket}")
            src_objects = utilities.oci_get_bucket_objects(state.oci_config, state.oci_namespace, src_bucket)
            src_files = files_data_frame(src_objects)
        else:
            src_files = pd.DataFrame({"File": [], "Process": []})

        src_files_selected = files_data_editor(src_files, "source")
        if src_files_selected["Process"].sum() == 0:
            oci_load_button_disabled = True
        else:
            oci_load_button_disabled = False

        if st.button("Load, Split, and Upload", type="primary", disabled=oci_load_button_disabled):
            process_list = src_files_selected[src_files_selected["Process"]].reset_index(drop=True)
            progress_text = "Operation in progress. Please wait."
            progress_bar = st.progress(0, text=progress_text)
            progress_ind = 100 / len(process_list)
            for index, f in process_list.iterrows():
                progress_stat = int((((index + 1) * progress_ind) / 2))
                progress_bar.progress(progress_stat, text=progress_text)
                # Note directory/file is created/deleted on every iteration for space savings
                with tempfile.TemporaryDirectory() as temp_dir:
                    src_file = utilities.oci_get_object(
                        state.oci_config,
                        state.oci_namespace,
                        src_bucket,
                        temp_dir,
                        f.File,
                    )
                    _, split_file = split.load_and_split_documents(
                        [src_file],
                        selected_embed_model,
                        state.chunk_size_input,
                        chunk_overlap_size,
                        write_json=True,
                        output_dir=temp_dir,
                    )
                    utilities.oci_put_object(
                        state.oci_config,
                        state.oci_namespace,
                        oci_compartments[bucket_compartment],
                        dst_bucket,
                        split_file[0],
                    )
                progress_stat = int(((index + 1) * progress_ind))
                progress_bar.progress(progress_stat, text=progress_text)
            progress_bar.empty()
        # Embedding
        st.header("Embed", divider="rainbow")

        if dst_bucket:
            try:
                dst_objects = utilities.oci_get_bucket_objects(state.oci_config, state.oci_namespace, dst_bucket)
                dst_files = files_data_frame(dst_objects)
            except Exception as ex:
                logger.exception(ex)
                dst_files = pd.DataFrame({"File": [], "Process": []})
        else:
            dst_files = pd.DataFrame({"File": [], "Process": []})

        dst_files_selected = files_data_editor(dst_files, "destination")
        populate_button_disabled = dst_files_selected["Process"].sum() == 0

    ######################################
    # Populate Vector Store
    ######################################
    st.text(f"Vector Store: {store_table}")

    if st.button(
        "Populate Vector Store",
        type="primary",
        key="button_populate",
        disabled=populate_button_disabled,
        help=button_help,
    ):
        temp_dir = tempfile.TemporaryDirectory()
        split_docos = []
        try:
            db_conn = utilities.db_connect(state.db_config)
            placeholder = st.empty()
            with placeholder:
                st.warning("Populating Vector Store... please be patient.", icon="⚠️")

            if file_source == "Local":
                src_files = split.write_files(local_files)
                split_docos, _ = split.load_and_split_documents(
                    src_files,
                    selected_embed_model,
                    state.chunk_size_input,
                    chunk_overlap_size,
                    write_json=False,
                    output_dir=None,
                )

            if file_source == "Web":
                if web_url.endswith(".pdf"):
                    file_name = os.path.basename(web_url)
                    pdf_file = requests.get(web_url, timeout=60)
                    print(file_name)
                    print(temp_dir.name)
                    temp_file_path = os.path.join(temp_dir.name, file_name)
                    logger.info("Loading PDF from web to %s", temp_file_path)
                    # Write the content to a file with the extracted filename
                    with open(temp_file_path, "wb") as temp_file:
                        temp_file.write(pdf_file.content)
                    logger.info("Wrote %s", temp_file_path)
                    split_docos, _ = split.load_and_split_documents(
                        [temp_file_path],
                        selected_embed_model,
                        state.chunk_size_input,
                        chunk_overlap_size,
                        write_json=False,
                        output_dir=None,
                    )
                else:
                    split_docos, _ = split.load_and_split_url(
                        selected_embed_model,
                        web_url,
                        state.chunk_size_input,
                        chunk_overlap_size,
                    )

            if file_source == "OCI":
                process_list = dst_files_selected[dst_files_selected["Process"]].reset_index(drop=True)
                for index, f in process_list.iterrows():
                    object_file = utilities.oci_get_object(
                        state.oci_config,
                        state.oci_namespace,
                        dst_bucket,
                        temp_dir.name,
                        f.File,
                    )
                    split_docos.append(object_file)

            # Population
            utilities.populate_vs(
                db_conn,
                store_table,
                store_comment,
                model,
                distance_metric,
                split_docos,
            )
            placeholder.empty()
            st_common.reset_rag()
            st.success("Vector Store Populated.", icon="✅")

        except Exception as ex:
            placeholder.empty()
            logger.exception("Operation Failed: %s", ex)
            st.error(f"Operation Failed: {ex}.", icon="🚨")

        temp_dir.cleanup()


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
