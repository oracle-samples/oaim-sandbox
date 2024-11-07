## Copyright (c) 2023, 2024, Oracle and/or its affiliates.
## Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
##################################################
# Base
##################################################
FROM container-registry.oracle.com/os/oraclelinux:9-slim AS pyenv
ENV TOKENIZERS_PARALLELISM=true
ENV RUNUSER=oracleaim

RUN microdnf -y update
RUN microdnf -y install python3.11 python3.11-pip 
RUN python3.11 -m venv --symlinks --upgrade-deps /opt/venv
COPY ./requirements.txt /opt/requirements.txt
RUN source /opt/venv/bin/activate && \
    pip3 install --upgrade pip wheel setuptools && \
    pip3 install -r /opt/requirements.txt
RUN groupadd $RUNUSER && useradd -u 10001 -g $RUNUSER -md /app $RUNUSER;
RUN install -d -m 0700 -o $RUNUSER -g $RUNUSER /app/.oci

##################################################
# Chatbot
##################################################
FROM pyenv AS sandbox
ARG ENVIRONMENT
ENV PATH=/opt/venv/bin:$PATH

#COPY THIRD_PARTY_LICENSES.txt /THIRD_PARTY_LICENSES.txt
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --chown=$RUNUSER:$RUNUSER src/ /app/
# Copy the OCI directory if it exists
ENV ENVIRONMENT=${ENVIRONMENT}
RUN if [ -d "/app/.oci" ] && [ "$ENVIRONMENT" != "development" ]; then \
        rm -rf /app/.oci; \
    else \
        sed -i 's|/.*/\(.*\.pem\)|/app/.oci/\1|g' /app/.oci/config; \
    fi

USER $RUNUSER
WORKDIR /app/

ENTRYPOINT ["/entrypoint.sh"]