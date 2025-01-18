"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import os
import server.databases as databases
import server.embedding as embedding
from common.schema import Database


def main() -> list[Database]:
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
    for db in database_list:
        if db["name"] in unique_entries:
            raise ValueError(f"Database '{db['name']}' already exists.")
        unique_entries.add(db["name"])

    # Validate Configuration and set vector_stores/status
    database_objects = []
    for database_obj in database_list:
        db = Database(**database_obj)
        database_objects.append(db)
        try:
            conn = databases.connect(db)
            db.connected = True
        except databases.DbException:
            db.connected = False
            continue
        db.vector_stores = embedding.get_vs(conn)
        if not db.connection and len(database_objects) > 1:
            db.set_connection = databases.disconnect(conn)
        else:
            db.set_connection(conn)

    return database_objects


if __name__ == "__main__":
    main()
