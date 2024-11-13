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
    """Initialize chatbot agents in the application state."""

    ## Language Model Prompt
    if "agents_instr" not in state:
        state.agents_instr = metadata.agents()
        logger.info("Initialized Agents")
        logger.info(state.agents_instr)
        state.agents_selected = state.agents_instr["DEFAULT"]


def update_agents():
    """Set the Agents"""
    state.agents_selected["name"] = state.text_area_ag_name
    state.agents_selected["desc"] = state.text_area_ag_desc
    state.agents_selected["action"] = state.text_area_ag_action


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    initialize_streamlit()
    st.header("Agents configuration")

    with st.container(border=True):

        ag_name = st.text_area(
            "Agents name:",
            value=state.agents_selected["name"],
            height=125,
            key="text_area_ag_name",
        )
        
        ag_desc = st.text_area(
            "Agents description:",
            value=state.agents_selected["desc"],
            height=125,
            key="text_area_ag_desc",
        )
        ag_sql = st.text_area(
            "Action:",
            value=state.agents_selected["action"],
            height=125,
            key="text_area_ag_action",
        )

        if st.button("Save"):
            #state.lm_instr_config[lm_instr_prompt]["prompt"] = " ".join(re.split(r"\s+", lm_instr, flags=re.UNICODE))
            update_agents()
            st.success("Engineered Prompt Saved", icon="✅")

 

if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
