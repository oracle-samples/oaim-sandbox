"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

from streamlit.testing.v1 import AppTest


def test_initialise_streamlit():
    """Initialise"""
    at = AppTest.from_file("content/prompt_eng.py", default_timeout=30).run()
    assert at.session_state.lm_instr is not None
    assert at.session_state.context_instr is not None


def test_main_lm():
    """Main LM Prompt"""
    at = AppTest.from_file("content/prompt_eng.py", default_timeout=30).run()
    assert at.session_state.lm_instr != "Testing"
    at.text_area(key="text_area_lm_instr").set_value("Testing    is fun").run()
    at.button[0].click().run()
    assert at.session_state.lm_instr == "Testing is fun"
    assert at.success[0].icon == "✅", "Engineered Prompt Saved"


def test_main_context():
    """Main Context Prompt"""
    at = AppTest.from_file("content/prompt_eng.py", default_timeout=30).run()
    assert at.session_state.context_instr != "Testing"
    at.text_area(key="text_area_context_instr").set_value("Testing    is fun").run()
    at.button[1].click().run()
    assert at.session_state.context_instr == "Testing is fun"
    assert at.success[0].icon == "✅", "Contextualize Prompt Saved"
