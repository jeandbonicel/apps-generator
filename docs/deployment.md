# Deployment

Apps Generator produces deployment configurations for Docker Compose, Kubernetes (Kustomize), and GitHub Actions CI/CD.

## Docker Compose

### Generating

After generating all projects in a workspace directory, run:

```bash
appgen docker-compose ./workspace
```

This scans the workspace, detects all generated projects by type, and produces a `docker-compose.yaml` with:

- **PostgreSQL** with per-service databases created via an init script
- **Backend services** with correct `SPRING_DATASOURCE_URL` pointing to Docker service names
- **API gateway** with routes using Docker service names instead of `localhost`
- **Micro-frontends** with nginx serving static assets and CORS headers for Module Federation
- **Platform shell** with nginx proxying `/api/*` to the gateway service

### Environment Variables

The generated Compose file uses variable substitution with sensible defaults:

```yaml
services:
  postgres:
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}

  my-gateway:
    environment:
      SPRING_PROFILES_ACTIVE: ${SPRING_PROFILES_ACTIVE:-local}

  my-platform:
    environment:
      GATEWAY_URL: http://my-gateway:8080
```

The `GATEWAY_URL` is substituted into the shell's nginx config via `envsubst` at container startup, replacing `${GATEWAY_URL}` in the `proxy_pass` directive.

### Running

```bash
cd workspace
docker compose up --build
```

Services start in dependency order. The shell is available at `http://localhost:5173`.

### Per-Service Databases

Each backend gets its own PostgreSQL database. The Compose file includes an init script that creates databases:

```sql
CREATE DATABASE product_service;
CREATE DATABASE inventory_service;
```

Each service connects to its own database via its `SPRING_DATASOURCE_URL`.

## Kubernetes

Each generated project includes a `k8s/` directory with Kustomize base and overlays.

### Structure

```
k8s/
  base/
    deployment.yaml     # Deployment with health/readiness probes
    service.yaml        # ClusterIP Service
    kustomization.yaml  # Base kustomization
  overlays/
    dev/
      kustomization.yaml    # Dev overrides (1 replica, lower limits)
    prod/
      kustomization.yaml    # Prod overrides (3 replicas, higher limits)
```

### Deploying

```bash
# Deploy to dev
kubectl apply -k ./product-service/k8s/overlays/dev
kubectl apply -k ./my-gateway/k8s/overlays/dev
kubectl apply -k ./my-platform/k8s/overlays/dev

# Deploy to prod
kubectl apply -k ./product-service/k8s/overlays/prod
```

### ConfigMap and Probes

Backend deployments include:
- **Liveness probe**: `GET /actuator/health/liveness` (checks if the app is running)
- **Readiness probe**: `GET /actuator/health/readiness` (checks if the app can serve traffic)
- **ConfigMap**: Environment variables for database URL, OIDC issuer, gateway URL, etc.

Frontend deployments include:
- **Liveness probe**: `GET /healthz` (nginx returns 200 "ok")
- **Readiness probe**: Same as liveness

### Production Considerations

The generated Kustomize manifests are a starting point. For production, you will want to add:
- **Ingress** with TLS termination (nginx-ingress, AWS ALB, etc.)
- **PostgreSQL** as a managed service (RDS, Cloud SQL) instead of a container
- **Secrets management** (Kubernetes Secrets, HashiCorp Vault, AWS Secrets Manager)
- **Horizontal Pod Autoscaler** based on CPU/memory metrics
- **Network policies** to restrict inter-service communication

## GitHub Actions CI/CD

Each generated project includes three workflow files in `.github/workflows/`:

### `ci.yaml` -- Continuous Integration

| Trigger | Steps |
|---------|-------|
| Pull request to `main` | Build, lint, test, Playwright E2E (frontend projects) |

For backend projects: `./gradlew build test` (Testcontainers requires Docker, which is available in GitHub Actions runners).

For frontend projects: `npm ci`, `npm run lint`, `npm run build`, `npx playwright test`.

### `build-and-push.yaml` -- Container Build

| Trigger | Steps |
|---------|-------|
| Push to `main` or version tags | Docker build, push to container registry |

The registry is configured via the `containerRegistry` and `containerRegistryOrg` parameters (default: `ghcr.io`). Images are tagged with the Git SHA and `latest`.

### `deploy.yaml` -- Deployment

| Trigger | Steps |
|---------|-------|
| Manual dispatch (workflow_dispatch) | Kustomize `set image`, `kubectl apply` |

Requires GitHub environment secrets:
- `KUBE_CONFIG` -- base64-encoded kubeconfig
- `REGISTRY_USERNAME` / `REGISTRY_PASSWORD` -- container registry credentials

### Customizing Workflows

The generated workflows are self-contained YAML files. Common customizations:
- Add Slack/Teams notifications on failure
- Add staging environment with approval gates
- Add database migration step before deployment
- Switch container registry (Docker Hub, ECR, GCR, ACR)

## Health Checks

### Backend Services

Spring Boot Actuator provides health endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/actuator/health` | Overall health status |
| `/actuator/health/liveness` | Liveness probe (is the app running?) |
| `/actuator/health/readiness` | Readiness probe (can it serve traffic?) |
| `/actuator/info` | Build info and version |

These endpoints are public (no JWT required) in both `SecurityConfig` and `DevSecurityConfig`.

### Frontend Services

Nginx serves a simple health endpoint:

```nginx
location = /healthz {
    access_log off;
    return 200 "ok";
}
```

This is used by Kubernetes probes and Docker health checks.
