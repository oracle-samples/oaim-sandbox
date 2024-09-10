"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import json
import os
import modules.logging_config as logging_config
import oracledb

logger = logging_config.logging.getLogger("modules.db_utils")


def initialise(user=None, password=None, dsn=None, wallet_password=None):
    """Create the configuration for connecting to an Oracle Database"""
    config = {"user": user, "password": password, "dsn": dsn, "wallet_password": wallet_password}

    # Update with EnvVars if set and not provided
    if not config["user"]:
        config["user"] = os.environ.get("DB_USERNAME", default=None)
    if not config["password"]:
        config["password"] = os.environ.get("DB_PASSWORD", default=None)
    if not config["dsn"]:
        config["dsn"] = os.environ.get("DB_DSN", default=None)
    if not config["wallet_password"]:
        config["wallet_password"] = os.environ.get("DB_WALLET_PASSWORD", default=None)

    # ADB mTLS (this is a default location req. for images; do not change)
    tns_directory = os.environ.get("TNS_ADMIN", default="tns_admin")
    config["config_dir"] = tns_directory
    if "wallet_password" in config and config["wallet_password"] is not None:
        config["wallet_location"] = config["config_dir"]

    logger.debug("Database Configuration: %s", config)
    return config


def connect(config):
    """Estabilish a connection to an Oracle Database"""
    conn = oracledb.connect(**config)
    logger.debug("Database Connection Established")
    return conn


def get_vs_tables(conn):
    """Retrieve Vector Storage Tables"""
    logger.info("Looking for Vector Storage Tables")
    output = {}
    sql = """
        SELECT ut.table_name||':'||REPLACE(utc.comments, 'GENAI: ', '') as jdoc
          FROM user_tab_comments utc, user_tables ut
         WHERE utc.table_name = ut.table_name
           AND utc.comments LIKE 'GENAI:%'"""
    try:
        cursor = conn.cursor()
        logger.debug("Executing SQL: %s", sql)
        for row in cursor.execute(sql):
            row_str = row[0]
            key, value = row_str.split(":", 1)
            value = json.loads(value)
            logger.info("--> Found Table: %s", key)
            output[key] = value
    except oracledb.DatabaseError as ex:
        logger.exception(ex, exc_info=False)
    finally:
        cursor.close()

    return json.dumps(output, indent=4)


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
                hasattr(error_obj, "code")
                and error_obj.code == 955
            ):
                logger.info("Table Exists")
        else:
            logger.exception(ex, exc_info=False)
            raise
    finally:
        cursor.close()
