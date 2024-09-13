+++
title = 'Model Configuration'
date = 2024-09-11T07:30:34Z
draft = false
+++

{{< hint type=[warning] icon=gdoc_fire title="10-Sept-2024: Documentation In-Progress..." >}}
Thank you for your patience as we work on updating the documentation. Please check back soon for the latest updates.{{< /hint >}}

## Supported Models

At a minimum, a Large Language Model (LLM) must be configured in **Oracle AI Microservices Sandbox** for basic functionality. For Retrieval-Augmented Generation (RAG), an embedding model will also need to be configured.

{{< hint type=[note] icon=gdoc_info_outline title="Additional Model Support" >}}
If there is a specific model that you would like to use with the **Oracle AI Microservices Sandbox**, please [open an issue in GitHub](https://github.com/oracle-samples/oaim-sandbox/issues/new).{{< /hint >}}

| Model                          | Type  | API                                           | On-Premises |
| ------------------------------ | ----- | --------------------------------------------- | ----------- |
| llama3.1                       | LLM   | [ChatOllama](#additional-information)         | X           |
| gpt-3.5-turbo                  | LLM   | [OpenAI](#additional-information)             |             |
| gpt-4o-mini                    | LLM   | [OpenAI](#additional-information)             |             |
| gpt-4                          | LLM   | [OpenAI](#additional-information)             |             |
| gpt-4o                         | LLM   | [OpenAI](#additional-information)             |             |
| llama-3-sonar-small-32k-chat   | LLM   | [ChatPerplexity](#additional-information)     |             |
| llama-3-sonar-small-32k-online | LLM   | [ChatPerplexity](#additional-information)     |             |
| mxbai-embed-large              | Embed | [OllamaEmbeddings](#additional-information)   | X           |
| nomic-embed-text               | Embed | [OllamaEmbeddings](#additional-information)   | X           |
| all-minilm                     | Embed | [OllamaEmbeddings](#additional-information)   | X           |
| thenlper/gte-base              | Embed | [HuggingFaceEndpointEmbeddings](#additional-information) | X|
| text-embedding-3-small         | Embed | [OpenAIEmbeddings](#additional-information)   |             |
| text-embedding-3-large         | Embed | [OpenAIEmbeddings](#additional-information)   |             |

## Configuration

To configure an LLM from the Sandbox, navigate to `Configuration -> Models`:

## Additional Information
{{< tabs "uniqueid" >}}
{{< tab "Ollama" >}}
# Ollama 
[Ollama](https://ollama.com/) is an open-source project that simplifies the running of LLMs and Embedding Models On-Premises.

When configuring an Ollama model in the Sandbox, set the `API Server` URL (e.g `http://127.0.0.1:11434`) and leave the API Key blank. Substitute the IP Address with IP of where Ollama is running.

{{< hint type=[tip] icon=gdoc_fire title="Auto Setup/Enable" >}}
You can set the following environment variable to automatically set the `API Server` URL and enable Ollama models (change the IP address as required):

```shell
export ON_PREM_OLLAMA_URL=http://127.0.0.1:11434
```

{{< /hint >}}

## Quickstart

Example of running llama3.1 on a Linux host:

1. Install Ollama:

```shell
sudo curl -fsSL https://ollama.com/install.sh | sh
```

1. Pull the llama3.1 model:

```shell
ollama pull llama3.1
```

1. Start Ollama

```shell
ollama serve
```

For more information and instructions on running Ollama on other platforms, please visit the [Ollama GitHub Repository](https://github.com/ollama/ollama/blob/main/README.md#quickstart).

{{< /tab >}}
{{< tab "HuggingFace" >}} 
# HuggingFace

[HuggingFace](https://huggingface.co/) is a platform where the machine learning community collaborates on models, datasets, and applications. It provides a large selection of models that can be run both in the cloud and On-Premises.

{{< hint type=[tip] icon=gdoc_fire title="Auto Setup/Enable" >}}
You can set the following environment variable to automatically set the `API Server` URL and enable HuggingFace models (change the IP address as required):

```shell
export ON_PREM_HF_URL=http://127.0.0.1:8080
```

{{< /hint >}}

## Quickstart

Example of running thenlper/gte-base in a container:

1. Set the Model based on CPU or GPU

   For CPUs: `export HF_IMAGE=ghcr.io/huggingface/text-embeddings-inference:cpu-1.2`
   For GPUs: `export HF_IMAGE=ghcr.io/huggingface/text-embeddings-inference:0.6`

1. Define a Temporary Volume

   ```bash
   export TMP_VOLUME=/tmp/hf_data
   mkdir -p $TMP_VOLUME
   ```

1. Define the Model

   ```bash
   export HF_MODEL=thenlper/gte-base
   ```

1. Start the Container

   ```bash
   podman run -d -p 8080:80 -v $TMP_VOLUME:/data --name hftei-gte-base \
       --pull always ${image} --model-id $HF_MODEL --max-client-batch-size 5024
   ```

1. Determine the IP

   ```bash
   docker inspect hftei-gte-base | grep IPA
   ```

   **NOTE:** if there is no IP, use 127.0.0.1 
{{< /tab >}}
{{< tab "OpenAI" >}}
# OpenAI

[OpenAI](https://openai.com/api/) is an AI research organization behind the popular, online ChatGPT chatbot. To use OpenAI models, you will need to sign-up, purchase credits, and provide the Sandbox an API Key.

**NOTE:** OpenAI is a cloud model and you should familiarize yourself with their Privacy Policies if using it to experiment with private, sensitive data in the Sandbox.

{{< hint type=[tip] icon=gdoc_fire title="Auto Setup/Enable" >}}
You can set the following environment variable to automatically set the `API Key` and enable OpenAI models:

```shell
export OPENAI_API_KEY=<super-secret API Key>
```
{{< /hint >}}
{{< /tab >}}
{{< tab "Perplexity AI" >}}
# Perplexity AI

[Perplexity AI](https://docs.perplexity.ai/getting-started) is an AI-powered answer engine. To use Perplexity AI models, you will need to sign-up, purchase credits, and provide the Sandbox an API Key.

**NOTE:** Perplexity AI is a cloud model and you should familiarize yourself with their Privacy Policies if using it to experiment with private, sensitive data in the Sandbox.

{{< hint type=[tip] icon=gdoc_fire title="Auto Setup/Enable" >}}
You can set the following environment variable to automatically set the `API Key` and enable Perplexity models:

```shell
export PPLX_API_KEY=<super-secret API Key>
```

{{< /hint >}}
{{< /tab >}}
{{< /tabs >}}
