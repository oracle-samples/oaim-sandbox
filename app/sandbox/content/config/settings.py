"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import inspect
import streamlit as st
from streamlit import session_state as state


#############################################################################
# MAIN
#############################################################################
def main() -> None:
    """Streamlit GUI"""
    st.write(state)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
