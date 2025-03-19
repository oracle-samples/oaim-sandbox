# Hands-on-lab Guide

## Set up
In this first step we are going to set up all the required components to run the AI Explorer for Apps.

### Containers runtime engine
We begin by starting our container runtime engine. We will be using Colima here,
and assuming that you are using an Apple Silicon Mac.
Start the container runtime engine.  If you already have a profile that you use, please double-check that it uses 4
CPUs and 8GB of memory.
```bash
colima start --vm-type vz --vz-rosetta --mount-type virtiofs --cpu 4 --memory 8
```

### Install and start Oracle DB 23ai

We are going to use Oracle Database 23ai to take advantage of the vector search feature among other things, so we spin up a container with it. Proceed as describd here: [DB](INSTALL_DB23AI.md)


### LLM runtime
We would like to interact with different LLMs localy and we are going to use Ollama for running them. We are going to use it in if Ollama isn't installed in your system already, you can use brew:

```bash
  brew install ollama
```

You can run Ollama as a service with:
```bash
  brew services start ollama
```

Or, if you don't want/need a background service you can just run:
```bash
  /opt/homebrew/opt/ollama/bin/ollama serve
```

We are going to interact with some LLM models, so we need to install them in Ollama (llama3.1 and mxbai for the embeddings):

```bash
ollama pull llama3.1
ollama pull mxbai-embed-large
```

### Clone the right branch
* Make sure to clone the branch `hol`. In a `<project_dir>` proceed in this way:
```bash
git clone --branch hol --single-branch https://github.com/oracle-samples/oaim-sandbox.git
```

### Install requirements:
  ```bash
    python3.11 -m venv .venv
    source .venv/bin/activate
    pip3 install --upgrade pip wheel
    pip3 install -r src/requirements.txt
  ```

### Startup 
The two scripts `server.sh` and `sandbox.sh` hold env variables needed to connect the DB. If for any reasons do you need to adapt to a different setup, change accordingly.

* In a separate shell:

    ```bash
    <project_dir>source ./server.sh
    ```

and get api-key from logs:
![API-KEY](images/api-key.png)

* set in `sandbox.sh` the server API key:
  ```bash
  export API_SERVER_KEY=<generated_key>
  ```

* in another terminal:
  ```bash
  <project_dir>source ./sandbox.sh
  ```

## Explore the env
In a browser, open the link: `http://localhost:8502/`

* let's check if the DB is correctly connected:

![DB](images/db.png)

* You should see the message: `Current Status: Connected`

* let's check models:

![models menu](images/models.png)

  * LLMs for chat completions must be:

  ![llms](images/llms.png)

  * LLMs for embeddings must be:

  ![embeddings](images/emb.png)
