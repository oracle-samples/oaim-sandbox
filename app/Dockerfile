## Copyright (c) 2023, 2024, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
##################################################
# Base
##################################################
FROM container-registry.oracle.com/os/oraclelinux:8-slim AS pyenv

ENV TOKENIZERS_PARALLELISM=true \
    RUNUSER=oracleaim

# Combine related commands into a single RUN layer to minimize image layers
RUN microdnf -y update && \
    microdnf -y install python3.11 python3.11-pip && \
    python3.11 -m venv --symlinks --upgrade-deps /opt/.venv && \
    groupadd $RUNUSER && \
    useradd -u 10001 -g $RUNUSER -md /app $RUNUSER && \
    install -d -m 0700 -o $RUNUSER -g $RUNUSER /app/.oci

# Use the virtual environment for pip installations
RUN source /opt/.venv/bin/activate && \
    pip install --upgrade pip wheel setuptools

# Clean up package manager caches to reduce image size
RUN microdnf clean all

##################################################
# Application
##################################################
FROM pyenv AS oaim_application
ARG IMAGE_TYPE
ENV PATH=/opt/.venv/bin:$PATH

# Copy application files
COPY --chown=$RUNUSER:$RUNUSER . /app/
RUN chmod +x /app/entrypoint.sh

RUN if [ "$IMAGE_TYPE" = "server" ]; then \
        rm -rf /app/sandbox; \
        pip3 install -r /app/server/requirements.txt; \
    elif [ "$IMAGE_TYPE" = "sandbox" ]; then \
        rm -rf /app/server; \
        rm -rf /app/.oci/*; \
        pip3 install -r /app/sandbox/requirements.txt; \
    else \
        pip3 install -r /app/requirements.txt; \
    fi

# Remove the OCI file if not development; update the key path if so
ENV ENVIRONMENT=${ENVIRONMENT}
RUN if [ -d "/app/.oci" ] && [ "$ENVIRONMENT" != "development" ]; then \
        rm -rf /app/.oci; \
    else \
        sed -i 's|/.*/\(.*\.pem\)|/app/.oci/\1|g' /app/.oci/config; \
    fi

# Set user and working directory
USER $RUNUSER
WORKDIR /app/

ENTRYPOINT ["/app/entrypoint.sh"]
