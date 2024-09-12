"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import math
import tempfile
import inspect

# Streamlit
import streamlit as st
from streamlit import session_state as state

import pandas as pd

# Configuration
from content.oci_config import initialise_streamlit as oci_initialise_streamlit
from content.db_config import initialise_streamlit as db_initialise_streamlit
from content.model_config import initialise_streamlit as model_initialise

# Modules
import modules.logging_config as logging_config
import modules.split as split
import modules.oci_utils as oci
import modules.vectorstorage as vectorstorage
import modules.db_utils as db_utils
import modules.st_common as st_common

logger = logging_config.logging.getLogger("chunk_embed")

### Currently the only supported Framework is Langchain
FRAMEWORK = "langchain"


#####################################################
# Functions
#####################################################
@st.cache_data
def get_compartments():
    """Get OCI Compartments; function for Streamlit caching"""
    return oci.get_compartments(state.oci_config)


def filesdataframe(objects, process=False):
    """Produce a dataframe of files"""
    files = pd.DataFrame({"File": [], "Process": []})
    if len(objects) >= 1:
        files = pd.DataFrame(
            {"File": [objects[0]], "Process": [process]},
        )
        for file in objects[1:]:
            new_record = pd.DataFrame([{"File": file, "Process": process}])
            files = pd.concat([files, new_record], ignore_index=True)
    return files


