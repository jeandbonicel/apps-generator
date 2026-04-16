# api-domain

Spring Boot 3 backend with Domain-Driven Design architecture, PostgreSQL, and multi-tenant support.

## What it generates

A Gradle-based Spring Boot application with:
- **DDD layered architecture** -- domain, application, infrastructure, interfaces
- **PostgreSQL** with Liquibase migrations
- **OAuth2 resource server** -- validates JWTs from Clerk, Keycloak, or any OIDC provider
- **Multi-tenant** -- extracts `X-Tenant-ID` header for data scoping with ORM-level isolation
- **CRUD resource generation** -- full REST endpoints, JPA entities, services, and tests from a JSON spec
- **Correlation ID tracing** -- extracts `X-Correlation-ID` from requests, adds to MDC for logging
- **Structured error handling** -- `GlobalExceptionHandler` with consistent JSON error responses
- **OpenAPI/Swagger** documentation
- **Integration tests** with Testcontainers
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

# With CRUD resources and api-client type generation
appgen generate api-domain -o ./catalog-service \
  -s projectName=catalog-service \
  -s groupId=com.example \
  -s basePackage=com.example.catalog \
  -s resources='[{"name":"product","fields":[{"name":"name","type":"string","required":true},{"name":"price","type":"decimal","required":true},{"name":"description","type":"text"}]}]' \
  --api-client ./my-api-client
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
| `resources` | `[]` | JSON array of resource configs (see below) |

**CLI-only options:**
- `--gateway <path>` -- register this service in an existing api-gateway's `routes.yaml`
- `--api-client <path>` -- generate TypeScript types in the api-client package

## Resources parameter

The `resources` parameter accepts a JSON array of resource definitions. Each resource generates a full CRUD stack: JPA entity, repository, service, REST controller, DTOs, Liquibase migration, and integration test.

```bash
-s resources='[
  {
    "name": "product",
    "fields": [
      {"name": "name", "type": "string", "required": true},
      {"name": "price", "type": "decimal", "required": true},
      {"name": "description", "type": "text"},
      {"name": "active", "type": "boolean"}
    ]
  },
  {
    "name": "category",
    "fields": [
      {"name": "name", "type": "string", "required": true}
    ]
  }
]'
```

Supported field types: `string`, `text`, `integer`, `long`, `decimal`, `boolean`, `date`, `datetime`.

Each resource generates:
- **Entity** extending `TenantAwareEntity` with Hibernate tenant filter
- **Repository** (Spring Data JPA)
- **Service** with CRUD operations (tenant-scoped via `TenantContext`)
- **REST Controller** with `GET` (list + paginated), `GET /{id}`, `POST`, `PUT`, `DELETE`
- **DTOs** -- response, create request, update request (with `@Valid` annotations)
- **Liquibase migration** -- `CREATE TABLE` with all fields + `tenant_id` column
- **Integration test** -- full CRUD test against Testcontainers PostgreSQL

See `docs/resources-and-crud.md` for detailed documentation on the resource schema.

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
│   │   │   ├── TenantAwareEntity.java    # Base class: Hibernate @Filter for tenant isolation
│   │   │   └── Product.java              # Generated per resource
│   │   ├── exception/
│   │   │   └── NotFoundException.java
│   │   ├── repository/
│   │   │   └── ProductRepository.java    # Generated per resource
│   │   └── service/
│   │       └── ProductService.java       # Generated per resource
│   ├── application/
│   ├── infrastructure/
│   │   ├── config/
│   │   │   ├── SecurityConfig.java       # OAuth2 JWT validation (@Profile("!local"))
│   │   │   ├── DevSecurityConfig.java    # Permits all (@Profile("local"))
│   │   │   ├── WebConfig.java            # CORS, tenant filter, correlation ID extraction
│   │   │   └── OpenApiConfig.java        # Swagger setup
│   │   ├── tenant/
│   │   │   ├── TenantContext.java         # ThreadLocal tenant holder
│   │   │   └── TenantFilterInterceptor.java  # Enables Hibernate tenant filter per request
│   │   ├── web/
│   │   │   └── GlobalExceptionHandler.java   # Structured JSON error responses
│   │   └── persistence/
│   └── interfaces/rest/
│       ├── HealthController.java
│       ├── ProductController.java        # Generated per resource
│       └── dto/
│           ├── ProductResponse.java
│           ├── CreateProductRequest.java
│           └── UpdateProductRequest.java
├── src/main/resources/
│   ├── application.yaml
│   ├── application-local.yaml
│   └── db/changelog/                     # Liquibase migrations
│       ├── db.changelog-master.yaml
│       └── 001-create-product.yaml       # Generated per resource
├── src/test/java/.../
│   ├── AbstractIntegrationTest.java      # Testcontainers base class
│   └── ProductControllerTest.java        # Generated per resource
├── docker/
│   ├── Dockerfile                        # Multi-stage (JDK build + JRE runtime)
│   └── docker-compose.yaml               # App + PostgreSQL + pgAdmin
├── k8s/base/ + overlays/
└── .github/workflows/
```

## Tenant isolation

The template implements ORM-level tenant isolation using Hibernate's `@Filter` mechanism. See `docs/multi-tenancy.md` for the full design.

**TenantAwareEntity** is the base class for all tenant-scoped entities. It defines a Hibernate `@FilterDef` with a `tenantFilter` that adds `WHERE tenant_id = :tenantId` to every query automatically.

**TenantFilterInterceptor** is a Spring `HandlerInterceptor` that runs before each request handler. It reads the tenant ID from `TenantContext` (set by the `WebConfig` filter) and enables the Hibernate filter on the current session.

The result: every JPA query on entities extending `TenantAwareEntity` -- including `findAll()`, custom JPQL, and Criteria queries -- is automatically scoped to the current tenant. No manual `WHERE` clauses needed.

```
Request arrives with X-Tenant-ID: org-123
  → WebConfig filter stores "org-123" in TenantContext + MDC
  → TenantFilterInterceptor enables Hibernate filter with tenantId="org-123"
  → productRepository.findAll() → SELECT ... WHERE tenant_id = 'org-123'
