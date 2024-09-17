"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v 1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import os
import json
import inspect
import pandas as pd

# Streamlit
import streamlit as st
from streamlit import session_state as state
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
import modules.logging_config as logging_config

# Utilities
import modules.st_common as st_common
import modules.logging_config as logging_config
import modules.split as split
import modules.test_framework as test_framework
import modules.chatbot as chatbot
import modules.report_utils as report_utils


# Help


from giskard.rag import QATestset
from giskard.rag import evaluate
import plotly.graph_objects as go

logger = logging_config.logging.getLogger("test_framework")


#############################################################################
# Functions
#############################################################################
def reset_test_set():
    """Clear all Test Set Data"""

    if "index" in st.session_state:
        state.pop("index", None)
    if "hide_input" in st.session_state:
        state.pop("hide_input", None)
    if "question_input" in st.session_state:
        state.pop("question_input", None)
    if "reference_answer_input" in st.session_state:
        state.pop("reference_answer_input", None)
    if "reference_context_input" in st.session_state:
        state.pop("reference_context_input", None)
    if "metadata_input" in st.session_state:
        state.pop("metadata_input", None)

    state.test_uploader_key += 1
    state.pop("test_set_report", None)
    state.pop("test_set", None)
    state.pop("temp_dir", None)
    state.pop("file_temp", None)


def get_answer_fn(question: str, history=None) -> str:
    """Send for completion"""
    # Format appropriately the history for your RAG agent
    chat_history_empty = StreamlitChatMessageHistory(key="empty")
    chat_history_empty.clear()
    if history:
        for h in history:
            if h["role"] == "assistant":
                chat_history_empty.add_ai_message(h["content"])
            else:
                chat_history_empty.add_user_message(h["content"])

    answer = chatbot.generate_response(
        state.chat_manager,
        question,
        chat_history_empty,
        False,
        state.rag_params,
        state.lm_instr,
        state.context_instr,
    )
    return answer["answer"]


def create_gauge(value):
    """Create the GUI Guage"""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": "Overall Correctness Score", "font": {"size": 42}},
            # Add the '%' suffix here
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "blue"},
                "steps": [
                    {"range": [0, 30], "color": "red"},
                    {"range": [30, 70], "color": "yellow"},
                    {"range": [70, 100], "color": "green"},
                ],
                "threshold": {
                    "line": {"color": "blue", "width": 4},
                    "thickness": 0.75,
                    "value": 95,
                },
            },
        )
    )
    return fig


def write_test_set(file):
    """Create a local copy of the Test Set"""
    with open(file, "w", encoding="utf-8") as f:
        # Don't write rows clicked to Hide
        test_set = state.test_set_edited[~state.test_set_edited["hide"]]
        # Don't write the "hide" column
        test_set = test_set.drop(columns=["hide"])
        for record in test_set.reset_index().to_dict(orient="records"):
            if "metadata" in record and isinstance(record["metadata"], str):
                record["metadata"] = json.loads(record["metadata"].replace("'", '"'))
            f.write(json.dumps(record) + "\n")


