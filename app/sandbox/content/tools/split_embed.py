import inspect
from content.config.database import db_requires_config

#############################################################################
# MAIN
#############################################################################
def main() -> None:
    """Streamlit GUI"""
    db_requires_config()


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
