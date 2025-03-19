# Hands-on-lab Guide

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
