# oaim-sandbox Helm Chart

## Secret Pre-Requisites

This Helm Chart requires three Kubernetes Secrets to be created prior to installing:

### Registry Credentials

**Note**: This requirement maybe deprecated in OCI/OKE: [Credential Provider](https://github.com/oracle-devrel/oke-credential-provider-for-ocir/issues/2)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: regcred
type: kubernetes.io/dockerconfigjson
stringData:
  .dockerconfigjson: ...
```

Example:

```bash
docker login iad.ocir.io -u <username>
kubectl create secret docker-registry regcred --from-file=.dockerconfigjson=/run/user/1002/containers/auth.json
```

### Model API Keys

Example:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: sandbox-api-keys
type: Opaque
stringData:
  openai_api_key: ...
  pplx_api_key: ...
```

### Database Authentication

Example:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: sandboxdb-authn
type: Opaque
stringData:
  password: ...
  service: ...
  username: ...
```

## Install

```bash
helm upgrade --install oaim-sandbox .
```

## Uninstall

```bash
helm uninstall oaim-sandbox
```
