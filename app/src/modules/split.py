"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

import os
import json
import math
import tempfile
from typing import List
import modules.logging_config as logging_config
import bs4

# Langchain
from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import HTMLSectionSplitter, CharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
import langchain_community.document_loaders as document_loaders

logger = logging_config.logging.getLogger("modules.split")


def write_files(input_files):
    """Write files locally"""
    output_files = []
    temp_dir = tempfile.mkdtemp()
    # Write and Load Document
    for file in input_files:
        temp_file_path = os.path.join(temp_dir, file.name)
        logger.info("Writing Local File %s", temp_file_path)
        with open(temp_file_path, "wb") as f:
            f.write(file.getbuffer())
        output_files.append(temp_file_path)

    return output_files


def doc_to_json(document: LangchainDocument, file: str, output_dir: str = None) -> List:
    """Creates a JSON file of the Document.  Returns the json file destination"""
    src_file_name = os.path.basename(file)
    dst_file_name = "_" + os.path.splitext(src_file_name)[0] + ".json"

    docs_dict = [doc.to_json() for doc in document]
    json_data = json.dumps(docs_dict, indent=4)

    dst_file_path = os.path.join(output_dir, dst_file_name)
    with open(dst_file_path, "w", encoding="utf-8") as file:
        file.write(json_data)
    file_size = os.path.getsize(dst_file_path)
    logger.info("Wrote split JSON file: %s (%i bytes)", dst_file_path, file_size)

    return dst_file_path


def process_metadata(idx, chunk):
    """Add Metadata to Split Document"""
    filename = os.path.basename(chunk.metadata["source"])
    file = os.path.splitext(filename)[0]

    split_doc_with_mdata = []
    chunk_metadata = chunk.metadata.copy()
    # Add More Metadata as Required
    chunk_metadata["id"] = f"{file}_{idx}"
    chunk_metadata["filename"] = filename
    split_doc_with_mdata.append(LangchainDocument(page_content=str(chunk.page_content), metadata=chunk_metadata))
    return split_doc_with_mdata


def split_document(
    model: str,
    chunk_size: int,
    chunk_overlap: int,
    document: List[LangchainDocument],
    extention: str,
) -> List[LangchainDocument]:
    """
    Split documents into chunks of size `chunk_size` characters and return a list of documents.
    """
    ##################################
    # Splitters - Start
    ##################################
    ## Text
    logger.info("Splitting for %s", model)
    chunk_overlap_ceil = math.ceil(chunk_overlap)
    match model:
        case "text-embedding*":
            text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
                separator="\n\n",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap_ceil,
                is_separator_regex=False,
                model_name=model,
                encoding_name=model,
            )
        case _:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap_ceil,
                add_start_index=True,
                strip_whitespace=True,
                length_function=len,
            )
    ## HTML
    headers_to_split_on = [
        ("h1", "Header 1"),
        ("h2", "Header 2"),
        ("h3", "Header 3"),
        ("h4", "Header 4"),
        ("h5", "Header 5"),
    ]
    html_splitter = HTMLSectionSplitter(headers_to_split_on=headers_to_split_on)
    ##################################
    # Splitters - End
    ##################################
    match extention:
        case "pdf":
            doc_split = text_splitter.split_documents(document)
        case "html":
            try:
                html_split = html_splitter.split_documents(document)
            except Exception as ex:
                logger.exception(ex)
                html_split = document
            doc_split = text_splitter.split_documents(html_split)
        case "md":
            doc_split = text_splitter.split_documents(document)
        case "csv":
            doc_split = text_splitter.split_documents(document)

    logger.info("Number of Chunks: %i", len(doc_split))
    return doc_split


##########################################
# Documents
##########################################
def load_and_split_documents(
    src_files: List,
    model: str,
    chunk_size: int,
    chunk_overlap: int,
    write_json: bool = False,
    output_dir: str = None,
) -> List[LangchainDocument]:
    """
    Loads file into a Langchain Document.  Calls the Splitter (split_document) function
    Returns the list of the chunks in a LangchainDocument.
    If output_dir, a list of written json files
    """
    split_files = []
    for file in src_files:
        split_docos = []
        name = os.path.basename(file)
        stat = os.stat(file)
        extension = os.path.splitext(file)[1][1:]
        logger.info("Loading %s (%i bytes)", name, stat.st_size)
        match extension:
            case "pdf":
                loader = document_loaders.PyPDFLoader(file)
            case "html":
                loader = document_loaders.UnstructuredHTMLLoader(file)
            case "md":
                loader = document_loaders.TextLoader(file)
            case "csv":
                loader = document_loaders.CSVLoader(file)
            case _:
                logger.error("Un-supported file extension: %s", extension)

        loaded_doc = loader.load()
        logger.info("Loaded Pages: %i", len(loaded_doc))

        # Chunk the File
        split_doc = split_document(model, chunk_size, chunk_overlap, loaded_doc, extension)

        # Add IDs to metadata
        for idx, chunk in enumerate(split_doc, start=1):
            split_doc_with_mdata = process_metadata(idx, chunk)
            split_docos += split_doc_with_mdata

        if write_json and output_dir:
            split_files += doc_to_json(split_docos, file, output_dir)
    logger.info("Total Number of Chunks: %i", len(split_docos))

    return split_docos, split_files


##########################################
# Web
##########################################
def load_and_split_url(
    model: str,
    url: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[LangchainDocument]:
    """
    Loads URL into a Langchain Document.  Calls the Splitter (split_document) function
    Returns the list of the chunks in a LangchainDocument.
    If output_dir, a list of written json files
    """
    split_docos = []
    split_files = []
    
    logger.info("Loading %s", url)
    loader = WebBaseLoader(
        web_paths=(f"{url}",),
        bs_kwargs=dict(parse_only=bs4.SoupStrainer()),
    )

    loaded_doc = loader.load()
    logger.info("Document Size: %s bytes", str(loaded_doc.__sizeof__()))
    logger.info("Loaded Pages: %i", len(loaded_doc))

    # Chunk the File
    split_doc = split_document(model, chunk_size, chunk_overlap, loaded_doc, "html")

    # Add IDs to metadata
    for idx, chunk in enumerate(split_doc, start=1):
        split_doc_with_mdata = process_metadata(idx, chunk)
        split_docos += split_doc_with_mdata

    logger.info("Total Number of Chunks: %i", len(split_docos))
    if len(split_docos) == 0:
        raise ValueError("Input source contains no chunk-able data.")

    return split_docos, split_files
