## Copyright (c) 2023, 2024, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
#############################################################
# Base - Web GUI
# Build from the app/ directory:
#  podman build -f sandbox/Dockerfile -t oaim-sandbox:0.1.0 .
#############################################################
FROM container-registry.oracle.com/os/oraclelinux:8-slim AS sandbox_pyenv

ENV TOKENIZERS_PARALLELISM=true \
    RUNUSER=oracleaim

# Combine related commands into a single RUN layer to minimize image layers
RUN microdnf -y update && \
    microdnf -y install python3.11 python3.11-pip && \
    microdnf clean all && \
    python3.11 -m venv --symlinks --upgrade-deps /opt/.venv && \
    groupadd $RUNUSER && \
    useradd -u 10001 -g $RUNUSER -md /app $RUNUSER && \
    install -d -m 0700 -o $RUNUSER -g $RUNUSER /app/.oci \
    install -d -m 0700 -o $RUNUSER -g $RUNUSER /app/tmp

# Avoid re-installs of python modules if the reqs haven't changed
COPY ./sandbox/requirements.txt /opt/sandbox/requirements.txt
# Use the virtual environment for pip installations
RUN source /opt/.venv/bin/activate && \
    pip install --upgrade pip wheel setuptools && \
    pip install -r /opt/sandbox/requirements.txt

##################################################
# Application
##################################################
FROM sandbox_pyenv AS oaim_sandbox
ENV PATH=/opt/.venv/bin:$PATH

COPY --chown=$RUNUSER:$RUNUSER . /app
RUN rm -rf /app/server /app/.oci

# Set user and working directory
USER $RUNUSER
WORKDIR /app/

RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
