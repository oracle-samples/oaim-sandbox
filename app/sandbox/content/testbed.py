"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# spell-checker:ignore streamlit, selectbox, testset, testsets
import random
import string
import inspect
import json
from io import BytesIO

import pandas as pd

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
def reset_testset(cache: bool = False) -> None:
    """Clear all Test Set Data"""
    st_common.clear_state_key("testbed")
    st_common.clear_state_key("selected_testset_name")
    st_common.clear_state_key("testbed_qa")
    st_common.clear_state_key("testbed_db_testsets")
    if cache:
        get_testbed_db_testsets.clear()


@st.cache_data
def get_testbed_db_testsets() -> dict:
    """Get Database TestSets; this is cached"""
    return api_call.get(url=f"{API_ENDPOINT}/testsets")["data"]


def qa_update_db() -> None:
    """Update QA in Database"""
    update_record(0)  # Ensure any changes made to current record are recorded
    api_url = f"{API_ENDPOINT}/testset_load"
    api_params = {
        "name": state.selected_new_testset_name,
        "tid": state.testbed["testset_id"],
    }
    json_data = json.dumps(state.testbed_qa)

    qa_file = BytesIO(json_data.encode("utf-8"))
    api_payload = {"files": [("files", ("data.json", qa_file, "application/json"))]}
    _ = api_call.post(url=api_url, params=api_params, payload=api_payload, timeout=120)
    st_common.clear_state_key("testbed_db_testsets")
    get_testbed_db_testsets.clear()
    state.testbed_db_testsets = get_testbed_db_testsets()


@st.fragment()
def update_record(direction: int = 0) -> None:
    """Update streamlit state with user changes"""
    state.testbed_qa[state.testbed["qa_index"]]["question"] = state[f"selected_q_{state.testbed['qa_index']}"]
    state.testbed_qa[state.testbed["qa_index"]]["reference_answer"] = state[f"selected_a_{state.testbed['qa_index']}"]
    state.testbed["qa_index"] += direction


