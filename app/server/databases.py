"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore genai

import json
import oracledb

from common.schema import Database, DatabaseModel, DatabaseVectorStorage, TestSets
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.database")


class DbException(Exception):
    """Custom Database Exceptions to be passed to HTTPException"""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def connect(config: Database) -> oracledb.Connection:
    """Establish a connection to an Oracle Database"""
    logger.info("Connecting to Database: %s", config.dsn)
    include_fields = set(DatabaseModel.model_fields.keys())
    db_config = config.model_dump(include=include_fields)
    # Check if connection settings are configured
    if any(not db_config[key] for key in ("user", "password", "dsn")):
        raise DbException(status_code=400, detail="Not all connection details supplied.")

    # Attempt to Connect
    try:
        conn = oracledb.connect(**db_config)
    except oracledb.DatabaseError as ex:
        if "ORA-01017" in str(ex):
            raise DbException(status_code=401, detail="Invalid database credentials.") from ex
        else:
            raise DbException(status_code=500, detail=str(ex)) from ex
    return conn


def disconnect(conn: oracledb.Connection) -> None:
    """Establish a connection to an Oracle Database"""
    return conn.close()


def execute_sql(conn: oracledb.Connection, run_sql: str) -> list:
    """Execute SQL against Oracle Database"""
    logger.debug("SQL: %s", run_sql)
    try:
        # Use context manager to ensure the cursor is closed properly
        with conn.cursor() as cursor:
            cursor.execute(run_sql)
            if cursor.description:  # Check if the query returns rows
                rows = cursor.fetchall()
            else:
                rows = None  # No rows to fetch
            return rows
    except oracledb.DatabaseError as ex:
        if ex.args:
            error_obj = ex.args[0]
            if hasattr(error_obj, "code") and error_obj.code == 955:
                logger.info("Table exists")
            if hasattr(error_obj, "code") and error_obj.code == 942:
                logger.info("Table does not exist")
            else:
                logger.exception("Database error: %s", ex)
                logger.info("Failed SQL: %s", run_sql)
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


def drop_vs(conn: oracledb.Connection, vs: DatabaseVectorStorage) -> None:
    """Drop Vector Storage"""
    logger.info("Dropping Vector Store: %s", vs.vector_store)
    sql = f"DROP TABLE {vs.vector_store} PURGE"
    _ = execute_sql(conn, sql)


def create_test_set(conn: oracledb.Connection) -> None:
    logger.info("Creating Test Set Table")
    table_sql = """
            CREATE TABLE IF NOT EXISTS test_sets (
                id          RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
                name        VARCHAR2(255) NOT NULL,
                date_loaded TIMESTAMP (6) WITH TIME ZONE NOT NULL,
                test_set    JSON
            )
        """
    index_sql = """
            CREATE INDEX IF NOT EXISTS test_sets_idx ON test_sets (name, date_loaded)
        """
    _ = execute_sql(conn, table_sql)
    _ = execute_sql(conn, index_sql)


def get_test_set(conn: oracledb.Connection, date_loaded: str = "%", name: str = "%") -> list:
    logger.info("Getting Test Set; Name: %s - Date Loaded: %s", name, date_loaded)
    test_sets = []
    sql = f"""
        SELECT name, to_char(date_loaded, 'YYYY-MM-DD HH24:MI:SS.FF') as date_loaded, test_set
          FROM test_sets
         WHERE to_char(date_loaded, 'YYYY-MM-DD HH24:MI:SS.FF') like '{date_loaded}'
           AND name like '{name}'
        ORDER BY date_loaded desc
      """
    results = execute_sql(conn, sql)
    try:
        for name, date_loaded, test_set in results:
            test_sets.append(TestSets(name=name, date_loaded=date_loaded, test_set=test_set))
    except TypeError as ex:
        logger.exception("Exception raised: %s", ex)
        create_test_set(conn)

    return test_sets
