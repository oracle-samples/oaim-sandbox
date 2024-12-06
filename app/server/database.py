"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore

import oracledb
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.database")


def connect(config: dict, test: bool = False) -> oracledb.Connection:
    """Establish a connection to an Oracle Database"""
    logger.debug("Attempting DB Connection: %s", config)
    conn = oracledb.connect(**config)
    if test:
        conn.close()
    return conn


def execute_sql(conn, run_sql):
    """Execute SQL against Oracle Database"""
    try:
        cursor = conn.cursor()
        cursor.execute(run_sql)
        logger.info("SQL Executed")
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
