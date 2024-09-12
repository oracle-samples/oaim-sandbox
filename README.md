# Oracle AI Microservices Sandbox

🚧 Developer Preview

## Description

The **Oracle AI Microservices Sandbox** provides a streamlined environment where developers and data scientists can explore the potential of Generative Artificial Intelligence (GenAI) combined with Retrieval-Augmented Generation (RAG) capabilities. By integrating the **Oracle Database** for Vector Storage, the Sandbox enables users to enhance existing Large Language Models (LLMs) through RAG. This method significantly improves the performance and accuracy of AI models, helping to avoid common issues such as knowledge cutoff and hallucinations.

## Getting Started

The **Oracle AI Microservices Sandbox** is available to install in your own environment, which may be an developer's desktop, on-premises data center environment, or a cloud provider. It can be run either on a bare-metal, within a container, or in a Kubernetes Cluster.

For more information, including additional information on **Setup and Configuration** please visit the [documentation](https://oracle-samples.github.io/oaim-sandbox)

### Prerequisites

- Oracle Database 23ai incl. Oracle Database 23ai Free
- Python 3.11 (for running Bare-Metal)
- Container Runtime e.g. docker/podman (for running in a Container)
- Access to an Embedding and Chat Model:
  - API Keys for Third-Party Chat Model
  - On-Premises Chat Model

#### Bare-Metal Installation

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

#### Container Installation

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

## Contributing

This project welcomes contributions from the community. Before submitting a pull request, please [review our contribution guide](./CONTRIBUTING.md).

## Security

Please consult the [security guide](./SECURITY.md) for our responsible security vulnerability disclosure process.

## License

Copyright (c) 2024 Oracle and/or its affiliates.
Released under the Universal Permissive License v1.0 as shown at [https://oss.oracle.com/licenses/upl/](https://oss.oracle.com/licenses/upl/)

See [LICENSE](./LICENSE.txt) for more details.
