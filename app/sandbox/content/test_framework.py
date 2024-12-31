"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit

import inspect
import streamlit as st
from streamlit import session_state as state

from sandbox.content.config.models import get_model
import sandbox.utils.st_common as st_common


import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.content.test_framework")


#####################################################
# Functions
#####################################################


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    st.header("Test Framework")
    st.write("Test Large Language and Embedding Configurations")

    # If there is no eligible (OpenAI Compat.) LL Models; then disable ALL functionality
    get_model(model_type="ll", only_enabled=True)
    test_qa_ll_models = [key for key, value in state.ll_model_enabled.items() if value.get("openai_compat")]
    if len(test_qa_ll_models) == 0:
        st.error(
            "No OpenAI compatible language models are configured and/or enabled. Disabling Testing Framework.",
            icon="❌",
        )
        st.stop()

    # If there is no eligible (OpenAI Compat.) Embedding Model; disable Generate Test Set
    gen_test_set_disabled = False
    get_model(model_type="embed", only_enabled=True)
    test_qa_embed_models = [key for key, value in state.embed_model_enabled.items() if value.get("openai_compat")]
    if len(test_qa_embed_models) == 0:
        st.error(
            "No OpenAI compatible embedding models are configured and/or enabled. Disabling Test Set Generation.",
            icon="❌",
        )
        gen_test_set_disabled = True

    # Used to clear the uploader files
    if "test_uploader_key" not in state:
        state.test_uploader_key = 0

    # Available/Compatible Model(s) found; continue
    st.toggle(
        "Generate new Test Dataset",
        key="selected_generate_test",
        value=False,
        disabled=gen_test_set_disabled,
        # on_change=reset_test_set,
        help="Create a new test dataset to be used for evaluation.",
    )

    ###################################
    # Create or Load Tests
    ###################################
    if state.selected_generate_test:
        st.header("Q&A Test Dataset Generation")
        test_qa_gen_file = st.file_uploader(
            (
                "Select a local PDF file to build a temporary Knowledge Base. "
                "It will be used to generate a synthetic Q&A pair testing dataset."
            ),
            key=f"uploader_{state.test_uploader_key}",
            accept_multiple_files=False,
            type="pdf",
        )
        gen_left, gen_center, gen_right = st.columns([0.3, 0.3, 0.3])
        test_qa_count = gen_left.number_input(
            "Number of Q&A to Generate:",
            key="selected_test_qa_count",
            min_value=0,
            max_value=100,
            value=2,
        )
        test_qa_embed = gen_center.selectbox(
            "Q&A Generation Embedding Model:",
            options=test_qa_embed_models,
            index=0,
            help="Don't see your model? Unfortunately it is not currently supported by the testing framework.",
            key="selected_test_qa_embed",
        )
        test_qa_llm = gen_right.selectbox(
            "Q&A Generation Language Model:",
            options=test_qa_ll_models,
            index=0,
            key="selected_test_qa_llm",
            help="Don't see your model? Unfortunately it is not currently supported by the testing framework.",
        )
        test_qa_gen_button_disabled = True
        if test_qa_gen_file:
            test_qa_gen_button_disabled = False

        left, right = st.columns([0.15, 0.85])
        if left.button("Generate Q&A", type="primary", key="qa_generation", disabled=test_qa_gen_button_disabled):
            placeholder = st.empty()
            with placeholder:
                st.info("Starting Q&A generation... please be patient.", icon="⚠️")




    if not state.selected_generate_test:
        st.header("Run Existing Q&A Test Dataset")

    # # the sidebars will set this to False if not everything is configured.
    # state.enable_sandbox = True
    # st_common.history_sidebar()
    # st_common.ll_sidebar()
    # st_common.rag_sidebar()
    # # Stop when sidebar configurations not set
    # if not state.enable_sandbox:
    #     st.stop()


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
