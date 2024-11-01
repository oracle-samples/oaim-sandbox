"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, iloc

import os
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import modules.logging_config as logging_config

from streamlit import session_state as state

logger = logging_config.logging.getLogger("modules.st_common")


def remove_component_by_title(soup, title):
    component_cards = soup.find_all("div", class_="component-card")
    for card in component_cards:
        title_element = card.find("div", class_="component-title")
        if title_element and title in title_element.text.strip().upper():
            card.decompose()


def clean(file_in="rag_eval_report.html", file_out="rag_eval_report_modified_html.html"):
    with open(file_in, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    titles_to_remove = ["GENERATOR", "RETRIEVER", "REWRITER", "ROUTING", "KNOWLEDGE_BASE", "KNOWLEDGE BASE OVERVIEW"]

    for title in titles_to_remove:
        remove_component_by_title(soup, title)

    with open(file_out, "w", encoding="utf-8") as file:
        file.write(soup.prettify())


def clean_hide(file_path):
    df = pd.read_json(file_path, orient="records", lines=True)

    df = df[df["hide"] == False]
    df = df.drop(columns=["hide"])

    cleaned_file_path = os.path.join(state["temp_dir"], "cleaned_edited_test_set.jsonl")
    df.to_json(cleaned_file_path, orient="records", lines=True)

    return cleaned_file_path


def record_update():
    file_path = os.path.join(state["temp_dir"], "edited_test_set.json")
    if not os.path.exists(file_path):
        state.test_set_edited.to_json(file_path, orient="records", lines=True)

    state.df = pd.read_json(file_path, orient="records", lines=True)
    logger.info(state.df.columns)

    if "index" not in state:
        state.index = 0
    if "hide_input" not in state:
        state.hide_input = state.df.at[state.index, "hide"]
    if "question_input" not in state:
        state.question_input = state.df.iloc[state.index]["question"]
    if "reference_answer_input" not in state:
        state.reference_answer_input = state.df.iloc[state.index]["reference_answer"]
    if "reference_context_input" not in state:
        state.reference_context_input = state.df.iloc[state.index]["reference_context"]
    if "metadata_input" not in state:
        state.metadata_input = state.df.iloc[state.index]["metadata"]

    logger.info("Question:")
    logger.info(state.question_input)
    # Create columns for buttons
    col1, col2, col3, _, _ = st.columns([1, 1, 1, 2, 2])

    # Button to move to the previous question
    with col1:
        if st.button("previous"):
            if state.index > 0:
                # Save the current input value before changing the index
                state.index -= 1
                state.hide_input = state.df.at[state.index, "hide"]
                state.question_input = state.df.at[state.index, "question"]
                state.reference_answer_input = state.df.at[state.index, "reference_answer"]
                state.reference_context_input = state.df.at[state.index, "reference_context"]
                state.metadata_input = state.df.at[state.index, "metadata"]

    # Button to move to the next question
    with col2:
        if st.button("next"):
            if state.index < len(state.df) - 1:
                # Save the current input value before changing the index
                state.index += 1
                state.hide_input = state.df.at[state.index, "hide"]
                state.question_input = state.df.at[state.index, "question"]
                state.reference_answer_input = state.df.at[state.index, "reference_answer"]
                state.reference_context_input = state.df.at[state.index, "reference_context"]
                state.metadata_input = state.df.at[state.index, "metadata"]

    # Button to save the current input value
    with col3:
        save_clicked = st.button("Save")
        if save_clicked:
            # Save the current input value in the DataFrame
            state.df.at[state.index, "hide"] = state.hide_input
            state.df.at[state.index, "question"] = state.question_input
            state.df.at[state.index, "reference_answer"] = state.reference_answer_input
            state.df.at[state.index, "reference_context"] = state.reference_context_input
            # state.df.at[state.index, 'metadata'] = state.metadata_input  # It's read-only
            logger.info("--------SAVE----------------------")

            index = state.df.index[state.index]

            new_data = {
                "hide": state.hide_input,
                "id": state.df.at[state.index, "id"],
                "question": state.question_input,
                "reference_answer": state.reference_answer_input,
                "reference_context": state.reference_context_input,
                "conversation_history": "",
            }
            for key, value in new_data.items():
                state.df.at[index, key] = value
            state.df.to_json(file_path, orient="records", lines=True, index=False)

    # Text input for the question, storing the user's input in the session state
    state.index_output = st.write("Record: " + str(state.index + 1) + "/" + str(state.df.shape[0]))
    state.hide_input = st.checkbox("Hide", value=state.hide_input)
    state.question_input = st.text_area("question", height=1, value=state.question_input)
    state.reference_answer_input = st.text_area("Reference answer", height=1, value=state.reference_answer_input)
    state.reference_context_input = st.text_area(
        "Reference context", height=10, value=state.reference_context_input, disabled=True
    )
    state.metadata_input = st.text_area("Metadata", height=1, value=state.metadata_input, disabled=True)

    if save_clicked:
        st.success("Q&A saved successfully!")

    st.write("Updated DataFrame:")


def clean_dir(temp_dir):
    logger.info("cleaning dir: %s", temp_dir)
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error("Failed to delete %s. Reason: %s", file_path, e)
