"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore

import oracledb
from common.schema import Database
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.database")


def connect(config: dict, test: bool = False) -> oracledb.Connection:
    """Establish a connection to an Oracle Database"""
    include_fields = set(Database.model_fields.keys())
    db_config = config.model_dump(include=include_fields)
    logger.debug("Attempting DB Connection: %s", db_config)
    conn = oracledb.connect(**db_config)
    if test:
        conn.close()
    return conn


def execute_sql(config: dict, run_sql: str) -> list:
    """Execute SQL against Oracle Database"""
    try:
        conn = connect(config)
        cursor = conn.cursor()
        cursor.execute(run_sql)
        rows = cursor.fetchall()
        logger.debug("SQL Executed: %s", run_sql)
        return rows
    except oracledb.DatabaseError as ex:
        if ex.args and len(ex.args) > 0:
            error_obj = ex.args[0]
            if (
                # ORA-00955: name is already used by an existing object
                hasattr(error_obj, "code") and error_obj.code == 955
            ):
                logger.info("Table Exists")
        else:
            logger.exception(ex, exc_info=False)
            raise
    finally:
        cursor.close()
