"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

from bs4 import BeautifulSoup
import streamlit as st
import modules.logging_config as logging_config
import os
import json
from streamlit import session_state as state

logger = logging_config.logging.getLogger("modules.st_common")

def remove_component_by_title(soup, title):
    component_cards = soup.find_all("div", class_="component-card")
    for card in component_cards:
        title_element = card.find("div", class_="component-title")
        if title_element and title in title_element.text.strip().upper():
            card.decompose()


def clean(fileIn="rag_eval_report.html", fileOut="rag_eval_report_modified_html.html"):

    with open(fileIn, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    titles_to_remove = ["GENERATOR", "RETRIEVER", "REWRITER", "ROUTING", "KNOWLEDGE_BASE", "KNOWLEDGE BASE OVERVIEW"]

    for title in titles_to_remove:
        remove_component_by_title(soup, title)

    with open(fileOut, "w", encoding="utf-8") as file:
        file.write(soup.prettify())


def clean_hide(file_path):
    df = pd.read_json(file_path, orient="records",lines=True)

    df = df[df['hide'] == False]
    df = df.drop(columns=['hide'])

    cleaned_file_path = os.path.join(st.session_state["temp_dir"], "cleaned_edited_test_set.json")
    df.to_json(cleaned_file_path, orient="records",lines=True)

    return(cleaned_file_path)


import pandas as pd


def record_update():
  

    file_path = os.path.join(st.session_state["temp_dir"], "edited_test_set.json")
    if not os.path.exists(file_path):
        st.session_state.test_set_edited.to_json(file_path, orient="records",lines=True)

    st.session_state.df = pd.read_json(file_path, orient="records",lines=True)
    logger.info(st.session_state.df.columns)

    if 'index' not in st.session_state:
        st.session_state.index = 0
    if 'hide_input' not in st.session_state:
        st.session_state.hide_input = st.session_state.df.at[st.session_state.index,"hide"]
    if 'question_input' not in st.session_state:
        st.session_state.question_input = st.session_state.df.iloc[st.session_state.index]["question"]
    if 'reference_answer_input' not in st.session_state:
        st.session_state.reference_answer_input = st.session_state.df.iloc[st.session_state.index]["reference_answer"]
    if 'reference_context_input' not in st.session_state:
        st.session_state.reference_context_input = st.session_state.df.iloc[st.session_state.index]["reference_context"]
    if 'metadata_input' not in st.session_state:
        st.session_state.metadata_input = st.session_state.df.iloc[st.session_state.index]["metadata"]

   
    logger.info("Question:")
    logger.info(st.session_state.question_input)
    # Create columns for buttons
    col1, col2, col3, _ , _ = st.columns([1, 1, 1, 2,2])


    # Button to move to the previous question
    with col1:
        if st.button("previous"):
            
            if st.session_state.index > 0:
                # Save the current input value before changing the index
                st.session_state.index -= 1
                st.session_state.hide_input = st.session_state.df.at[st.session_state.index,"hide"]
                st.session_state.question_input = st.session_state.df.at[st.session_state.index,"question"]
                st.session_state.reference_answer_input = st.session_state.df.at[st.session_state.index,"reference_answer"]
                st.session_state.reference_context_input = st.session_state.df.at[st.session_state.index,"reference_context"]
                st.session_state.metadata_input = st.session_state.df.at[st.session_state.index,"metadata"]

    # Button to move to the next question
    with col2:
        if st.button("next"):
            
            if st.session_state.index < len(st.session_state.df) - 1:
                # Save the current input value before changing the index
                st.session_state.index += 1
                st.session_state.hide_input = st.session_state.df.at[st.session_state.index,"hide"]
                st.session_state.question_input = st.session_state.df.at[st.session_state.index,"question"]
                st.session_state.reference_answer_input = st.session_state.df.at[st.session_state.index,"reference_answer"]
                st.session_state.reference_context_input = st.session_state.df.at[st.session_state.index,"reference_context"]
                st.session_state.metadata_input = st.session_state.df.at[st.session_state.index,"metadata"]

    # Button to save the current input value
    with col3:
        save_clicked = st.button("Save")
        if save_clicked:
            # Save the current input value in the DataFrame
            st.session_state.df.at[st.session_state.index, 'hide'] = st.session_state.hide_input
            st.session_state.df.at[st.session_state.index, 'question'] = st.session_state.question_input
            st.session_state.df.at[st.session_state.index, 'reference_answer'] = st.session_state.reference_answer_input
            st.session_state.df.at[st.session_state.index, 'reference_context'] = st.session_state.reference_context_input
            #st.session_state.df.at[st.session_state.index, 'metadata'] = st.session_state.metadata_input  # It's read-only
            logger.info("--------SAVE----------------------")
        
            
            index=st.session_state.df.index[st.session_state.index]


            new_data = {
                    'hide':st.session_state.hide_input,
                    'id':st.session_state.df.at[st.session_state.index, 'id'],
                    'question':st.session_state.question_input,
                    'reference_answer': st.session_state.reference_answer_input,
                    'reference_context': st.session_state.reference_context_input,
                    'conversation_history': ""
            }
            for key, value in new_data.items():
                st.session_state.df.at[index, key] = value
            st.session_state.df.to_json(file_path, orient="records",lines=True, index=False)
            

    # Text input for the question, storing the user's input in the session state
    st.session_state.index_output = st.write("Record: "+str(st.session_state.index+1)+"/"+str(st.session_state.df.shape[0]))
    st.session_state.hide_input = st.checkbox("Hide", value=st.session_state.hide_input)
    st.session_state.question_input = st.text_area("question",  height=1, value=st.session_state.question_input)
    st.session_state.reference_answer_input = st.text_area("Reference answer", height=1,  value=st.session_state.reference_answer_input)
    st.session_state.reference_context_input = st.text_area("Reference context",  height=10, value=st.session_state.reference_context_input,disabled=True)
    st.session_state.metadata_input = st.text_area("Metadata",  height=1, value=st.session_state.metadata_input,disabled=True)

    if save_clicked:
        st.success("Q&A saved successfully!")

    st.write("Updated DataFrame:")
   
def clean_dir(temp_dir):
    logger.info("cleaning dir: "+temp_dir)
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path) 
            except Exception as e:
                logger.error(f"Failed to delete {file_path}. Reason: {e}")