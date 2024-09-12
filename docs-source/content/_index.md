+++
title = 'Getting Started'
date = 2024-09-10T10:48:24Z
description = 'AI Microservices Sandbox'
keywords = 'oracle microservices development genai rag'
draft = false
geekdocBreadcrumb = false
+++

{{< hint type=[warning] icon=gdoc_fire title="10-Sept-2024: Documentation In-Progress..." >}}
Thank you for your patience as we work on updating the documentation. Please check back soon for the latest updates.{{< /hint >}}

The **Oracle AI Microservices Sandbox** provides a streamlined environment where developers and data scientists can explore the potential of Generative Artificial Intelligence (GenAI) combined with Retrieval-Augmented Generation (RAG) capabilities. By integrating the **Oracle Database** for Vector Storage, the Sandbox enables users to enhance existing Large Language Models (LLMs) through RAG. This method significantly improves the performance and accuracy of AI models, helping to avoid common issues such as knowledge cutoff and hallucinations.

Main Features:

- Configuring Embedding and Chat Models
- Splitting and Embedding Documentation
- Storing Embedded Documents into the Oracle Database
- Modifying System Prompts
- Experimenting with Large Language Model (LLM) Parameters

The **Oracle AI Microservices Sandbox** streamlines the entire workflow from prototyping to production, making it easier to create and deploy RAG-powered GenAI solutions using the **Oracle Database**.

# Getting Started

The **Oracle AI Microservices Sandbox** is available to install in your own environment, which may be an developer's desktop, on-premises data center environment, or a cloud provider. It can be run either on a bare-metal, within a container, or in a Kubernetes Cluster.

## Prerequisites

- Oracle Database 23ai incl. Oracle Database 23ai Free
- Python 3.11 (for running Bare-Metal)
- Container Runtime e.g. docker/podman (for running in a Container)
- Access to an Embedding and Chat Model:
  - API Keys for Third-Party Chat Model
  - On-Premises Chat Model

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

1. Complete the [Walkthrough](walkthrough/) to get familiar with the Sandbox.

### Container Installation

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

1. Complete the [Walkthrough](walkthrough/) to get familiar with the Sandbox.

# Need help?

We'd love to hear from you! You can contact us in the
[#oracle-db-microservices](https://oracledevs.slack.com/archives/C06L9CDGR6Z) channel in the
Oracle Developers slack workspace, or [open an issue in GitHub](https://github.com/oracle-samples/oaim-sandbox/issues/new).