def filesdataeditor(files, key):
    """Edit Dataframe"""
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
    db_initialise_streamlit()
    if not state.db_configured:
        st.error("Database is not configured, all functionality is disabled", icon="🚨")
        st.stop()

    model_initialise()

    file_sources = ["OCI", "Local", "Web"]
    oci_initialise_streamlit()
    if not state.oci_configured:
        st.warning("OCI is not configured, some functionality is disabled", icon="⚠️")
        file_sources.remove("OCI")
    #############################################################################
    # GUI
    #############################################################################
    st.header("Embedding Configuration", divider="rainbow")
    selected_embed_model = st.selectbox(
        "Embedding models available: ",
        options=list(key for key, value in state.embed_model_config.items() if value.get("enabled")),
        index=0,
        key="select_box_embed_model",
    )
    try:
        model, api_accessible, err_msg = vectorstorage.get_embedding_model(
            selected_embed_model, state.embed_model_config
        )
        embed_url = state.embed_model_config[selected_embed_model]["url"]
        st.write(f"Embedding Server: {embed_url}")
    except KeyError:
        st.error("No embedding models are are configured and/or enabled.", icon="⚠️",)
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
    chunk_overlap_size = math.ceil((state.chunk_overlap_input / 100) * state.chunk_size_input)
    store_table, store_comment = vectorstorage.get_vs_table(
        selected_embed_model, state.chunk_size_input, chunk_overlap_size, distance_metric
    )
    ######################################
    # Splitting
    ######################################
    st.header("Load and Split Documents", divider="rainbow")
    file_source = st.radio("File Source:", file_sources, key="radio_file_source", horizontal=True)

    ######################################
    # Local Source
    ######################################
    if file_source == "Local":
        st.subheader("Local Files", divider=False)
        local_files = st.file_uploader("Choose a file:", key="local_file_uploader", accept_multiple_files=True)
        src_files = []
        split_docos = []
        if len(local_files) > 0:
            src_files = split.write_files(local_files)
            split_docos, _ = split.load_and_split_documents(
                src_files,
                selected_embed_model,
                state.chunk_size_input,
                chunk_overlap_size,
                write_json=False,
                output_dir=None,
            )

        # List out Split Files
        if len(split_docos) == 0:
            store_button_disabled = True
        else:
            store_button_disabled = False

        st.text(f"Vector Store: {store_table}")
        if st.button(
            "Populate Vector Store",
            type="primary",
            key="button_local_load",
            disabled=store_button_disabled,
        ):
            placeholder = st.empty()
            with placeholder:
                st.warning("Populating Vector Store... please be patient.", icon="⚠️")
            try:
                db_conn = db_utils.connect(state.db_config)
                vectorstorage.populate_vs(
                    db_conn,
                    store_table,
                    store_comment,
                    model,
                    distance_metric,
                    documents=split_docos,
                )
                placeholder.empty()
                st_common.reset_rag()
                st.success("Vector Store Populated.", icon="✅")
            except Exception as ex:
                placeholder.empty()
                st.error(f"Operation Failed: {ex}.", icon="🚨")

    ######################################
    # Web Source
    ######################################
    if file_source == "Web":
        st.subheader("Web Pages", divider=False)
        web_url = st.text_input("URL:", key="text_input_web_url")
        web_load_button_disabled = True
        if web_url:
            url_accessible, err_msg = vectorstorage.is_url_accessible(web_url)
            web_load_button_disabled = not url_accessible

        st.text(f"Vector Store: {store_table}")
        if st.button(
            "Load, Split, and Populate Vector Store",
            type="primary",
            key="button_web_load",
            disabled=web_load_button_disabled,
        ):
            placeholder = st.empty()
            with placeholder:
                st.warning("Operation in progress... please be patient.", icon="⚠️")
            try:
                split_docos, _ = split.load_and_split_url(
                    selected_embed_model,
                    web_url,
                    state.chunk_size_input,
                    chunk_overlap_size,
                )
                db_conn = db_utils.connect(state.db_config)
                # If API Key is needed and not set, it will except here
                vectorstorage.populate_vs(
                    db_conn,
                    store_table,
                    store_comment,
                    model,
                    distance_metric,
                    documents=split_docos,
                )
                placeholder.empty()
                st_common.reset_rag()
                st.success("Operation Completed.", icon="✅")
            except Exception as ex:
                placeholder.empty()
                st.error(f"Operation Failed: {ex}.", icon="🚨")

    ######################################
    # OCI Source
    ######################################
    if file_source == "OCI":
        if "oci_namespace" not in state:
            state.oci_namespace = oci.get_namespace(state.oci_config)
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
                src_bucket_list = oci.get_buckets(
                    state.oci_config,
                    state.oci_namespace,
                    oci_compartments[bucket_compartment],
                )

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
            src_objects = oci.get_bucket_objects(state.oci_config, state.oci_namespace, src_bucket)
            src_files = filesdataframe(src_objects)
        else:
            src_files = pd.DataFrame({"File": [], "Process": []})

        src_files_selected = filesdataeditor(src_files, "source")
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
                with tempfile.TemporaryDirectory() as tmpdirname:
                    src_file = oci.get_object(
                        state.oci_config,
                        state.oci_namespace,
                        src_bucket,
                        tmpdirname,
                        f.File,
                    )
                    _, split_file = split.load_and_split_documents(
                        [src_file],
                        selected_embed_model,
                        state.chunk_size_input,
                        chunk_overlap_size,
                        write_json=True,
                        output_dir=tmpdirname,
                    )
                    oci.put_object(
                        state.oci_config,
                        state.oci_namespace,
                        oci_compartments[bucket_compartment],
                        dst_bucket,
                        split_file,
                    )
                progress_stat = int(((index + 1) * progress_ind))
                progress_bar.progress(progress_stat, text=progress_text)
            progress_bar.empty()
        # Embedding
        st.header("Embed", divider="rainbow")

        if dst_bucket:
            try:
                dst_objects = oci.get_bucket_objects(state.oci_config, state.oci_namespace, dst_bucket)
                dst_files = filesdataframe(dst_objects)
            except Exception as ex:
                logger.exception(ex)
                dst_files = pd.DataFrame({"File": [], "Process": []})
        else:
            dst_files = pd.DataFrame({"File": [], "Process": []})

        dst_files_selected = filesdataeditor(dst_files, "destination")
        if dst_files_selected["Process"].sum() == 0:
            store_button_disabled = True
        else:
            store_button_disabled = False

        st.text(f"Vector Store: {store_table}")
        if st.button(
            "Populate Vector Store",
            type="primary",
            disabled=store_button_disabled,
            help="""
                This button is disabled if there are no documents from the source bucket split with
                the current split and embed options.  Please Split and Embed to enable Vector Storage.
            """,
        ):
            placeholder = st.empty()
            with placeholder:
                st.warning("Populating Vector Store... please be patient.", icon="⚠️")
            process_list = dst_files_selected[dst_files_selected["Process"]].reset_index(drop=True)
            logger.info("Processing %i files", len(process_list))
            progress_text = "Operation in progress. Please wait."
            progress_bar = st.progress(0, text=progress_text)
            progress_ind = 100 / len(process_list)
            db_conn = db_utils.connect(state.db_config)
            for index, f in process_list.iterrows():
                progress_stat = int((((index + 1) * progress_ind) / 2))
                progress_bar.progress(progress_stat, text=progress_text)
                # Note directory/file is created/deleted on every iteration for space savings
                with tempfile.TemporaryDirectory() as tmpdirname:
                    dst_file = oci.get_object(
                        state.oci_config,
                        state.oci_namespace,
                        dst_bucket,
                        tmpdirname,
                        f.File,
                    )
                    vectorstorage.populate_vs(
                        db_conn,
                        store_table,
                        store_comment,
                        model,
                        distance_metric,
                        src_files=[dst_file],
                    )
                progress_stat = int(((index + 1) * progress_ind))
                progress_bar.progress(progress_stat, text=progress_text)
            progress_bar.empty()
            placeholder.empty()
            st_common.reset_rag()
            st.success("Vector Store Populated.", icon="✅")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
