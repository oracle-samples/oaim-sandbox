"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

# spell-checker:ignore genai
import json
import oracledb

from common.schema import Database, DatabaseModel, DatabaseVectorStorage
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.database")


class DbException(Exception):
    """Custom DB Exception"""

    def __init__(self, message):
        super().__init__(message)


def connect(config: DatabaseModel) -> oracledb.Connection:
    """Establish a connection to an Oracle Database"""
    logger.info("Connecting to Database: %s", config.dsn)
    include_fields = set(Database.model_fields.keys())
    db_config = config.model_dump(include=include_fields)
    # Check if connection settings are configured
    if any(not db_config[key] for key in ("user", "password", "dsn")):
        raise DbException("Not all connection details supplied.")

    # Attempt to Connect
    try:
        conn = oracledb.connect(**db_config)
    except oracledb.DatabaseError as ex:
        if "ORA-01017" in str(ex):
            raise DbException("Invalid Credentials") from ex
        else:
            raise DbException(str(ex)) from ex
    return conn


def disconnect(conn: oracledb.Connection) -> None:
    """Establish a connection to an Oracle Database"""
    return conn.close()


def execute_sql(conn: oracledb.Connection, run_sql: str) -> list:
    """Execute SQL against Oracle Database"""
    try:
        # Use context manager to ensure the cursor is closed properly
        with conn.cursor() as cursor:
            cursor.execute(run_sql)
            rows = cursor.fetchall()
            logger.debug("SQL Executed: %s", run_sql)
            return rows

    except oracledb.DatabaseError as ex:
        if ex.args:
            error_obj = ex.args[0]
            if hasattr(error_obj, "code") and error_obj.code == 955:
                logger.info("Table Exists")
            else:
                logger.exception("Database error: %s", ex)
                raise
        else:
            logger.exception("Database error: %s", ex)
            raise

    except oracledb.InterfaceError as ex:
        logger.exception("Interface error: %s", ex)
        raise


def get_vs(conn: oracledb.Connection) -> DatabaseVectorStorage:
    """Retrieve Vector Storage Tables"""
    logger.info("Looking for Vector Storage Tables")
    vector_stores = []
    sql = """SELECT ut.table_name,
                    REPLACE(utc.comments, 'GENAI: ', '') AS comments
                FROM all_tab_comments utc, all_tables ut
                WHERE utc.table_name = ut.table_name
                AND utc.comments LIKE 'GENAI:%'"""
    results = execute_sql(conn, sql)
    for table_name, comments in results:
        comments_dict = json.loads(comments)
        vector_stores.append(DatabaseVectorStorage(vector_store=table_name, **comments_dict))

    return vector_stores