# Prevent Page Re-Load
@st.fragment()
def download_file(file_name, helper):
    """Download Files"""
    if file_name and os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as read_file:
            st.download_button(label=helper, file_name=os.path.basename(file_name), data=read_file)


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    css = """
    <style>
        div[data-testid="column"] {
            width: fit-content !important;
            flex: unset;
        }
        div[data-testid="column"] * {
            width: fit-content !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    st.title("Test Framework")
    try:
        lm_model = st_common.lm_sidebar()
    except ValueError:
        st.error(
            "No models are configured and/or enabled.",
            icon="🚨",
        )
        st.stop()
    # Used to clear the uploader files
    if "test_uploader_key" not in state:
        state.test_uploader_key = 0

    st.header("Q&A Test Set")
    st.write("You can upload an existing Test Set (default), or Generate a new Test Set.")
    st.toggle("Generate a New Test Dataset", key="toggle_generate_test", value=False, on_change=reset_test_set)

    ###################################
    # Create or Load Tests
    ###################################
    # Init and empty Test Set if not defined
    st_common.set_default_state("test_set", None)
    st_common.set_default_state("temp_dir", None)

    # TO CHECK
    # file_path = "temp_file.csv"
    # if os.path.exists(file_path):
    #    os.remove(file_path)

    if state.toggle_generate_test:
        ###### TEST DATASET GENERATION ######
        qa_gen_file = st.file_uploader(
            (
                "Select a local PDF file to build a temporary Knowledge Base. "
                "It will be used to generate a synthetic Q&A pair testing dataset."
            ),
            key=f"uploader_{state.test_uploader_key}",
            accept_multiple_files=False,
            type="pdf",
        )
        qa_gen_button_disabled = True
        if qa_gen_file:
            qa_gen_button_disabled = False
        qa_count = st.number_input("Number of Q&A to Generate:", key="qa_count", min_value=0, max_value=100, value=2)

        left, right = st.columns(2, vertical_alignment="bottom")
        if left.button("Generate Q&A", type="primary", key="qa_generation", disabled=qa_gen_button_disabled):
            placeholder = st.empty()
            with placeholder:
                st.info("Starting Q&A generation... please be patient.", icon="⚠️")
            # Write file to unique temporary directory
            eval_file = split.write_files([qa_gen_file])[0]
            file_name = os.path.basename(eval_file)
            state.temp_dir = os.path.dirname(eval_file)

            # Load and Split
            tn_file = os.path.join(state["temp_dir"], f"{file_name}_{str(qa_count)}_text_nodes.pkl")
            text_nodes = test_framework.load_and_split(eval_file, tn_file)

            # Build Knowlege Base
            kb_file = os.path.join(state["temp_dir"], f"{file_name}_{str(qa_count)}_knowledge_base.json")
            kb = test_framework.build_knowledge_base(text_nodes, kb_file)

            # Generate Q&A
            qa_file = os.path.join(state["temp_dir"], f"{file_name}_{str(qa_count)}_test_set.json")
            state.qa_file = qa_file
            state.test_set = test_framework.generate_qa(qa_file, kb, qa_count)
            placeholder.empty()
            st.success("Q&A Generation Succeeded.", icon="✅")
        right.button("Reset", key="reset_test_framework", type="primary", on_click=reset_test_set)

    if not state.toggle_generate_test:
        ###### TEST LOAD EXISTING ######

        test_set_file = st.file_uploader(
            "Select a local, existing Q&A pair testing dataset:",
            key=f"uploader_{state.test_uploader_key}",
            accept_multiple_files=True,
            type=["json", "jsonl"],
        )
        test_set_button_disabled = True
        if len(test_set_file) > 0:
            test_set_button_disabled = False

        left, right = st.columns(2, vertical_alignment="bottom")
        if left.button("Load Tests", key="load_tests", disabled=test_set_button_disabled):
            placeholder = st.empty()
            with placeholder:
                st.info("Loading Test Sets... please be patient.", icon="⚠️")
            qa_files = split.write_files(test_set_file)
            state.temp_dir = os.path.dirname(qa_files[0])
            logger.info("Temp dir created with Generate Q&A: " + state.temp_dir)
            merged_test_file = test_framework.merge_jsonl_files(qa_files, state["temp_dir"])
            state.merged_test_file = merged_test_file
            state.test_set = QATestset.load(merged_test_file)

            with placeholder:
                st.success("Test Sets Loaded.", icon="✅")
            placeholder.empty()
        right.button("Reset", key="reset_test_framework", type="primary", on_click=reset_test_set)

    ###################################
    # Run Tests
    ###################################
    if state["test_set"] and state["temp_dir"]:
        # Initialise RAG
        st_common.initialise_rag()

        # RAG
        st_common.rag_sidebar()

        # Save
        st_common.save_settings_sidebar()

        # Load Test data in Panda Dataframe

        if not state.toggle_generate_test:
            logger.info("LOAD MERGED FILE")
            st.session_state.test_set_edited = pd.read_json(state["merged_test_file"], orient="records", lines=True)
        else:
            logger.info("LOAD FILE GENERATED")
            st.session_state.test_set_edited = pd.read_json(state["qa_file"], orient="records", lines=True)

        # state["test_set_report"] = state["test_set"].to_pandas()

        st.session_state.test_set_edited["hide"] = False
        cols = st.session_state.test_set_edited.columns.tolist()
        cols = ["hide"] + [col for col in cols if col != "hide"]
        st.session_state.test_set_edited = st.session_state.test_set_edited[cols]

        logger.info("st.session_state.test_set_edited columns:")
        logger.info(st.session_state.test_set_edited.columns)

        # EDIT DATASET
        # state["test_set_edited"] = st.data_editor(state["test_set_report"], hide_index=True, height=250)

        ### Record one-by-one
        report_utils.record_update()
        # Write Edited Test Set and offer Download
        edited_test_file = os.path.join(state["temp_dir"], "edited_test_set.json")
        new_test_dataset = report_utils.clean_hide(edited_test_file)
        download_file(new_test_dataset, "Download Q&A Test Set")

        #################
        # Evaluator
        #################
        st.header("Q&A Evaluation")
        if not state.rag_params["enable"] or all(
            state.rag_params[key] for key in ["model", "chunk_size", "chunk_overlap", "distance_metric"]
        ):
            try:
                chat_cmd = st_common.initialise_chatbot(lm_model)
                state.chat_manager = chat_cmd
                state.initialised = True
                st_common.update_rag()
            except Exception as ex:
                logger.exception(ex, exc_info=False)
                st.error(f"Failed to initialise the chat client: {ex}")
                st_common.clear_initialised()
                if st.button("Retry", key="retry_initialise"):
                    st.rerun()
                st.stop()

        if "chat_manager" in state:
            if st.button("Start Evaluation", type="primary", key="evaluate_button"):
                placeholder = st.empty()
                with placeholder:
                    st.info("Starting Q&A evaluation... please be patient.", icon="⚠️")

                # Run Evaluation
                logger.info("state.test_set = QATestset.load(edited_test_file): " + edited_test_file)

                clean_test_file = report_utils.clean_hide(edited_test_file)
                state.test_set = QATestset.load(clean_test_file)

                report = evaluate(get_answer_fn, testset=state.test_set)
                report_df = report.to_pandas()

                report_df.to_json(os.path.join(state["temp_dir"], "eval_report.json"))
                logger.info("Metrics %s", report._metrics_results)
                by_topic = report.correctness_by_topic()

                # report.failures
                report_file = os.path.join(state["temp_dir"], "eval_report.pkl")
                test_framework.dump_pickle(report_file)
                logger.info("Report generated and saved")
                placeholder.empty()
                with placeholder:
                    st.success("Q&A Completed.", icon="✅")

                st.title("RAG evaluation")

                gauge_fig = create_gauge(report.correctness * 100)
                # Display gauge
                st.plotly_chart(gauge_fig)

                # ADDITIONAL
                # Correctness on each topic of the Knowledge Base
                logger.info("REPORT report.correctness_by_topic(): %s", report.correctness_by_topic())
                by_topic = report.correctness_by_topic()
                logger.info("by_topic: %s", type(by_topic))
                st.subheader("By topic")
                st.dataframe(by_topic)

                # Correctness on each type of question
                logger.info(
                    "report.correctness_by_question_type %s",
                    report.correctness_by_question_type(),
                )
                # get all the failed questions
                logger.info("report.failures %s", report.failures)
                st.subheader("Failures")
                st.dataframe(report.failures, hide_index=True)

                # get the failed questions filtered by topic and question type
                results = report.to_pandas()
                logger.info("report.correctness  :%s", report.correctness)
                st.subheader("Correctness by each Q&A")
                st.dataframe(results, hide_index=True)
                placeholder.empty()
                html_report_orig = os.path.join(state["temp_dir"], "rag_eval_report_orig.html")
                report.to_html(html_report_orig)
                html_report = os.path.join(state["temp_dir"], "rag_eval_report.html")
                report_utils.clean(html_report_orig, html_report)
                download_file(html_report, "Download Report")
                st.button("Reset", key="reset_test_report", type="primary", on_click=reset_test_set)
        else:
            st.error("Not all required RAG options are set, please review or disable RAG.")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
