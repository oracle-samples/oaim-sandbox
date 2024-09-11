#!/bin/bash
## Copyright (c) 2023, 2024, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

if [ "$ENVIRONMENT" = "development" ]; then
    echo "Running in development mode..."
    exec bash
else
    exec streamlit run /app/oaim-sandbox.py
fi