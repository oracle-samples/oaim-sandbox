"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v 1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore giskard testset, ollama, testsets

import os
import json
import tempfile
import pandas as pd

from pypdf import PdfReader
from oracledb import Connection
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

from giskard.llm import set_llm_model, set_embedding_model
from giskard.rag import generate_testset, KnowledgeBase
from giskard.rag.question_generators import simple_questions, complex_questions

import server.databases as databases
import common.schema as schema
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("server.testbed")


def jsonl_to_json_content(content: str) -> json:
    """Convert JSONL content to JSON,"""
    # If the content is in bytes, decode it to a string
    if isinstance(content, bytes):
        content = content.decode("utf-8")

    try:
        parsed_data = json.loads(content)
        return json.dumps(parsed_data)
    except json.JSONDecodeError:
        lines = content.strip().split("\n")

    try:
        parsed_lines = [json.loads(line) for line in lines]
        # If only one JSON object, return it as a dict
        if len(parsed_lines) == 1:
            return json.dumps(parsed_lines[0])
        return json.dumps(parsed_lines)
    except json.JSONDecodeError as ex:
        raise ValueError("Invalid JSONL content") from ex


def create_testset_objects(conn: Connection) -> None:
    """Create table to store Q&A from TestSets"""
    testsets_tbl = """
            CREATE TABLE IF NOT EXISTS testsets (
                tid     RAW(16) DEFAULT SYS_GUID(),
                name    VARCHAR2(255) NOT NULL,
                created TIMESTAMP(9) WITH LOCAL TIME ZONE,
                CONSTRAINT testsets_pk PRIMARY KEY (tid),
                CONSTRAINT testsets_uq UNIQUE (name, created)
            )
        """
    testset_qa_tbl = """
            CREATE TABLE IF NOT EXISTS testset_qa (
                tid      RAW(16) DEFAULT SYS_GUID(),
                qa_data  JSON,
                CONSTRAINT testset_qa_fk FOREIGN KEY (tid) REFERENCES testsets(tid) ON DELETE CASCADE
            )
        """
    evaluation_tbl = """
            CREATE TABLE IF NOT EXISTS evaluation (
                tid                 RAW(16) DEFAULT SYS_GUID(),
                evaluated           TIMESTAMP(9) WITH LOCAL TIME ZONE,
                settings            JSON,
                testset_jsonl       JSON,
                report_details      JSON,
                knowledge_base      JSON,
                knowledge_base_meta JSON,
                agent_answer        JSON,
                metrics_results     JSON,
                CONSTRAINT evaluation_fk FOREIGN KEY (tid) REFERENCES testsets(tid) ON DELETE CASCADE
            )
        """
    logger.info("Creating testsets Table")
    _ = databases.execute_sql(conn, testsets_tbl)
    logger.info("Creating testset_qa Table")
    _ = databases.execute_sql(conn, testset_qa_tbl)
    logger.info("Creating evaluation Table")
    _ = databases.execute_sql(conn, evaluation_tbl)


def get_testsets(conn: Connection) -> list:
    """Get list of TestSets"""
    logger.info("Getting TestSets")
    testsets = []
    sql = "SELECT tid, name, to_char(created) FROM testsets"
    results = databases.execute_sql(conn, sql)
    try:
        testsets = [schema.TestSets(tid=tid.hex(), name=name, created=created) for tid, name, created in results]
    except TypeError:
        create_testset_objects(conn)

    return testsets


def get_testset_qa(conn: Connection, tid: schema.TestSetsIdType) -> list:
    """Get list of TestSet Q&A"""
    logger.info("Getting TestSet Q&A for TID: %s", tid)
    binds = {"tid": tid}
    sql = "SELECT qa_data FROM testset_qa where tid=:tid"
    results = databases.execute_sql(conn, sql, binds)
    qa_data = [qa_data[0] for qa_data in results]
    testset_qa = schema.TestSetQA(qa_data=qa_data)

    return testset_qa


