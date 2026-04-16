# api-gateway

Spring Cloud Gateway (BFF) -- single entry point for all backend services with JWT validation, tenant forwarding, correlation ID tracing, and security headers.

## What it generates

A reactive Spring Boot application using Spring Cloud Gateway that:
- Routes `/api/{service}/**` to the correct backend service
- Validates JWT tokens (OAuth2 resource server, reactive/WebFlux)
- Forwards `X-Tenant-ID` header to all downstream services
- Generates and forwards `X-Correlation-ID` for end-to-end request tracing
- Adds security headers to every response
- Provides CORS configuration for all routes
- Has a `routes.yaml` config file auto-updated by the CLI

## Usage

```bash
# Generate gateway
appgen generate api-gateway -o ./gateway \
  -s projectName=my-gateway \
  -s groupId=com.example \
  -s basePackage=com.example.gateway

# Register backend services (auto-updates routes.yaml)
appgen generate api-domain -o ./order-service \
  -s projectName=order-service --gateway ./gateway

appgen generate api-domain -o ./inventory-service \
  -s projectName=inventory-service --gateway ./gateway
```

After registration, `routes.yaml` contains:
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: http://localhost:8081
          predicates:
            - Path=/api/order/**
          filters:
            - StripPrefix=2
        - id: inventory-service
          uri: http://localhost:8082
          predicates:
            - Path=/api/inventory/**
          filters:
            - StripPrefix=2
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Gateway name (kebab-case) |
| `groupId` **(required)** | `com.example` | Maven/Gradle group ID |
| `basePackage` **(required)** | `com.example` | Java base package |
| `javaVersion` | `21` | Java version (17 or 21) |
| `springBootVersion` | `3.3.0` | Spring Boot version |
| `springCloudVersion` | `2023.0.2` | Spring Cloud version |
| `gatewayPort` | `8080` | Listening port |
| `oidcIssuerUri` | `https://auth.example.com/realms/main` | OIDC issuer URI |

## Feature flags

| Feature | Default | Description |
|---------|---------|-------------|
| `oauth2` | on | JWT validation via OIDC |
| `docker` | on | Dockerfile + docker-compose |
| `kubernetes` | on | Kustomize base + dev/prod overlays |
| `cicd` | on | GitHub Actions workflows |

## Generated structure

```
my-gateway/
├── build.gradle.kts                    # Spring Cloud Gateway + WebFlux
├── src/main/java/.../
│   ├── MyGatewayApplication.java
│   ├── config/
│   │   ├── SecurityConfig.java         # Reactive OAuth2 JWT validation (@Profile("!local"))
│   │   ├── DevSecurityConfig.java      # Permits all (@Profile("local"))
│   │   └── CorsConfig.java            # CORS for all routes
│   └── filter/
│       ├── TenantHeaderFilter.java    # X-Tenant-ID forwarding + MDC logging
│       ├── CorrelationIdFilter.java   # Generates/forwards X-Correlation-ID
│       └── SecurityHeadersFilter.java # Response security headers
├── src/main/resources/
│   ├── application.yaml                # Gateway config + log pattern with correlationId
│   ├── application-local.yaml          # Local profile
│   └── routes.yaml                     # Route definitions (CLI-managed)
├── docker/
├── k8s/base/ + overlays/
└── .github/workflows/
```

## CorrelationIdFilter

The `CorrelationIdFilter` is a `GlobalFilter` that runs before all other filters (order: -2). It provides end-to-end request tracing across the entire stack.

For each request:
1. Checks for an existing `X-Correlation-ID` header (e.g., from an upstream load balancer)
2. If absent, generates a new UUID
3. Adds the correlation ID to the SLF4J MDC for structured logging
4. Forwards the header to downstream services (mutates the request)
5. Returns the header in the response so the frontend can capture it

The api-client also generates its own correlation ID per request. The gateway's ID is authoritative for backend-to-backend tracing, while the client's ID is useful for browser-side logging.

The log pattern includes the correlation ID:

```
%d{ISO8601} [%X{correlationId}] [%X{tenantId}] %-5level %logger{36} - %msg%n
```

## SecurityHeadersFilter

The `SecurityHeadersFilter` is a `GlobalFilter` (order: 0) that adds security headers to every API response:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer leakage |
| `Cache-Control` | `no-store` | Prevents caching of API responses |

These headers apply to all gateway responses. The platform shell's nginx config adds additional headers (CSP, Permissions-Policy) for the frontend.

## DevSecurityConfig

Two security configurations coexist using Spring profiles:

- **`SecurityConfig`** (`@Profile("!local")`) -- production config, validates JWTs via the reactive OAuth2 resource server
- **`DevSecurityConfig`** (`@Profile("local")`) -- permits all exchanges, disables CSRF, so you can develop without a running OIDC provider

Activate the local profile:

```bash
./gradlew bootRun --args='--spring.profiles.active=local'
```

The `DevSecurityConfig` uses `@EnableWebFluxSecurity` since the gateway is reactive (WebFlux-based), unlike the servlet-based api-domain.

## How it fits the stack

```
Browser --> Shell (:5173)
  |-- /api/* --> Gateway (:8080)
                  |-- /api/order/**     --> order-service (:8081)
                  |-- /api/inventory/** --> inventory-service (:8082)
                  |-- JWT + X-Tenant-ID + X-Correlation-ID forwarded
                  |-- Security headers added to responses
```

## Running locally

```bash
./gradlew bootRun    # http://localhost:8080

# Or with local profile (no OIDC required)
./gradlew bootRun --args='--spring.profiles.active=local'
```

**Endpoints:**
- Gateway: `http://localhost:8080`
- Health: `http://localhost:8080/actuator/health`
- Routes: `http://localhost:8080/actuator/gateway/routes`
