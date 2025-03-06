## Copyright (c) 2024, 2025, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
##################################################
# Base - All-In-One
##################################################
FROM container-registry.oracle.com/os/oraclelinux:8-slim AS all_in_one_pyenv

# NUMBA_DISABLE_JIT is for Apple Silicon support
ENV TOKENIZERS_PARALLELISM=true \
    NUMBA_DISABLE_JIT=1 \
    RUNUSER=oracleaim

# Combine related commands into a single RUN layer to minimize image layers
RUN microdnf -y update && \
    microdnf -y install python3.11 python3.11-pip && \
    microdnf clean all && \
    python3.11 -m venv --symlinks --upgrade-deps /opt/.venv && \
    groupadd $RUNUSER && \
    useradd -u 10001 -g $RUNUSER -md /app $RUNUSER && \
    install -d -m 0700 -o $RUNUSER -g $RUNUSER /app/.oci && \
    install -d -m 0700 -o $RUNUSER -g $RUNUSER /app/tmp

# Avoid re-installs of python modules if the reqs haven't changed
COPY ./requirements.txt /opt/requirements.txt
COPY ./sandbox/requirements.txt /opt/sandbox/requirements.txt
COPY ./server/requirements.txt /opt/server/requirements.txt
# Use the virtual environment for pip installations
RUN source /opt/.venv/bin/activate && \
    pip install --upgrade pip wheel setuptools && \
    pip install -r /opt/requirements.txt

##################################################
# Application
##################################################
FROM all_in_one_pyenv AS oaim_application
ENV PATH=/opt/.venv/bin:$PATH
ENV TEMP=/app/tmp

COPY --chown=$RUNUSER:$RUNUSER . /app/
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

RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
