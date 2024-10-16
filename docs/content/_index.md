+++
title = " "
menus = 'main'
archetype = "home"
description = 'AI Microservices Sandbox'
keywords = 'oracle microservices development genai rag'
+++

<!--
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

spell-checker:ignore streamlit, genai, venv, oaim
-->

{{% notice style="code" title="10-Sept-2024: Documentation In-Progress..." icon="pen" %}}
Thank you for your patience as we work on updating the documentation. Please check back soon for the latest updates.
{{% /notice %}}

The **Oracle AI Microservices Sandbox** (the **Sandbox**) provides a streamlined environment where developers and data scientists can explore the potential of Generative Artificial Intelligence (**GenAI**) combined with Retrieval-Augmented Generation (**RAG**) capabilities. By integrating the Oracle Database AI Vector Search, the **Sandbox** enables users to enhance existing Large Language Models (**LLM**s) through **RAG**. This method significantly improves the performance and accuracy of AI models, helping to avoid common issues such as knowledge cutoff and hallucinations.

- **GenAI**: Powers the generation of text, images, or other data based on prompts using pre-trained **LLM**s.
- **RAG**: Enhances **LLM**s by retrieving relevant, real-time information from vector storage allowing models to provide up-to-date and accurate responses.
- **Vector Database**: A database, including Oracle Database 23ai, that can natively store and manage vector embeddings and handle the unstructured data they describe, such as documents, images, video, or audio.

## Sandbox Features

- [Configuring Embedding and Chat Models](sandbox/configuration/model_config)
- [Splitting and Embedding Documentation](sandbox/tools/split_embed)
- [Storing Embedded Documents into the Oracle Database](sandbox/tools/split_embed)
- [Modifying System Prompts (Prompt Engineering)](sandbox/tools/prompt_eng)
- [Experimenting with **LLM** Parameters](sandbox/chatbot)
- [Testing Framework on auto-generated or existing Q&A datasets](sandbox/test_framework)

The **Sandbox** streamlines the entire workflow from prototyping to production, making it easier to create and deploy RAG-powered GenAI solutions using the **Oracle Database**.

# Getting Started

The **Sandbox** is available to install in your own environment, which may be a developer's desktop, on-premises data center environment, or a cloud provider. It can be run either on a bare-metal, within a container, or in a Kubernetes Cluster.

{{% notice style="code" title="Prefer a Step-by-Step?" icon="circle-info" %}}
The [Walkthrough](walkthrough) is a great way to familiarize yourself with the Sandbox and its features.
{{% /notice %}}

## Prerequisites

- Oracle Database 23ai incl. Oracle Database 23ai Free
- Python 3.11 (for running Bare-Metal)
- Container Runtime e.g. docker/podman (for running in a Container)
- Access to an Embedding and Chat Model:
  - API Keys for Third-Party Models
  - On-Premises Models<sub>\*</sub>

<sub>\*Oracle recommends running On-Premises Models on hardware with GPUs. For more information, please review the [Infrastructure](infrastructure/) documentation.</sub>

### Bare-Metal Installation

To run the application on bare-metal; download the [source](https://github.com/oracle-samples/oaim-sandbox) and from the top-level directory:

1. Create and activate a Python Virtual Environment:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip3 install --upgrade pip wheel
   ```

1. Install the Python modules:

   ```bash
   pip3 install -r app/requirements.txt
   ```

1. Start Streamlit:

   ```bash
   cd app/src
   streamlit run oaim-sandbox.py --server.port 8501
   ```

1. Navigate to `http://localhost:8501`.

1. [Configure](configuration) the Sandbox.

### Container Installation

{{% notice style="code" title="Same... but Different" icon="circle-info" %}}
Reference to `podman` commands, if applicable to your environment, can be substituted with `docker`.
{{% /notice %}}

To run the application in a container; download the [source](https://github.com/oracle-samples/oaim-sandbox) and from the top-level directory:

1. Build the image.

   From the `app/` directory, build Image:

   ```bash
   podman build -t oaim-sandbox .
   ```

1. Start the Container:

   ```bash
   podman run -p 8501:8501 -it --rm oaim-sandbox
   ```

1. Navigate to `http://localhost:8501`.

1. [Configure](configuration) the Sandbox.

# Need help?

We'd love to hear from you! You can contact us in the
[#oracle-db-microservices](https://oracledevs.slack.com/archives/C06L9CDGR6Z) channel in the
Oracle Developers slack workspace, or [open an issue in GitHub](https://github.com/oracle-samples/oaim-sandbox/issues/new).