def upsert_qa(
    conn: Connection,
    name: schema.TestSetsNameType,
    created: schema.TestSetDateType,
    json_data: json,
    tid: schema.TestSetsIdType = None,
) -> schema.TestSetsIdType:
    """Upsert Q&A"""
    logger.info("Upsert TestSet: %s - %s", name, created)
    binds = {"name": name, "created": created, "json_array": json_data, "tid": tid}
    plsql = """
        DECLARE
            l_tid      TESTSETS.TID%TYPE := :tid;
            l_name     TESTSETS.NAME%TYPE := :name;
            l_created  TESTSETS.CREATED%TYPE := TO_TIMESTAMP(:created ,'YYYY-MM-DD"T"HH24:MI:SS.FF');
            l_qa_array JSON_ARRAY_T := JSON_ARRAY_T(:json_array);
            l_qa_obj   JSON_OBJECT_T;
            l_qa_str   VARCHAR2(32000);
        BEGIN
            BEGIN
                IF l_tid is NULL THEN
                    SELECT tid into l_tid
                    FROM testsets
                    WHERE created = l_created
                    AND name = l_name;
                ELSE
                    UPDATE testsets SET name = l_name WHERE tid = l_tid;
                END IF;

                DELETE FROM testset_qa WHERE tid = l_tid;
            EXCEPTION WHEN NO_DATA_FOUND THEN
                INSERT INTO TESTSETS (name, created) VALUES (l_name, l_created)
                RETURNING tid INTO l_tid;
            END;
            FOR i IN 0 .. l_qa_array.get_size - 1
            LOOP
                l_qa_obj := TREAT(l_qa_array.get(i) AS json_object_t);
                l_qa_str := l_qa_obj.stringify(); -- Using due to DB Bug
                INSERT INTO testset_qa (tid, qa_data) VALUES (l_tid, l_qa_str);
            END LOOP;
            DBMS_OUTPUT.PUT_LINE(l_tid);
        END;
    """
    logger.debug("Upsert PLSQL: %s", plsql)
    return databases.execute_sql(conn, plsql, binds)


def insert_evaluation(conn, tid, evaluated, settings, report_data):
    """Insert Evaluation Data"""
    logger.info("Insert evaluation; TID: %s", tid)
    binds = {
        "tid": tid,
        "evaluated": evaluated,
        "settings": settings,
        "testset_jsonl": report_data["testset_jsonl"],
        "report_details": report_data["report_details"],
        "knowledge_base": report_data["knowledge_base"],
        "knowledge_base_meta": report_data["knowledge_base_meta"],
        "metrics_results": report_data["metrics_results"],
    }
    plsql = """
        DECLARE
            l_evaluated EVALUATION.EVALUATED%TYPE := TO_TIMESTAMP(:evaluated ,'YYYY-MM-DD"T"HH24:MI:SS.FF');
        BEGIN
            INSERT INTO evaluation (
                tid, evaluated, settings, testset_jsonl, report_details,
                knowledge_base, knowledge_base_meta, metrics_results
            VALUES (
                :tid, l_evaluated, :settings, :testset_jsonl, :report_details,
                :knowledge_base, :knowledge_base_meta, :metrics_results
            );
        END;
    """
    logger.debug("Insert PLSQL: %s", plsql)
    databases.execute_sql(conn, plsql, binds)


def load_and_split(eval_file, chunk_size=2048):
    """Load and Split Document for Testbed"""
    logger.info("Loading %s; Chunk Size: %i", eval_file, chunk_size)
    loader = PdfReader(eval_file)
    documents = []
    for page in loader.pages:
        document = Document(text=page.extract_text())
        documents.append(document)
    splitter = SentenceSplitter(chunk_size=chunk_size)
    text_nodes = splitter(documents)

    return text_nodes


def build_knowledge_base(text_nodes: str, questions: int, ll_model: schema.Model, embed_model: schema.Model):
    """Establish a temporary Knowledge Base"""

    def configure_and_set_model(client_model):
        """Configure and set Model for TestSet Generation"""
        model_name, params = None, None
        if client_model.api == "OpenAI" or client_model.api == "OpenAIEmbeddings":
            model_name, params = client_model.name, {"api_key": client_model.api_key}
        elif client_model.api == "ChatOllama":
            model_name, params = (
                f"ollama/{client_model.name}",
                {"disable_structured_output": True, "api_base": client_model.url},
            )
        elif client_model.api == "OllamaEmbeddings":
            model_name, params = f"ollama/{client_model.name}", {"api_base": client_model.url}

        if client_model.type == "ll":
            set_llm_model(model_name, **params)
        else:
            set_embedding_model(model_name, **params)

    logger.info("KnowledgeBase creation starting...")
    configure_and_set_model(ll_model)
    configure_and_set_model(embed_model)

    knowledge_base_df = pd.DataFrame([node.text for node in text_nodes], columns=["text"])
    knowledge_base = KnowledgeBase(data=knowledge_base_df)
    logger.info("KnowledgeBase Created")

    logger.info("TestSet from Knowledge Base starting...")
    testset = generate_testset(
        knowledge_base,
        question_generators=[
            simple_questions,
            complex_questions,
        ],
        num_questions=questions,
        agent_description="A chatbot answering questions on a knowledge base",
    )
    logger.info("Test Set from Knowledge Base Generated")

    return testset


def process_report(action, temp_dir):
    """Process an evaluate report"""
    files = {
        "testset.jsonl": "testset_jsonl",
        "report_details.json": "report_details",
        "knowledge_base.jsonl": "knowledge_base",
        "knowledge_base_meta.json": "knowledge_base_meta",
        "metrics_results.json": "metrics_results",
    }
    if action == "save":
        logger.info("Saved Evaluation Report")
        data = {}
        for file_name, var_name in files.items():
            file_path = os.path.join(temp_dir, file_name)
            with open(file_path, "r", encoding="utf-8") as file:
                data[var_name] = json.load(file)
    if action == "load":
        pass

    return data
