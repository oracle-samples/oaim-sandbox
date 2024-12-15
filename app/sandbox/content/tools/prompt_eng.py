"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes a web interface for setting the chatbot instr using Streamlit (`st`).

Session States Set:
- prompts_config: Stores all Prompt Examples
"""
# spell-checker:ignore selectbox

import inspect
import streamlit as st
from streamlit import session_state as state

import sandbox.utils.st_common as st_common
import sandbox.utils.api_call as api_call
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("config.tools.prompt_eng")

# Set endpoint if server has been established
API_ENDPOINT = None
if "server" in state:
    API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/prompts"


#####################################################
# Functions
#####################################################
def get() -> dict[str, dict]:
    """Get a dictionary of all Prompts"""
    if "prompts_config" not in state or state["prompts_config"] == dict():
        try:
            state["prompts_config"] = api_call.get(url=API_ENDPOINT, token=state.server["key"])
            logger.info("State created: state['prompts_config']")
        except api_call.ApiError as ex:
            logger.error("Unable to retrieve prompts: %s", ex)
            st.error(f"Unable to retrieve prompts: {ex}", icon="🚨")
            state["prompts_config"] = dict()


def patch(category: str, prompt_name: str, prompt: str) -> None:
    """Update Prompt Instructions"""
    # Check if the prompt instructions are changed
    configured_prompt = next(
        item["prompt"]
        for item in state["prompts_config"]
        if item["name"] == prompt_name and item["category"] == category
    )
    if configured_prompt != prompt:
        try:
            api_call.patch(
                url=API_ENDPOINT + "/" + category + "/" + prompt_name,
                body={"data": {"prompt": prompt}},
                token=state.server["key"],
            )
            # Success
            logger.info("Prompt instructions updated for: %s (%s)", prompt_name, category)
            st.success(f"{prompt_name} Instructions - Updated", icon="✅")
            st_common.clear_state_key(f"selected_prompt_{category}_name")
            st_common.clear_state_key(f"prompt_{category}_prompt")
            st_common.clear_state_key("prompts_config")
            get()  # Refresh the Config
        except api_call.ApiError as ex:
            logger.info("Unable to perform prompt update for %s (%s): %s", prompt_name, category, ex)
            st.error(f"Unable to perform prompt update: {ex}", icon="🚨")
    else:
        st.info("Prompt Instructions - No Changes Detected.", icon="ℹ️")


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    st.header("Prompt Engineering")
    st.write("Select which prompts to use and their instructions.  Currently selected prompts are used.")
    get()  # Create/Rebuild state

    st.subheader("System Prompt")
    sys_dict = {item["name"]: item["prompt"] for item in state.prompts_config if item["category"] == "sys"}
    with st.container(border=True):
        selected_prompt_sys_name = st.selectbox(
            "Current System Prompt: ",
            options=list(sys_dict.keys()),
            index=list(sys_dict.keys()).index(state.user_settings["prompts"]["sys"]),
            key="selected_prompts_sys",
            on_change=st_common.update_user_settings_state,
            args=("prompts", "sys"),
        )
        prompt_sys_prompt = st.text_area(
            "System Instructions:",
            value=sys_dict[selected_prompt_sys_name],
            height=150,
            key="prompt_sys_prompt",
        )
        if st.button("Save Instructions", key="save_sys_prompt"):
            patch("sys", selected_prompt_sys_name, prompt_sys_prompt)

    st.subheader("Context Prompt")
    ctx_dict = {item["name"]: item["prompt"] for item in state.prompts_config if item["category"] == "ctx"}
    with st.container(border=True):
        selected_prompt_ctx_name = st.selectbox(
            "Current Context Prompt: ",
            options=list(ctx_dict.keys()),
            index=list(ctx_dict.keys()).index(state.user_settings["prompts"]["ctx"]),
            key="selected_prompts_ctx",
            on_change=st_common.update_user_settings_state,
            args=("prompts", "ctx"),
        )
        prompt_ctx_prompt = st.text_area(
            "Context Instructions:",
            value=ctx_dict[selected_prompt_ctx_name],
            height=150,
            key="prompt_ctx_prompt",
        )
        if st.button("Save Instructions", key="save_ctx_prompt"):
            patch("ctx", selected_prompt_ctx_name, prompt_ctx_prompt)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
