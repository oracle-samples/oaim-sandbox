# Hands-on-lab Guide

* install DB:

```bash
podman run -d --name db23ai -p 1521:1521 container-registry.oracle.com/database/free:latest
```

* start DB: 
```bash
colima start x64
```

* install ollama

* start ollama

* install llama3.1:
```bash
podman exec -it ollama ollama pull llama3.1
```

* install embeddings:
```bash
podman exec -it ollama ollama pull mxbai-embed-large
```

* Install requirements:
  ```bash
    python3.11 -m venv .venv
    source .venv/bin/activate
    pip3 install --upgrade pip wheel
    pip3 install -r src/requirements.txt
  ```

* Update server.sh, sandbox.sh

* In two separate shells:

    * terminal 1:
    ```bash
    <home_dir>source ./server.sh
    ```
    * terminal 2:
    ```bash
    <home_dir>source ./sandbox.sh
    ```
