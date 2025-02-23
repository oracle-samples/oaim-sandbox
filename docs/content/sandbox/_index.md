+++
title = 'The Sandbox'
weight = 20
+++

<!--
Copyright (c) 2024-2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
-->

<!--
Copyright (c) 2024-2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

spell-checker:ignore streamlit, oaim, uvicorn
-->

The **Oracle AI Microservices Sandbox** (the **Sandbox**) consists of an API Server ([**oaim-server**](#api-server-oaim-server)) and an _optional_ web-based GUI ([**oaim-sandbox**](#client-oaim-sandbox)) component.  Both the API Server and GUI can be run on bare-metal or inside containers.  

![Architecture Overview](images/arch_overview.png)

The following additional components, not delivered with the **Sandbox**, are also required.  These can be run On-Premises or in the Cloud:
- [Oracle Database 23ai](#database), including [Oracle Database 23ai **Free**](https://www.oracle.com/uk/database/free/)
- Access to at least one [Large Language Model](#large-language-model)
- Access to at least one [Embedding Model](#embedding-model) (for Retrieval Augmented Generation)

The **Sandbox** is specifically designed to run in container orchestration systems, such as [Kubernetes](https://kubernetes.io/).  For more information on deploying the **Sandbox** in Kubernetes, using a Helm Chart, please review the [Installation](../installation) documentation.

## API Server (OAIM Server)

The workhorse of the **Sandbox** is the API Server, referred to as the **OAIM Server**.  By default, the **OAIM Server** will start on port 8000

{{% notice style="code" title="BYO Client" icon="circle-info" %}}
The **OAIM Server** API documentation can be accessed at `http://<IP Address>:<Port>/v1/docs#` 
{{% /notice %}}

![API Server](images/api_server.png)

Powered by [FastAPI](https://fastapi.tiangolo.com/) and [Uvicorn](https://www.uvicorn.org/), the **OAIM Server** acts as an intermediary between the clients, AI Models, and the Oracle Database. It processes incoming API requests, including 

## Client (OAIM Sandbox)

, built with [Streamlit](https://streamlit.io/)

## Database
[Oracle Database 23ai](https://www.oracle.com/uk/database/23ai/), including [Oracle Database 23ai **Free**](https://www.oracle.com/uk/database/free/)

## Document Source


## AI Models

### Large Language Model

### Embedding Model