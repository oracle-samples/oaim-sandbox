+++
title = 'Installation'
weight = 30
+++

<!--
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
-->

{{% notice style="code" title="20-Jan-2025: Documentation In-Progress..." icon="pen" %}}
Thank you for your patience as we work on updating the documentation. Please check back soon for the latest updates.
{{% /notice %}}

## Kubernetes

1. Log into your Container Registry

podman login iad.ocir.io -u maacloud/oracleidentitycloudservice/john.lathouwers@oracle.com
dML1j<etHOV:pMeik-l>

1. Build the Images

Server:
From the src/ directory:

podman build -f sandbox/Dockerfile -t iad.ocir.io/maacloud/oaim-sandbox:0.1.0 .
podman build -f server/Dockerfile -t iad.ocir.io/maacloud/oaim-server:0.1.0 .

1. Push the Images to the Container Registry:

podman push iad.ocir.io/maacloud/oaim-sandbox:0.1.0
podman push iad.ocir.io/maacloud/oaim-server:0.1.0

1. From the helm/ directory Load the Helm

helm upgrade --namespace oaim-sandbox --install dev .

1. Uninstall

helm uninstall dev
