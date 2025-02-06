# OCI Installation of ingress-nginx

This is an example of using ingress-nginx with Oracle Cloud Infrastructure's 
Oracle Kubernetes Engine.  This will create a loadbalancer exposing port 80
for the GUI and port 8000 for the API Server.  It is HIGHLY recommended to
protect these ports with NSG's.  The example has two values that should be supplied:

- `<CSV's of NSG OCIDs>` - NSG OCID's to protect the LB ports
- `<Reserved IP>` - A reserved IP address for the Loadbalancer

These can be removed from the code if not reserving an IP or protecting the Load Balancer.


## Example

1. Create a values.yaml:
```yaml
controller:
  kind: DaemonSet
  image:
    pullPolicy: IfNotPresent
  resources:
    requests:
      cpu: 100m
      memory: 90Mi
  # Service is configured via its own manifest and is conditional
  service:
    enabled: false
  config:
    ssl-redirect: "false" # NGINX isn't using any TLS certificates, terminated at LB
    use-forwarded-headers: "true" # NGINX will decide on redirection based on headers
  ingressClassResource:
    name: nginx
    enabled: true
    default: false
    controllerValue: "k8s.io/ingress-nginx"
  updateStrategy:
    rollingUpdate:
      maxUnavailable: 1
    type: RollingUpdate
  metrics:
    enabled: true
  livenessProbe:
    httpGet:
      path: "/healthz"
      port: 10254
      scheme: HTTP
    initialDelaySeconds: 10
    periodSeconds: 10
    timeoutSeconds: 1
    successThreshold: 1
    failureThreshold: 5
  readinessProbe:
    httpGet:
      path: "/healthz"
      port: 10254
      scheme: HTTP
    initialDelaySeconds: 10
    periodSeconds: 10
    timeoutSeconds: 1
    successThreshold: 1
    failureThreshold: 3
```

1. Install the ingress-nginx Helm Chart:

```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace -f values.yaml
```

1. Create the service:
```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    meta.helm.sh/release-name: ingress-nginx
    meta.helm.sh/release-namespace: ingress-nginx
    oci.oraclecloud.com/load-balancer-type: lb
    service.beta.kubernetes.io/oci-load-balancer-shape: flexible
    service.beta.kubernetes.io/oci-load-balancer-shape-flex-max: "100"
    service.beta.kubernetes.io/oci-load-balancer-shape-flex-min: "10"
    oci.oraclecloud.com/oci-network-security-groups: "<CSV's of NSG OCIDs>"
  finalizers:
  - service.kubernetes.io/load-balancer-cleanup
  labels:
    app.kubernetes.io/component: controller
    app.kubernetes.io/instance: ingress-nginx
    app.kubernetes.io/name: ingress-nginx
  name: ingress-nginx-controller
  namespace: ingress-nginx
spec:
  allocateLoadBalancerNodePorts: true
  externalTrafficPolicy: Cluster
  internalTrafficPolicy: Cluster
  ipFamilies:
  - IPv4
  ipFamilyPolicy: SingleStack
  loadBalancerIP: <Reserved IP>
  ports:
  - appProtocol: http
    name: sandbox
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
  sessionAffinity: None
  type: LoadBalancer
  ```