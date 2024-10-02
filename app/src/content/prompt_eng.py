"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes a web interface for setting the chatbot instr using Streamlit (`st`).
It includes a form to input the instr used for chatbot prompt engineering.
"""
# spell-checker:ignore streamlit, selectbox

import re
import inspect
import modules.logging_config as logging_config
import modules.metadata as metadata

# Streamlit
import streamlit as st
from streamlit import session_state as state

logger = logging_config.logging.getLogger("prompt_eng")


#####################################################
# Functions
#####################################################
def initialize_streamlit():
    """Initialize chatbot instructions in the application state."""

    ## Language Model Prompt
    if "lm_instr" not in state:
        state.lm_instr_config = metadata.prompt_engineering()
        state.lm_instr_prompt = list(state.lm_instr_config.keys())[0]
        state.lm_instr = state.lm_instr_config[state.lm_instr_prompt]["prompt"]
        logger.info("Initialized Language Model Prompt")

    if "context_instr" not in state:
        state.context_instr = """
            Given a chat history and the latest user question
            which might reference context in the chat history, formulate a standalone question
            which can be understood without the chat history. Do NOT answer the question,
            just reformulate it if needed and otherwise return it as is.""".strip()

        state.context_instr = " ".join(re.split(r"\s+", state.context_instr, flags=re.UNICODE))
        logger.info("Initialized Context Prompt")


def update_lm_instr():
    """Set the LM Prompt Instructions"""
    state.lm_instr_prompt = state.selectbox_lm_instr_prompt
    state.lm_instr = state.lm_instr_config[state.lm_instr_prompt]["prompt"]


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    initialize_streamlit()
    st.header("Prompt Engineering")

    with st.container(border=True):
        lm_instr_prompt = st.selectbox(
            "Language Model Prompt: ",
            options=list(state.lm_instr_config.keys()),
            index=list(state.lm_instr_config.keys()).index(state.lm_instr_prompt),
            key="selectbox_lm_instr_prompt",
            on_change=update_lm_instr,
        )
        lm_instr = st.text_area(
            "Language Model Instructions:",
            value=state.lm_instr_config[lm_instr_prompt]["prompt"],
            height=125,
            key="text_area_lm_instr",
        )
        if st.button("Save"):
            state.lm_instr_config[lm_instr_prompt]["prompt"] = " ".join(re.split(r"\s+", lm_instr, flags=re.UNICODE))
            update_lm_instr()
            st.success("Engineered Prompt Saved", icon="✅")

    with st.form("update_contextualize_prompt"):
        context_instr = st.text_area(
            "Contextualize Instructions:",
            value=state.context_instr,
            height=125,
            help="For creating context",
            key="text_area_context_instr",
        )
        if st.form_submit_button(label="Save"):
            state.context_instr = " ".join(re.split(r"\s+", context_instr, flags=re.UNICODE))
            st.success("Contextualize Prompt Saved", icon="✅")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
