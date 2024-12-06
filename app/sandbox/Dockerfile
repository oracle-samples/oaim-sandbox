## Copyright (c) 2023, 2024, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
##################################################
# Base
##################################################
FROM container-registry.oracle.com/os/oraclelinux:9-slim AS pyenv
ARG INCL_SERVER=false
ENV TOKENIZERS_PARALLELISM=true \
    RUNUSER=oracleaim

# Combine related commands into a single RUN layer to minimize image layers
RUN microdnf -y update && \
    microdnf -y install python3.11 python3.11-pip && \
    python3.11 -m venv --symlinks --upgrade-deps /opt/venv && \
    groupadd $RUNUSER && \
    useradd -u 10001 -g $RUNUSER -md /app $RUNUSER && \
    install -d -m 0700 -o $RUNUSER -g $RUNUSER /app/.oci

# Use the virtual environment for pip installations
COPY ./requirements.txt /opt/requirements.txt
RUN source /opt/venv/bin/activate && \
    pip install --upgrade pip wheel setuptools && \
    pip install -r /opt/requirements.txt

RUN if [ "$INCL_SERVER" = "true" ]; then \
        cp -r ../server/requirements.txt /opt/requirements_server.txt && \
        pip install -r /opt/requirements_server.txt; \
    fi

# Clean up package manager caches to reduce image size
RUN microdnf clean all


##################################################
# Sandbox
##################################################
FROM pyenv AS oaim_sandbox

# Argument and environment setup
ARG ENVIRONMENT
ARG INCL_SERVER=false
ENV PATH=/opt/venv/bin:$PATH

# Copy application and common files with proper ownership
COPY --chown=$RUNUSER:$RUNUSER . /app/
COPY --chown=$RUNUSER:$RUNUSER ../common /app/
RUN if [ "$INCL_SERVER" = "true" ]; then \
        cp -r --chown=$RUNUSER:$RUNUSER ../server /app/; \
    fi

# Set user and working directory
USER $RUNUSER
WORKDIR /app/

# Correct ENTRYPOINT syntax
ENTRYPOINT ["streamlit", "run", "/app/oaim-sandbox.py"]