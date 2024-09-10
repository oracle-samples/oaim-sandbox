+++
title = 'Configuration'
date = 2024-09-10T13:57:37Z
draft = true
+++

The **Oracle AI Microservices Sandbox** is not configured out-of-the-box. To enable functionality, an embedding model, language model, database, and optionally, Oracle Cloud Infrastructure (OCI) will need to be configured.

Once you have configured the Sandbox, the settings can be exported and re-imported after an application restart.

# Model Configuration

At a minimum, a large language model (LLM) will need to be configured to experiment with the **Oracle AI Microservices Sandbox**. The LLM can be a third-party LLM, such as ChatGPT or Perplexity, or an on-premises LLM. _If you are experimenting with sensitive, private data_, it is recommended to run both the embedding and LLM on-premises.

For more information on the currently supported models and how to configure them, please read the [Model Configuration](model/)

# Database Configuration

A 23ai Oracle Database is required to store the embedding vectors to enable Retrieval-Augmented Generation (RAG). The ChatBot can be used without the database configuration, but you will be unable to split/embed or experiment with RAG in the ChatBot.

For more information on configuring the database, please read the [Database Configuration](database/)

# OCI Configuration (Optional)

Oracle Cloud Infrastructure (OCI) Object Storage buckets can be used to store documents for embedding. OCI Object Storage can also be used to store the split documents before inserting them in the Oracle Database Vector Store.

For more information on configuring OCI, please read the [OCI Configuration](oci/)

# Import Settings
