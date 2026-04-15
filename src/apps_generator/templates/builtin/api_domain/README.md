# api-domain

Spring Boot 3 backend with Domain-Driven Design architecture, PostgreSQL, and multi-tenant support.

## What it generates

A Gradle-based Spring Boot application with:
- **DDD layered architecture** — domain, application, infrastructure, interfaces
- **PostgreSQL** with Liquibase migrations
- **OAuth2 resource server** — validates JWTs from Clerk, Keycloak, or any OIDC provider
- **Multi-tenant** — extracts `X-Tenant-ID` header for data scoping
- **OpenAPI/Swagger** documentation
- Docker, Kubernetes, and CI/CD

## Usage

```bash
appgen generate api-domain -o ./order-service \
  -s projectName=order-service \
  -s groupId=com.example \
  -s basePackage=com.example.orders

# With Clerk as OIDC issuer
appgen generate api-domain -o ./order-service \
  -s projectName=order-service \
  -s groupId=com.example \
  -s basePackage=com.example.orders \
  -s oidcIssuerUri=https://your-clerk-domain.clerk.accounts.dev
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Project name (kebab-case) |
| `groupId` **(required)** | `com.example` | Maven/Gradle group ID |
| `basePackage` **(required)** | `com.example` | Java base package |
| `javaVersion` | `21` | Java version (17 or 21) |
| `springBootVersion` | `3.3.0` | Spring Boot version |
| `containerRegistry` | `ghcr.io` | Container registry |
| `containerRegistryOrg` | `your-org` | Registry organization |
| `k8sNamespace` | `default` | Kubernetes namespace |
| `dbName` | derived from projectName | PostgreSQL database name |
| `oidcIssuerUri` | `https://auth.example.com/realms/main` | OIDC issuer URI |

## Feature flags

| Feature | Default | Description |
|---------|---------|-------------|
| `database` | on | PostgreSQL + Liquibase migrations |
| `oauth2` | on | OAuth2 resource server (JWT validation) |
| `docker` | on | Multi-stage Dockerfile + docker-compose |
| `kubernetes` | on | Kustomize base + dev/prod overlays |
| `cicd` | on | GitHub Actions (CI, build-push, deploy) |
| `openapi` | on | OpenAPI/Swagger documentation |

## Generated structure

```
order-service/
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
├── gradlew / gradlew.bat
├── src/main/java/com/example/orders/
│   ├── OrderServiceApplication.java
│   ├── domain/
│   │   ├── model/
│   │   ├── repository/
│   │   └── service/
│   ├── application/
│   ├── infrastructure/
│   │   ├── config/
│   │   │   ├── SecurityConfig.java    # OAuth2 JWT validation
│   │   │   ├── WebConfig.java         # CORS + X-Tenant-ID filter
│   │   │   └── OpenApiConfig.java     # Swagger setup
│   │   └── persistence/
│   └── interfaces/rest/
│       ├── HealthController.java
│       └── dto/
├── src/main/resources/
│   ├── application.yaml
│   ├── application-local.yaml
│   └── db/changelog/                  # Liquibase migrations
├── src/test/java/.../
├── docker/
│   ├── Dockerfile                     # Multi-stage (JDK build + JRE runtime)
│   └── docker-compose.yaml            # App + PostgreSQL + pgAdmin
├── k8s/base/ + overlays/
└── .github/workflows/
```

## Multi-tenant support

The `WebConfig.java` includes a servlet filter that:
1. Reads the `X-Tenant-ID` header from incoming requests
2. Stores it in SLF4J MDC for logging (all log lines include `tenantId`)
3. Makes it available for downstream data scoping

The platform shell's `useApi()` hook automatically sends this header with every API call.

## How it connects to the shell

The shell sends two headers with every API request:

```
Authorization: Bearer <jwt>     ← validated by SecurityConfig (OAuth2 resource server)
X-Tenant-ID: <org-id>          ← extracted by WebConfig tenant filter
```

This works with both Clerk and OIDC — the backend only validates the JWT against the configured `oidcIssuerUri` and doesn't care which provider issued it.

## Running locally

```bash
cd order-service

# Start PostgreSQL
docker compose -f docker/docker-compose.yaml up -d

# Run the app (port 8080)
./gradlew bootRun

# Or with local profile
./gradlew bootRun --args='--spring.profiles.active=local'
```

**Endpoints:**
- API: `http://localhost:8080`
- Health: `http://localhost:8080/actuator/health`
- Swagger UI: `http://localhost:8080/swagger-ui.html` (if openapi enabled)
- pgAdmin: `http://localhost:8432` (from docker-compose)
