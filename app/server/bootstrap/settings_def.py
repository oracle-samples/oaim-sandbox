"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""


def main() -> list[dict]:
    """Define example Model Support"""
    settings_list = [
        {
            "client": "default",
            "database": "DEFAULT",
            "prompts": {
                "ctx": "Basic Example",
                "sys": "Basic Example"
            },
            "rag": {
                "enabled": False
            }
        },
        {
            "client": "server",
            "database": "DEFAULT",
            "prompts": {
                "ctx": "Basic Example",
                "sys": "Basic Example"
            },
            "rag": {
                "enabled": False
            }
        },
    ]
    return settings_list


if __name__ == "__main__":
    main()