```

## Correlation ID tracing

The `WebConfig` servlet filter extracts the `X-Correlation-ID` header from incoming requests and adds it to the SLF4J MDC. This means every log line from that request includes the correlation ID.

The gateway generates the correlation ID (see api-gateway docs). The backend receives it, logs with it, and includes it in error responses via `GlobalExceptionHandler`.

## Error handling

`GlobalExceptionHandler` (`@RestControllerAdvice`) catches exceptions and returns structured JSON:

```json
{
  "timestamp": "2024-09-17T14:00:00Z",
  "status": 400,
  "error": "Bad Request",
  "message": "Validation failed",
  "correlationId": "a1b2c3d4-...",
  "fieldErrors": [
    { "field": "name", "message": "must not be blank" }
  ]
}
```

Handled exceptions:
- `NotFoundException` -- 404
- `MethodArgumentNotValidException` -- 400 with field-level errors
- `IllegalStateException` -- 400
- Generic `Exception` -- 500 (message hidden for security)

The `correlationId` field is included when present in the MDC, enabling end-to-end request tracing from the browser to the error response.

## DevSecurityConfig

Two security configurations coexist using Spring profiles:

- **`SecurityConfig`** (`@Profile("!local")`) -- production config, validates JWTs via the OIDC issuer
- **`DevSecurityConfig`** (`@Profile("local")`) -- permits all requests, disables CSRF, so you can develop without a running OIDC provider

Activate the local profile:

```bash
./gradlew bootRun --args='--spring.profiles.active=local'
```

## Integration tests

The generated `AbstractIntegrationTest` base class:
- Starts a real PostgreSQL via **Testcontainers** (`postgres:16-alpine`)
- Configures Spring datasource properties dynamically
- Provides `MockMvc` for HTTP request testing
- Uses the `test` profile (security permits all)

Each generated resource gets a `*ControllerTest` that extends this base class and tests the full CRUD lifecycle: create, read, list, update, delete -- all against a real database.

## Multi-tenant support

The `WebConfig.java` includes a servlet filter that:
1. Reads the `X-Tenant-ID` header from incoming requests
2. Stores it in `TenantContext` (ThreadLocal) and SLF4J MDC for logging
3. The `TenantFilterInterceptor` enables the Hibernate `@Filter` using this value

The platform shell's `useApi()` hook automatically sends this header with every API call.

## How it connects to the shell

The shell sends two headers with every API request:

```
Authorization: Bearer <jwt>     -- validated by SecurityConfig (OAuth2 resource server)
X-Tenant-ID: <org-id>          -- extracted by WebConfig tenant filter
```

This works with both Clerk and OIDC -- the backend only validates the JWT against the configured `oidcIssuerUri` and doesn't care which provider issued it.

## Running locally

```bash
cd order-service

# Start PostgreSQL
docker compose -f docker/docker-compose.yaml up -d

# Run the app (port 8080)
./gradlew bootRun

# Or with local profile (no OIDC required)
./gradlew bootRun --args='--spring.profiles.active=local'
```

**Endpoints:**
- API: `http://localhost:8080`
- Health: `http://localhost:8080/actuator/health`
- Swagger UI: `http://localhost:8080/swagger-ui.html` (if openapi enabled)
- pgAdmin: `http://localhost:8432` (from docker-compose)
