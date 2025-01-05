"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, selectbox

import inspect
import streamlit as st
from streamlit import session_state as state

from sandbox.content.config.models import get_model
import sandbox.utils.st_common as st_common
import sandbox.utils.api_call as api_call

import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.content.testbed")

# Set endpoint if server has been established
API_ENDPOINT = None
EMBED_API_ENDPOINT = None
if "server" in state:
    API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/testbed"
    EMBED_API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/embed"


#####################################################
# Functions
#####################################################
def reset_test_set():
    """Clear all Test Set Data"""
    state.test_uploader_key += 1


@st.fragment()
def download_test_set(test_set_edited):
    """Download Files; in fragment function to Prevent Page Re-Load"""
    json_data = test_set_edited.to_json(orient="records", lines=True).encode("utf-8")
    st.download_button(label="Download Q&A Test Set", file_name="test_set.json", data=json_data)


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    db_avail = st_common.is_db_configured()
    if not db_avail:
        logger.debug("Testbed Disabled (Database not configured)")
        st.error("Database is not configured. Disabling Testbed.", icon="🛑")

    # If there is no eligible (OpenAI Compat.) LL Models; then disable ALL functionality
    get_model(model_type="ll", only_enabled=True)
    available_ll_models = [key for key, value in state.ll_model_enabled.items() if value.get("openai_compat")]
    if not available_ll_models:
        st.error(
            "No OpenAI compatible language models are configured and/or enabled. Disabling Testing Framework.",
            icon="🛑",
        )

    if not db_avail or not available_ll_models:
        st.stop()

    # If there is no eligible (OpenAI Compat.) Embedding Model; disable Generate Test Set
    gen_test_set_disabled = False
    get_model(model_type="embed", only_enabled=True)
    available_embed_models = [key for key, value in state.embed_model_enabled.items() if value.get("openai_compat")]
    if not available_embed_models:
        st.warning(
            "No OpenAI compatible embedding models are configured and/or enabled. Disabling Test Set Generation.",
            icon="⚠️",
        )
        gen_test_set_disabled = True

    test_set_sources = ["Local", "Database"]
    if "db_test_sets" not in state:
        state.db_test_sets = api_call.get(url=f"{API_ENDPOINT}/test_sets")["data"]
    if not state.db_test_sets:
        test_set_sources.remove("Database")
    #############################################################################
    # GUI
    #############################################################################
    st.header("Testbed", divider="red")
    st.write("Test Large Language and Embedding Configurations")

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
    if "test_set" not in state:
        state.test_set = []

    ###################################
    # Load/Generate Test Set
    ###################################
    button_text, api_url = None, None
    api_params = {}
    if not state.selected_generate_test:
        st.header("Run Existing Q&A Test Dataset")
        button_text = "Load Q&A"
        api_url = f"{API_ENDPOINT}/test_sets"
        test_set_source = st.radio("Test Set Source:", test_set_sources, key="radio_test_source", horizontal=True)
        if test_set_source == "Local":
            st.file_uploader(
                "Select a local, existing Q&A pair testing dataset:",
                key=f"uploader_{state.test_uploader_key}",
                accept_multiple_files=True,
                type=["jsonl", "json"],
            )
    if state.selected_generate_test:
        st.header("Q&A Test Dataset Generation")
        button_text = "Generate Q&A"
        api_url = f"{API_ENDPOINT}/generate_qa"
        st.file_uploader(
            (
                "Select a local PDF file to build a temporary Knowledge Base. "
                "It will be used to generate a synthetic Q&A pair testing dataset."
            ),
            key=f"uploader_{state.test_uploader_key}",
            accept_multiple_files=False,
            type="pdf",
        )
        col_left, col_center, col_right = st.columns([0.2, 0.35, 0.35])
        test_gen_questions = col_left.number_input(
            "Number of Q&A:",
            key="selected_test_gen_questions",
            min_value=0,
            max_value=100,
            value=2,
        )
        test_gen_llm = col_center.selectbox(
            "Q&A Language Model:",
            key="selected_test_gen_llm",
            options=available_ll_models,
            index=0,
            help="Don't see your model? Unfortunately it is not currently supported by the testing framework.",
        )
        test_gen_embed = col_right.selectbox(
            "Q&A Embedding Model:",
            key="selected_test_gen_embed",
            options=available_embed_models,
            index=0,
            help="Don't see your model? Unfortunately it is not currently supported by the testing framework.",
        )
        api_params = {"ll_model": test_gen_llm, "embed_model": test_gen_embed, "questions": test_gen_questions}

    test_set_name = st.text_input(
        "Test Set Name (Required):",
        max_chars=20,
        key="selected_test_set_name",
        placeholder="Press Enter to set.",
    )
    button_load_disabled = state[f"uploader_{state.test_uploader_key}"] is None or test_set_name == ""
    col_left, col_center, _ = st.columns([0.2, 0.35, 0.35])
    if col_left.button(button_text, key="load_tests", disabled=button_load_disabled):
        placeholder = st.empty()
        with placeholder:
            st.info("Processing Q&A... please be patient.", icon="⚠️")
        api_params["name"] = test_set_name
        files = st_common.local_file_payload(state[f"uploader_{state.test_uploader_key}"])
        api_payload = {"files": files}
        try:
            response = api_call.post(url=api_url, params=api_params, payload=api_payload)
            test_timestamp = response["data"]["date_loaded"]
            test_count = response["data"]["test_count"]
            placeholder.empty()
            st.success(f"{test_count} Tests Loaded.", icon="✅")
            st_common.clear_state_key("db_test_sets")
        except Exception as ex:
            logger.error("Exception: %s", ex)
            st.error("Test Sets not compatible.", icon="🚨")

    col_center.button("Reset", key="reset_test_framework", type="primary", on_click=reset_test_set)

    ###################################
    # Create Test Set
    ###################################

    # if not test_qa_gen_button_disabled:
    #     if "button_generate" in state and state.button_generate is True:
    #         state.running = True
    #     else:
    #         state.running = False
    # else:
    #     state.running = True

    # if col_left.button("Generate Q&A", type="primary", key="button_generate", disabled=state.running):
    #     placeholder = st.empty()
    #     with placeholder:
    #         st.warning("Starting Q&A generation... please be patient.", icon="⚠️")

    #     # Send file to server
    #     api_url = f"{EMBED_API_ENDPOINT}/local/store"
    #     api_params = {"client": state.user_settings["client"], "directory": "testbed"}
    #     files = st_common.local_file_payload(state[f"uploader_{state.test_uploader_key}"])
    #     api_payload = {"files": files}
    #     _ = api_call.post(url=api_url, params=api_params, payload=api_payload)

    #     # Generate Q&A
    #     api_url = f"{API_ENDPOINT}/generate_qa"
    #     api_params["ll_model"] = test_qa_llm
    #     api_params["embed_model"] = test_qa_embed
    #     api_params["questions"] = test_qa_count
    #     test_set_data = api_call.post(url=api_url, params=api_params)
    #     state.test_set = test_set_data["data"]
    #     placeholder.empty()
    #     st.success("Q&A Test Dataset Generated", icon="✅")

    # ###################################
    # # Show/Edit Q&A Tests
    # ###################################
    # if state.test_set:
    #     test_set_edited = pd.DataFrame(state.test_set).drop_duplicates(subset=["question"])
    #     st.write(test_set_edited)
    #     download_test_set(test_set_edited)

    #     ###################################
    #     # Evaluator
    #     ###################################
    #     st.header("Q&A Evaluation")
    #     st.info("Use the sidebar settings for evaluation parameters", icon="⬅️")
    #     st_common.ll_sidebar()
    #     st_common.rag_sidebar()
    #     if st.button("Start Evaluation", type="primary", key="evaluate_button"):
    #         placeholder = st.empty()
    #         with placeholder:
    #             st.warning("Starting Q&A evaluation... please be patient.", icon="⚠️")
    #             st_common.copy_user_settings(new_client="testbed")

    #             # Upload TestSet
    #             # api_url = f"{EMBED_API_ENDPOINT}/local/store"
    #             # api_params = {"client": state.user_settings["client"], "directory": "testbed"}
    #             # files = BytesIO(f"{state.test_uploader_key}.json", json.dumps(state.test_set).encode("utf-8")])
    #             # api_payload = {"files": files}
    #             # _ = api_call.post(url=api_url, params=api_params, payload=api_payload)

    #             api_url = f"{API_ENDPOINT}/evaluate"
    #             params = {"test_set_id": state.state.test_uploader_key}
    #             evaluate = api_call.post(url=api_url, params=params)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
