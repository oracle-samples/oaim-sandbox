"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import os


def main() -> list[dict]:
    """Define Default Database"""
    database_list = [
        {
            "name": "DEFAULT",
            "user": os.environ.get("DB_USERNAME", default=None),
            "password": os.environ.get("DB_PASSWORD", default=None),
            "dsn": os.environ.get("DB_DSN", default=None),
            "wallet_password": os.environ.get("DB_WALLET_PASSWORD", default=None),
            "tns_admin": os.environ.get("TNS_ADMIN", default="tns_admin"),
        },
    ]

    # Check for Duplicates
    unique_entries = set()
    for database in database_list:
        if database["name"] in unique_entries:
            raise ValueError(f"Database '{database['name']}' already exists.")
        unique_entries.add(database["name"])

    return database_list


if __name__ == "__main__":
    main()
