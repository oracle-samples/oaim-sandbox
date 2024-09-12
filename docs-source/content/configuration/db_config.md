---
title: 'Database Configuration'
date: 2024-09-10T13:57:37Z
draft: false
---

{{< hint type=[warning] icon=gdoc_fire title="10-Sept-2024: Documentation In-Progress..." >}}
Thank you for your patience as we work on updating the documentation. Please check back soon for the latest updates.{{< /hint >}}

To use the Retrieval-Augmented Generation (RAG) functionality of the Sandbox, you will need to setup/enable an [embedding model](model_config) and have access to an **Oracle Database 23ai**.  Both the [Always Free Oracle Autonomous Database Serverless (ADB-S)](https://docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/autonomous-always-free.html) and the [Oracle Database 23ai Free](https://www.oracle.com/uk/database/free/get-started/) are supported and a great way to get up and running quickly.

## Configuration

The database can either be configured using environment variables or through the Sandbox interface.

### Sandbox Interface

To configure the Database from the Sandbox, navigate to `Configuration -> Database`:

![Database Config](../images/db_config.png)

Provide the following input:
- DB Username: The pre-created [database username](#database-user) where the embeddings will be stored
- DB Password: The password for the `DB Username`
- Database Connect String: The full connection string or [TNS Alias](#using-a-wallettns_admin-directory) for the Database.  This is normally in the form of (description=... (service_name=<service>)).
- Wallet Password: If the connection to the database uses mTLS, provide the wallet password.  **NOTE**: Review [Using a Wallet](#using-a-wallettns_admin-directory) for additional setup instructions.

Once all fields are set, click the `Save` button.

### Environment Variables

The following environment variables can be set, prior to starting the Sandbox, to automatically configure the database:

- DB_USERNAME: The pre-created [database username](#database-user) where the embeddings will be stored
- DB_PASSWORD: The password for the `DB Username`
- DB_DSN: The full connection string or [TNS Alias](#using-a-wallettns_admin-directory) for the Database.  This is normally in the form of (description=... (service_name=<service>)).
- DB_WALLET_PASSWORD: If the connection to the database uses mTLS, provide the wallet password.  **NOTE**: Review [Using a Wallet](#using-a-wallettns_admin-directory) for additional setup instructions.

For Example:

```bash
export DB_USERNAME="DEMO"
export DB_PASSWORD=MYCOMPLEXSECRET
export DB_DSN="(description=(address=(protocol=tcps)(port=1521)(host=database.host.com))(connect_data=(service_name=SANDBOXDB)))"
export DB_WALLET_PASSWORD=MYCOMPLEXWALLETSECRET
```

## Using a Wallet/TNS_ADMIN Directory

For mTLS connectivity, or to specify a TNS Alias instead of a full connect string, you can set the `TNS_ADMIN` environment variable to the location where the SQL*Net files are staged.  Alternatively, you can copy those files to the `app/src/tns_admin` directory.

If using and ADB-S wallet, unzip the contents to one of the above (`TNS_ADMIN` or `app/src/tns_admin`) directories.

## Database User

A database user is required to store the embeddings used for RAG into a Vector Store. A non-privileged user should be used for this purpose, using the below syntax as an example:

```sql
CREATE USER "DEMO" IDENTIFIED BY MYCOMPLEXSECRET
    DEFAULT TABLESPACE "DATA"
    TEMPORARY TABLESPACE "TEMP";
GRANT "DB_DEVELOPER_ROLE" TO "DEMO";
ALTER USER "DEMO" DEFAULT ROLE ALL;
ALTER USER "DEMO" QUOTA UNLIMITED ON DATA;
```

Replace "DEMO" as required.

{{< hint type=[tip] icon=gdoc_fire title="Multiple Users" >}}
Creating multiple users in the same database allows developers to separate their experiments simply by changing the "Database User:"
{{< /hint >}}
