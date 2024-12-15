"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

from common.schema import SettingsModel


def main() -> list[dict]:
    """Define example Settings Support"""
    settings_list = [
        {
            "client": "default",
            "prompts": {"ctx": "Basic Example", "sys": "Basic Example"},
            "rag": {"database": "DEFAULT", "rag_enabled": False},
        },
        {
            "client": "server",
            "database": "DEFAULT",
            "prompts": {"ctx": "Basic Example", "sys": "Basic Example"},
            "rag": {"database": "DEFAULT", "rag_enabled": False},
        },
    ]
    settings_objects = [SettingsModel(**settings_dict) for settings_dict in settings_list]
    return settings_objects


if __name__ == "__main__":
    main()
