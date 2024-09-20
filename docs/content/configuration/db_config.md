+++
title = "Database Configuration"
date = 2024-09-10T13:57:37Z
draft = false
+++

<!--
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
-->

To use the Retrieval-Augmented Generation (RAG) functionality of the Sandbox, you will need to setup/enable an [embedding model](../model_config) and have access to an **Oracle Database 23ai**. Both the [Always Free Oracle Autonomous Database Serverless (ADB-S)](https://docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/autonomous-always-free.html) and the [Oracle Database 23ai Free](https://www.oracle.com/uk/database/free/get-started/) are supported. They are a great, no-cost, way to get up and running quickly.

## Configuration

The database can either be configured using environment variables or through the **Sandbox** interface.

### Sandbox Interface

To configure the Database from the Sandbox, navigate to `Configuration -> Database`:

![Database Config](../images/db_config.png)

Provide the following input:

- **DB Username**: The pre-created [database username](#database-user) where the embeddings will be stored
- **DB Password**: The password for the **DB Username**
- **Database Connect String**: The full connection string or [TNS Alias](#using-a-wallettns_admin-directory) for the Database. This is normally in the form of `(DESCRIPTION=(ADDRESS=(PROTOCOL=tcp)(HOST=<hostname>)(PORT=<port>))(CONNECT_DATA=(SERVICE_NAME=<service_name>)))` or `//<hostname>:<port>/<service_name>`.
- **Wallet Password** (_Optional_): If the connection to the database uses mTLS, provide the wallet password. {{< icon "gdoc_star" >}}Review [Using a Wallet](#using-a-wallettns_admin-directory) for additional setup instructions.

Once all fields are set, click the `Save` button.

### Environment Variables

The following environment variables can be set, prior to starting the Sandbox, to automatically configure the database:

- **DB_USERNAME**: The pre-created [database username](#database-user) where the embeddings will be stored
- **DB_PASSWORD**: The password for the `DB Username`
- **DB_DSN**: The connection string or [TNS Alias](#using-a-wallettns_admin-directory) for the Database. This is normally in the form of `(description=... (service_name=<service_name>))` or `//host:port/service_name`.
- **DB_WALLET_PASSWORD** (_Optional_): If the connection to the database uses mTLS, provide the wallet password. {{< icon "gdoc_star" >}}Review [Using a Wallet](#using-a-wallettns_admin-directory) for additional setup instructions.

For Example:

```bash
export DB_USERNAME="DEMO"
export DB_PASSWORD=MYCOMPLEXSECRET
export DB_DSN="//localhost:1521/SANDBOXDB"
export DB_WALLET_PASSWORD=MYCOMPLEXWALLETSECRET
```

## Using a Wallet/TNS_ADMIN Directory

For mTLS database connectivity or to specify a TNS alias instead of a full connect string, you can use the contents of a `TNS_ADMIN` directory.

{{< hint type=[info] icon=gdoc_info_outline title="Unzip Wallet" >}}
If using and ADB-S wallet, unzip the contents into the `TNS_ADMIN` directory. The `.zip` file will not be recognized.
{{< /hint >}}

### Bare-Metal Installation

For bare-metal installations, set the `TNS_ADMIN` environment variable, or copy the contents of your current TNS_ADMIN to `app/src/tns_admin` before starting the **Sandbox**.

### Container Installation

For container installations, there are a couple of ways to include the contents of your `TNS_ADMIN` in the image:

- Before building the image, copy the contents of your `TNS_ADMIN` to `app/src/tns_admin`. This will include your `TNS_ADMIN` as part of the image.
- Mount your `TNS_ADMIN` directory into the container on startup, for example: `podman run -p 8501:8501 -v $TNS_ADMIN:/app/tns_admin -it --rm oaim-sandbox`
- Copy the `TNS_ADMIN` directory into an existing running container, for example: `podman cp $TNS_ADMIN /app/tns_admin oaim-sandbox`

## Database User

A database user is required to store the embeddings, used for **RAG**, into the Oracle Database. A non-privileged user should be used for this purpose, using the below syntax as an example:

```sql
CREATE USER "DEMO" IDENTIFIED BY MYCOMPLEXSECRET
    DEFAULT TABLESPACE "DATA"
    TEMPORARY TABLESPACE "TEMP";
GRANT "DB_DEVELOPER_ROLE" TO "DEMO";
ALTER USER "DEMO" DEFAULT ROLE ALL;
ALTER USER "DEMO" QUOTA UNLIMITED ON DATA;
```

Replace "DEMO" as required.

{{< hint type=[tip] icon=gdoc_info_outline title="Multiple Users" >}}
Creating multiple users in the same database allows developers to separate their experiments simply by changing the "Database User:"
{{< /hint >}}
