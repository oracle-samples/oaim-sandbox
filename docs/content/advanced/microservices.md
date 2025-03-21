+++
title = 'Microservices'
weight = 5
+++

<!--
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

spell-checker: ignore opentofu ocid oraclecloud oaim  ollama crds ADBDB finalizers mxbai 
-->

The {{< full_app_ref >}} was specifically designed to run on infrastructure supporting microservices architecture, including [Kubernetes](https://kubernetes.io/).

## Oracle Kubernetes Engine

The following example shows running the {{< short_app_ref >}} in [Oracle Kubernetes Engine](https://docs.oracle.com/en-us/iaas/Content/ContEng/Concepts/contengoverview.htm) (**OKE**).  The Infrastructure as Code (**IaC**) provided in the source [opentofu](https://github.com/oracle-samples/oaim-sandbox/tree/main/opentofu) directory was used to provision the infrastructure in Oracle Cloud Infrastructure (**OCI**).

![OCI OKE](../images/infra_oci.png)

The command to connect to the **OKE** cluster will be output as part of the **IaC**.

### Ingress

To access the {{< short_app_ref >}} GUI and API Server, you can either use a port-forward or an Ingress service.  For demonstration purposes, the [Ingress-Nginx Controller](https://kubernetes.github.io/ingress-nginx/deploy/) will be used to create a [Flexible LoadBalancer](https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/overview.htm) in **OCI**.

This example will create the loadbalancer exposing port 80 for the {{< short_app_ref >}} GUI and port 8000 for the {{< short_app_ref >}} API Server.  It is _HIGHLY_ recommended to protect these ports with [Network Security Groups](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/networksecuritygroups.htm) (**NSGs**).

The service manifest has two values that should be supplied:

- `<lb_nsg_ocid>` - **NSG** OCID's to protect the LB ports
- `<lb_reserved_ip>` - A reserved IP address for the Loadbalancer

These will be output as part of the **IaC** but can be removed from the code if not reserving an IP or protecting the Load Balancer.

1. Create a `ingress.yaml`:
    ```yaml
    controller:
      kind: DaemonSet
      # Service is configured via its own manifest and is conditional
      service:
        enabled: false
      config:
        ssl-redirect: "false" # NGINX isn't using any TLS certificates, terminated at LB
        use-forwarded-headers: "true" # NGINX will decide on redirection based on headers
      updateStrategy:
        rollingUpdate:
          maxUnavailable: 1
        type: RollingUpdate
    ```

1. Install the Ingress-Nginx Controller:
    ```bash
    helm upgrade \
        --install ingress-nginx ingress-nginx \
        --repo https://kubernetes.github.io/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        -f ingress.yaml
    ```

1. Create a `service.yaml` file (replace `<...>` values or remove):
    ```yaml
      apiVersion: v1
      kind: Service
      metadata:
        annotations:
          oci.oraclecloud.com/load-balancer-type: lb
          service.beta.kubernetes.io/oci-load-balancer-shape: flexible
          service.beta.kubernetes.io/oci-load-balancer-shape-flex-max: "100"
          service.beta.kubernetes.io/oci-load-balancer-shape-flex-min: "10"
          oci.oraclecloud.com/oci-network-security-groups: "<lb_nsg_ocid>"
          service.beta.kubernetes.io/oci-load-balancer-security-list-management-mode: None
        name: ingress-nginx-controller
        namespace: ingress-nginx
      spec:
        allocateLoadBalancerNodePorts: true
        externalTrafficPolicy: Cluster
        internalTrafficPolicy: Cluster
        ipFamilies:
        - IPv4
        ipFamilyPolicy: SingleStack
        loadBalancerIP: "<lb_reserved_ip>"
        ports:
        - appProtocol: http
          name: client
          port: 80
          protocol: TCP
          targetPort: http
        - appProtocol: http
          name: server
          port: 8000
          protocol: TCP
          targetPort: http
        selector:
          app.kubernetes.io/component: controller
          app.kubernetes.io/instance: ingress-nginx
          app.kubernetes.io/name: ingress-nginx
        type: LoadBalancer
      ```

1. Apply the Service:
    ```bash
    kubectl apply -f service.yaml
    ```

### Images

You will need to build the {{< short_app_ref >}} container images and stage them in a container registry, such as the [OCI Container Registry](https://docs.oracle.com/en-us/iaas/Content/Registry/Concepts/registryoverview.htm) (**OCIR**).

1. Build the {{< short_app_ref >}} images:

    From the code source `src/` directory:
    ```bash
    podman build --arch amd64 -f client/Dockerfile -t oai-client:latest .

    podman build --arch amd64 -f server/Dockerfile -t oai-server:latest .
    ```

1. Log into your container registry:

    More information on authenticating to **OCIR** can be found [here](https://docs.oracle.com/en-us/iaas/Content/Registry/Tasks/registrypushingimagesusingthedockercli.htm).

    ```bash
    podman login <registry-domain>
    ```

    Example:
    ```bash
    podman login iad.ocir.io
    ```

    You will be prompted for a username and token password.

1. Push the {{< short_app_ref >}} images:

    More information on pushing images to **OCIR** can be found [here](https://docs.oracle.com/en-us/iaas/Content/Registry/Tasks/registrypushingimagesusingthedockercli.htm).

    Example (the values for `<server_repository>` and `<server_repository>` are provided from the **IaC**):
    ```bash
    podman tag oai-client:latest <client_repository>:latest
    podman push <client_repository>:latest

    podman tag oai-server:latest <server_repository>:latest
    podman push <server_repository>:latest
    ```

### The {{< short_app_ref >}}

The {{< short_app_ref >}} can be deployed using the [Helm](https://helm.sh/) chart provided with the source:
[{{< short_app_ref >}} Helm Chart](https://github.com/oracle-samples/oaim-sandbox/tree/main/helm).  A list of all values can be found in [values_summary.md](https://github.com/oracle-samples/oaim-sandbox/tree/main/helm/values_summary.md).

If you deployed a GPU node pool as part of the **IaC**, you can deploy Ollama and enable a Large Language and Embedding Model out-of-the-box.

1. Create the `oai-explorer` namespace:
    
    ```bash
    kubectl create namespace oai-explorer
    ```

1. Create a secret to hold the API Key:

    ```bash
    kubectl create secret generic api-key \
      --from-literal=apiKey=$(openssl rand -hex 32) \
      --namespace=oai-explorer
    ```

1. Create a secret to hold the Database Authentication:

    The command has two values that should be supplied:

    - `<adb_password>` - Password for the ADB ADMIN User
    - `<adb_service>` - The Service Name (i.e. ADBDB_TP)

    ```bash
    kubectl create secret generic db-authn \
      --from-literal=username='ADMIN' \
      --from-literal=password='<adb_password>' \
      --from-literal=service='<adb_service>' \
      --namespace=oai-explorer
    ```

    These will be output as part of the **IaC**.

    {{< icon "star" >}} While the example shows the ADMIN user, it is advisable to [create a new non-privileged database user](../client/configuration/db_config/#database-user).


1. Create the `values.yaml` file for the Helm Chart:

    The `values.yaml` has five values that should be supplied:

    - `<lb_reserved_ip>` - A reserved IP address for the Loadbalancer
    - `<adb_ocid>` - Autonomous Database OCID
    - `<client_repository>` - Full path to the repository for the {{< short_app_ref >}} Image 
    - `<server_repository>` - Full path to the repository for the API Server Image

    These will be output as part of the **IaC**.

    {{< icon "star" >}} If using the **IaC** for **OCI**, it is not required to specify an ImagePullSecret as the cluster nodes are configured with the [Image Credential Provider for OKE](https://github.com/oracle-devrel/oke-credential-provider-for-ocir).

    ```yaml
    global:
      api:
        secretName: "api-key"

    # -- API Server configuration
    oai-server:
      enabled: true
      image:
        repository: <server_repository>
        tag: "latest"

      ingress:
        enabled: true
        annotations:
          nginx.ingress.kubernetes.io/upstream-vhost: "<lb_reserved_ip>"

      # -- Oracle Autonomous Database Configuration
      adb:
        enabled: true
        ocid: "<adb_ocid>"
        mtlsWallet: ""
        authN:
          secretName: "db-authn"

    oai-client:
      enabled: true
      image:
        repository: <client_repository>
        tag: "latest"

      ingress:
        enabled: true
        annotations:
          nginx.ingress.kubernetes.io/upstream-vhost: "<lb_reserved_ip>"

      client:
        features:
          disableTestbed: "false"
          disableApi: "false"
          disableTools: "false"
          disableDbCfg: "true"
          disableModelCfg: "false"
          disableOciCfg: "true"
          disableSettings: "true"

    ollama:
      enabled: true
      models:
        - llama3.1
        - mxbai-embed-large
      resources:
        limits:
          nvidia.com/gpu: 1
    ```

1. Deploy the Helm Chart:

    From the `helm/` directory:

    ```bash
    helm upgrade \
      --install oai-explorer . \
      --namespace oai-explorer \
      -f values.yaml
    ```

### Cleanup

To remove the {{< short_app_ref >}} from the OKE Cluster:

1. Uninstall the Helm Chart:

    ```bash
    helm uninstall oai-explorer -n oai-explorer
    ```

1. Delete the `oai-explorer` namespace:

    ```bash
    kubectl delete namespace oai-explorer
    ```