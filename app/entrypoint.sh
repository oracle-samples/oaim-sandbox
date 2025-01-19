#!/bin/bash
## Copyright (c) 2023, 2024, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

if [ -d /app/server ] && [ -d /app/sandbox ]; then
    echo "Starting Application (Sandbox and Server)"
    exec streamlit run ./oaim_sandbox.py
fi

if [ -d /app/server ] && [ ! -d /app/sandbox ]; then
    echo "Starting Server"
    exec uvicorn oaim_server:app
fi

if [ ! -d /app/server ] && [ -d /app/sandbox ]; then
    echo "Starting Sandbox"
    if [ -z "$API_SERVER_KEY" ] || [ -z "$API_SERVER_URL" ] || [ -z "$API_SERVER_PORT" ]; then
        echo "Error: API_SERVER variables not set; unable to start the Sandbox."
        exit 1
    fi
    exec streamlit run ./oaim_sandbox.py
fi