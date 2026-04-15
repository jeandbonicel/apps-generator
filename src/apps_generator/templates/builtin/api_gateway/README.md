# api-gateway

Spring Cloud Gateway (BFF) — single entry point for all backend services with JWT validation, tenant forwarding, and automatic route management.

## What it generates

A reactive Spring Boot application using Spring Cloud Gateway that:
- Routes `/api/{service}/**` to the correct backend service
- Validates JWT tokens (OAuth2 resource server, reactive/WebFlux)
- Forwards `X-Tenant-ID` header to all downstream services
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
│   │   ├── SecurityConfig.java         # Reactive OAuth2 JWT validation
│   │   └── CorsConfig.java            # CORS for all routes
│   └── filter/
│       └── TenantHeaderFilter.java    # X-Tenant-ID forwarding + MDC logging
├── src/main/resources/
│   ├── application.yaml                # Gateway config
│   ├── application-local.yaml          # Local profile
│   └── routes.yaml                     # Route definitions (CLI-managed)
├── docker/
├── k8s/base/ + overlays/
└── .github/workflows/
```

## How it fits the stack

```
Browser → Shell (:5173)
  └─ /api/* → Gateway (:8080)
               ├─ /api/order/**     → order-service (:8081)
               ├─ /api/inventory/** → inventory-service (:8082)
               └─ JWT + X-Tenant-ID forwarded
```

## Running locally

```bash
./gradlew bootRun    # http://localhost:8080
```

**Endpoints:**
- Gateway: `http://localhost:8080`
- Health: `http://localhost:8080/actuator/health`
- Routes: `http://localhost:8080/actuator/gateway/routes`
