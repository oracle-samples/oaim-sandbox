"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, vectorstore, vectorstorage, llms, filt, mult, rerank, selectbox

import json
import copy
import io
import zipfile
import tempfile
import shutil
import os

# Streamlit
import streamlit as st
from streamlit import session_state as state

# Utilities
import modules.utilities as utilities
import modules.logging_config as logging_config
import modules.metadata as meta
import modules.help as custom_help



from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_cohere import CohereEmbeddings


from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
import getpass
import os,json
import oracledb


logger = logging_config.logging.getLogger("modules.agents_collection")

@tool
def query_entity(entity: str) -> str:
    """Query the entity employee only giving a name as input"""
    #SQL="SELECT * FROM emp WHERE UPPER(ename) = :key"
    #SELECT json_serialize(data PRETTY) FROM department_dv WHERE lower(json_value(data, '$.department_name')) like lower(:key)
    SQL=state.agents_selected["action"]
    result= sql(SQL,entity)
    logger.info("Tool query_entity executed for entity:"+entity)
    logger.info("SQL: "+SQL)
    logger.info(result)
    print(result)
    return result

def sql(query: str, key: str) -> str:
    """TO BE REMOVED IN ACTUAL DISTRIBUTION"""
    un = 'vector'
    cs = 'localhost:1521/FREEPDB1'
    pw = 'vector'
    # query example: "SELECT * FROM emp WHERE UPPER(ename) = :key"
    
    # Connect to Oracle database
    with oracledb.connect(user=un, password=pw, dsn=cs) as connection:
        with connection.cursor() as cursor:
            # Execute the query with parameterized input
            cursor.execute(query, {'key': key.upper()})
            
            # Set up rowfactory before fetching results
            columns = [col[0] for col in cursor.description]
            cursor.rowfactory = lambda *args: dict(zip(columns, args))
            
            # Fetch the first row
            data = cursor.fetchone()
            
            # Return data if found, otherwise a message
            if data:
                return data
            else:
                return "No information found"