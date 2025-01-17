+++
title = '📚 Split/Embed'
weight = 20
+++

<!--
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
-->

The first phase of building a RAG Chatbot start with the chunking of document base and generation of vector embeddings will be stored into a vector store to be retrieved by vectors distance search and added to the context to answer the question grounded to the information provided.

We choose the freedom to exploit LLMs for embeddings provided by public services like Cohere, OpenAI, and Perplexity, or running on top a GPU compute node managed by the customer and exposed through the open source platform OLLAMA, to avoid sharing data with external services that are beyond full customer control.

From the Split/Embed voice of menu, you’ll access to the ingestion page:

![Split](images/split.png)


The Embedding models available list will depend from the Configuration/Models page.

You’ll define quickly the embedding size, that depends on model type, the overlap size, the distance metrics adopted and availble in the Oracle DB 23ai that will play the role as vector store.

The Load and Split Documents part of Split/Embed form will allow to choose documents (txt,pdf,html,etc.) stored on the Object Storage service available on the Oracle Cloud Infrastructure, on the client’s desktop or getting from URLs, like shown in following snapshot:

![Embed](images/embed.png)

It will be created a “speaking” table, like the TEXT_EMBEDDING_3_SMALL_8191_1639_COSINE in the example. You could create on the same documents set several options of vector store, since nobody normally knows which is the best chunking size, and test them indipendently. 