def qa_update_gui(qa_testset: list) -> None:
    """Update Q&A Records in GUI"""
    dataframe = pd.DataFrame(qa_testset)
    records = dataframe.shape[0]
    st.write("Record: " + str(state.testbed["qa_index"] + 1) + "/" + str(records))

    prev_disabled = next_disabled = records == 0
    if state.testbed["qa_index"] == 0:
        prev_disabled = True
    if state.testbed["qa_index"] + 1 == records:
        next_disabled = True
    prev_col, next_col, _ = st.columns([3, 3, 6])
    prev_col.button(
        "← Previous",
        disabled=prev_disabled,
        use_container_width=True,
        on_click=update_record,
        kwargs=dict(direction=-1),
    )
    next_col.button(
        "Next →",
        disabled=next_disabled,
        use_container_width=True,
        on_click=update_record,
        kwargs=dict(direction=1),
    )
    st.text_area(
        "Question:",
        dataframe.loc[state.testbed["qa_index"], "question"],
        key=f"selected_q_{state.testbed['qa_index']}",
    )
    st.text_area(
        "Answer:",
        dataframe.loc[state.testbed["qa_index"], "reference_answer"],
        key=f"selected_a_{state.testbed['qa_index']}",
    )
    st.text_area(
        "Context:",
        dataframe.loc[state.testbed["qa_index"], "reference_context"],
        disabled=True,
        height=68,
    )
    st.text_input("Metadata:", dataframe.loc[state.testbed["qa_index"], "metadata"], disabled=True)


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
    gen_testset_disabled = False
    get_model(model_type="embed", only_enabled=True)
    available_embed_models = [key for key, value in state.embed_model_enabled.items() if value.get("openai_compat")]
    if not available_embed_models:
        st.warning(
            "No OpenAI compatible embedding models are configured and/or enabled. Disabling Test Set Generation.",
            icon="⚠️",
        )
        gen_testset_disabled = True

    testset_sources = ["Database", "Local"]
    if "testbed_db_testsets" not in state:
        state.testbed_db_testsets = get_testbed_db_testsets()
    if not state.testbed_db_testsets:
        testset_sources.remove("Database")

    #############################################################################
    # GUI
    #############################################################################
    st.header("Testbed", divider="red")
    st.write("""
             Test Large Language and Embedding Configurations by generating or using an existing 'Test Set'.
             """)

    # Initialise the testbed state
    if "testbed" not in state:
        state.testbed = {
            "uploader_key": random.randint(1, 100),
            "qa_index": 0,
            "testset_id": None,
            "testset_name": "".join(random.choices(string.ascii_letters, k=16)),
        }

    # Available/Compatible Model(s) found; continue
    st.toggle(
        "Generate Q&A Test Set",
        key="selected_generate_test",
        value=False,
        disabled=gen_testset_disabled,
        on_change=reset_testset,
        help="Create a new Test Set to be used for evaluation.",
    )

    ###################################
    # Load/Generate Test Set
    ###################################
    button_load_disabled = True
    button_text, api_url, testset_source = None, None, None
    api_params = {"timeout": 3600}
    if not state.selected_generate_test:
        st.subheader("Run Existing Q&A Test Set", divider="red")
        button_text = "Load Q&A"
        testset_source = st.radio(
            "TestSet Source:",
            testset_sources,
            index=0,
            key="radio_test_source",
            horizontal=True,
            on_change=reset_testset,
            kwargs=dict(cache=True),
        )
        if testset_source == "Local":
            # Upload a TestSet from client host
            api_url = f"{API_ENDPOINT}/testset_load"
            test_upload_file = st.file_uploader(
                "Select a local, existing Q&A Test Set",
                key=f"selected_uploader_{state.testbed['uploader_key']}",
                accept_multiple_files=True,
                type=["jsonl", "json"],
            )
            button_load_disabled = len(test_upload_file) == 0
        else:
            # Select existing TestSet from Database
            api_url = f"{API_ENDPOINT}/testset_qa"
            testset_list = [f"{item['name']} -- Created: {item['created']}" for item in state.testbed_db_testsets]
            db_testset = st.selectbox(
                "Test Set:", options=testset_list, key="selected_db_testset", on_change=reset_testset
            )
            button_load_disabled = db_testset is None

    # Generate Test
    if state.selected_generate_test:
        st.subheader("Generate new Q&A Test Set", divider="red")
        button_text = "Generate Q&A"
        api_url = f"{API_ENDPOINT}/testset_generate"
        test_upload_file = st.file_uploader(
            (
                "Select a local PDF file to build a temporary Knowledge Base. "
                "It will be used to generate a synthetic Q&A Test Set."
            ),
            key=f"selected_uploader_{state.testbed['uploader_key']}",
            accept_multiple_files=False,
            type="pdf",
        )
        button_load_disabled = test_upload_file is None
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

    # Process Q&A Request
    button_load_disabled = button_load_disabled or state.testbed["testset_id"] == ""
    col_left, col_center, _ = st.columns([3, 3, 4])
    if not button_load_disabled:
        if "load_tests" in state and state.load_tests is True:
            state.running = True
        else:
            state.running = False
    else:
        state.running = True
    if col_left.button(button_text, key="load_tests", use_container_width=True, disabled=state.running):
        placeholder = st.empty()
        with placeholder:
            st.info("Processing Q&A... please be patient.", icon="⚠️")
        if testset_source != "Database":
            api_params["name"] = state.testbed["testset_name"]
            files = st_common.local_file_payload(state[f"selected_uploader_{state.testbed['uploader_key']}"])
            api_payload = {"files": files}
            try:
                response = api_call.post(url=api_url, params=api_params, payload=api_payload)
                get_testbed_db_testsets.clear()
                state.testbed_db_testsets = get_testbed_db_testsets()
                state.testbed["testset_id"] = next(
                    (d["tid"] for d in state.testbed_db_testsets if d.get("name") == state.testbed["testset_name"]),
                    None,
                )
            except Exception as ex:
                logger.error("Exception: %s", ex)
                st.error("Test Sets not compatible.", icon="🚨")
        else:
            # Set required state from splitting selected DB TestSet
            testset_name, testset_created = state.selected_db_testset.split(" -- Created: ", 1)
            state.testbed["testset_name"] = testset_name
            state.testbed["testset_id"] = next(
                (
                    d["tid"]
                    for d in state.testbed_db_testsets
                    if d["name"] == testset_name and d["created"] == testset_created
                ),
                None,
            )
            response = api_call.get(url=api_url, params={"tid": state.testbed["testset_id"]})
        state.testbed_qa = response["data"]["qa_data"]
        st.success(f"{len(state.testbed_qa)} Tests Loaded.", icon="✅")
        placeholder.empty()
    col_center.button(
        "Reset",
        key="reset_test_framework",
        type="primary",
        use_container_width=True,
        on_click=reset_testset,
        kwargs={"cache": True},
    )

    ###################################
    # Show/Edit Q&A Tests
    ###################################
    if "testbed_qa" in state:
        st.subheader("Q&A Test Set Details", divider="red")
        st.text_input(
            "Test Set Name:",
            max_chars=20,
            key="selected_new_testset_name",
            value=state.testbed["testset_name"],
            help="Update your Test Set a name to easily identify it later.",
            on_change=qa_update_db,
        )
        qa_update_gui(state.testbed_qa)
        testbed_qa_df = pd.DataFrame(state.testbed_qa)
        st.download_button(
            label="Download",
            data=testbed_qa_df.to_json(orient="records", indent=4),
            file_name=f"{state.selected_new_testset_name}_testset.json",
            mime="application/json",
            on_click=qa_update_db,
        )
        ###################################
        # Evaluator
        ###################################
        st.subheader("Q&A Evaluation", divider="red")
        st.info("Use the sidebar settings for evaluation parameters", icon="⬅️")
        st_common.ll_sidebar()
        st_common.rag_sidebar()
        if st.button(
            "Start Evaluation",
            type="primary",
            key="evaluate_button",
            help="Evaluation will automatically save the TestSet to the Database",
            on_click=qa_update_db,
        ):
            st_common.copy_user_settings(new_client="testbed")
            placeholder = st.empty()
            with placeholder:
                st.warning("Starting Q&A evaluation... please be patient.", icon="⚠️")
            api_url = f"{API_ENDPOINT}/evaluate"
            api_params = {"tid": state.testbed["testset_id"]}
            evaluate = api_call.post(url=api_url, params=api_params, timeout=1200)
            st.success("Evaluation Complete!", icon="✅")
            placeholder.empty()

        ###################################
        # Results
        ###################################
        # if evaluate:
        #     st.subheader("Results", divider="red")
        #     results = evaluate["data"][0]


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
