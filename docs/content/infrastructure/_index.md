+++
title = 'Infrastructure'
weight = 20
+++

<!--
Copyright (c) 2024-2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
-->

{{% notice style="code" title="20-Jan-2025: Documentation In-Progress..." icon="pen" %}}
Thank you for your patience as we work on updating the documentation. Please check back soon for the latest updates.
{{% /notice %}}

The **Oracle AI Microservices Sandbox** (the **Sandbox**) consists of an API Server ([oaim-server](#oaim-server)) and an _optional_ web-based GUI ([oaim-sandbox](#oaim-sandbox)) component.  Both the API Server and GUI can be run on bare-metal or inside container(s).  

The **Sandbox** is specifically designed to run in container orchestration systems, such as [Kubernetes](https://kubernetes.io/).  For more information on deploying the **Sandbox** in Kubernetes, using a Helm Chart, please review the [Installation](../installation) documentation.

The following additional components, not delivered with the Sandbox, are also required.  These can be run On-Premises or in the Cloud:
- Oracle Database 23ai
- Access to at least one Large Language
- Access to at least one Embedding model (for Retrieval Augmented Generation)

## OAIM Server


## OAIM Sandbox