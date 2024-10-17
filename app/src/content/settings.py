"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script allows importing/exporting configurations using Streamlit (`st`).
"""
# spell-checker:ignore streamlit

import inspect
import json
import copy

# Streamlit
import streamlit as st
from streamlit import session_state as state

# Utilities
import modules.logging_config as logging_config

logger = logging_config.logging.getLogger("settings")


#############################################################################
# Functions
#############################################################################
def compare_dicts_recursive(current, uploaded):
    """Recursively Compare the Session State with the Uploaded Settings"""
    diff = {}
    all_keys = set(current.keys()).union(set(uploaded.keys()))

    for key in all_keys:
        if isinstance(current.get(key), dict) and isinstance(uploaded.get(key), dict):
            # Recursively compare nested dictionaries
            nested_diff = compare_dicts_recursive(current[key], uploaded[key])
            if nested_diff:
                diff[key] = nested_diff
        elif current.get(key) != uploaded.get(key) and uploaded.get(key) != "":
            # Report differences for non-dict values
            diff[key] = {"current": current.get(key), "uploaded": uploaded.get(key)}

    return diff


# Function to compare session state with uploaded JSON, ignoring extra keys in session state
def compare_with_uploaded_json(current_state, uploaded_json):
    """Compare session state with uploaded JSON, ignoring extra keys in session state"""
    diff = {}

    for key in uploaded_json:
        if key in current_state:
            if isinstance(current_state[key], dict) and isinstance(uploaded_json[key], dict):
                nested_diff = compare_dicts_recursive(current_state[key], uploaded_json[key])
                if nested_diff:
                    diff[key] = nested_diff
            elif current_state[key] != uploaded_json[key]:
                diff[key] = {"current": current_state[key], "uploaded": uploaded_json[key]}

    return diff


def update_session_state_recursive(session_state, updates):
    """Apply settings to the Session State"""
    for key, value in updates.items():
        if value == "" or value is None:
            # Skip empty string values
            continue

        if isinstance(value, dict):
            if key not in session_state:
                session_state[key] = {}
            update_session_state_recursive(session_state[key], value)
        else:
            # Check if the value is different from the current state before updating
            if key not in session_state or session_state[key] != value:
                logger.info("Setting %s to %s", key, value)
                session_state[key] = value


#####################################################
# MAIN
#####################################################
def main():
    """Streamlit GUI"""

    st.header("Import Settings")
    state_dict = copy.deepcopy(state)
    uploaded_file = st.file_uploader("Upload the Settings file", type="json")
    if uploaded_file is not None:
        file_content = uploaded_file.read()

        # Convert the JSON content to a dictionary
        try:
            uploaded_settings_dict = json.loads(file_content)
            differences = compare_with_uploaded_json(state_dict, uploaded_settings_dict)

            # Show differences
            if differences:
                if st.button("Apply New Settings"):
                    # Update session state with values from the uploaded JSON
                    update_session_state_recursive(state, uploaded_settings_dict)
                    st.success("Configuration has been updated with the uploaded settings.", icon="✅")
                    st.rerun()
                st.subheader("Differences found:")
                st.json(differences)
            else:
                st.write("No differences found. The current configuration matches the saved settings.")
        except json.JSONDecodeError:
            st.error("Error: The uploaded file is not a valid.")
    else:
        st.info("Please upload a Settings file.")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
