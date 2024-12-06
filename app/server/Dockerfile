## Copyright (c) 2023, 2024, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
##################################################
# Base
##################################################
FROM container-registry.oracle.com/os/oraclelinux:9-slim AS pyenv
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

# Clean up package manager caches to reduce image size
RUN microdnf clean all

##################################################
# Server
##################################################
FROM pyenv AS oaim_sandbox

# Argument and environment setup
ARG ENVIRONMENT
ENV PATH=/opt/venv/bin:$PATH

# Copy application and common files with proper ownership
COPY --chown=$RUNUSER:$RUNUSER . /app/
COPY --chown=$RUNUSER:$RUNUSER ../common /app/

# Copy the OCI directory if it exists
ENV ENVIRONMENT=${ENVIRONMENT}
RUN if [ -d "/app/.oci" ] && [ "$ENVIRONMENT" != "development" ]; then \
        rm -rf /app/.oci; \
    else \
        sed -i 's|/.*/\(.*\.pem\)|/app/.oci/\1|g' /app/.oci/config; \
    fi

# Set user and working directory
USER $RUNUSER
WORKDIR /app/

ENTRYPOINT ["uvicorn", "oaim_server:app"]