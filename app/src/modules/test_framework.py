"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v 1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import os
import pickle

import pandas as pd

from pypdf import PdfReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document

import giskard
from giskard.rag import KnowledgeBase, generate_testset
from giskard.llm.client.openai import OpenAIClient
from giskard.rag.question_generators import (
    complex_questions,
    simple_questions,
)

# History

import modules.logging_config as logging_config

logger = logging_config.logging.getLogger("modules.test_framework")

os.environ["GSK_DISABLE_SENTRY"] = "true"
os.environ["GSK_DISABLE_ANALYTICS"] = "true"


def dump_pickle(cucumber):
    """Dump pickle to file"""
    with open(cucumber, "wb") as file:
        pickle.dump(cucumber, file)
    logger.info("Dumped %s", cucumber)


def load_and_split(eval_file, tn_file, chunk_size=2048):
    """Load and Split Document"""
    logger.info("Loading %s; Chunk Size: %i", eval_file, chunk_size)
    loader = PdfReader(eval_file)
    documents = []
    for page in loader.pages:
        document = Document(text=page.extract_text())
        documents.append(document)
    splitter = SentenceSplitter(chunk_size=chunk_size)
    text_nodes = splitter(documents)
    logger.info("Writing: %s", tn_file)
    dump_pickle(tn_file)

    return text_nodes


def build_knowledge_base(text_nodes, kb_file, model="gpt-4o-mini"):
    """Establish a temporary Knowlege Base"""
    logger.info("KnowledgeBase creation starting..")
    knowledge_base_df = pd.DataFrame([node.text for node in text_nodes], columns=["text"])
    knowledge_base_df.to_json(
        kb_file,
        orient="records",
    )
    knowledge_base = KnowledgeBase(knowledge_base_df, llm_client=OpenAIClient(model=model))
    logger.info("KnowledgeBase created and saved: %s", kb_file)

    return knowledge_base


def generate_qa(qa_file, kb, qa_count, api="openai", model="gpt-4o-mini"):
    """Generate an example QA"""
    logger.info("QA Generation starting..")
    giskard.llm.set_llm_api(api)
    giskard.llm.set_default_client(OpenAIClient(model=model))

    test_set = generate_testset(
        kb,
        question_generators=[simple_questions, complex_questions],
        num_questions=qa_count,
        agent_description="A chatbot answering questions on a knowledge base",
    )
    test_set.save(qa_file)
    logger.info("QA created and saved: %s", qa_file)

    return test_set


def merge_jsonl_files(file_list, temp_dir):
    """Take Uploaded QA files and merge into a single one"""
    output_file = os.path.join(temp_dir, "merged_dataset.jsonl")
    logger.info("Writing test set file: %s", output_file)
    with open(output_file, "w", encoding="utf-8") as outfile:
        for input_file in file_list:
            logger.info("Processing: %s", input_file)
            with open(input_file, "r", encoding="utf-8") as infile:
                for line in infile:
                    outfile.write(line)

    logger.info("De-duplicating: %s", output_file)
    df = pd.read_json(output_file, lines=True)
    duplicate_ids = df[df.duplicated("id", keep=False)]
    if not duplicate_ids.empty:
        # Remove duplicates, keeping the first occurrence
        df = df.drop_duplicates(subset="id", keep="first")
    df.to_json(output_file, orient="records", lines=True)
    logger.info("Wrote test set file: %s", output_file)

    return output_file
