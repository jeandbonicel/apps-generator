# Architecture

Apps Generator produces a full-stack, multi-tenant architecture with six template types that compose into a single deployable system.

## Request Flow

```
Browser
  |
  |  1. User authenticates via Clerk or OIDC
  |  2. Shell sets window.__SHELL_TENANT_ID__ and __SHELL_AUTH_TOKEN__
  |  3. API client attaches headers to every request:
  |       Authorization: Bearer <jwt>
  |       X-Tenant-ID: <org-id>
  |       X-Correlation-ID: <uuid>
  |
  v
Shell (nginx :80)
  |
  |  - Serves static assets (HTML, JS, CSS)
  |  - Loads MFE remotes via Module Federation (remoteEntry.js)
  |  - Proxies /api/* requests to the gateway
  |  - Passes X-Correlation-ID and X-Tenant-ID headers through
  |  - Adds security headers: CSP, X-Frame-Options DENY, HSTS, nosniff
  |
  v
API Gateway (Spring Cloud Gateway :8080)
  |
  |  Filter chain (ordered):
  |    1. CorrelationIdFilter  -- preserves or generates X-Correlation-ID, adds to MDC
  |    2. TenantHeaderFilter   -- forwards X-Tenant-ID to downstream services
  |    3. SecurityHeadersFilter -- adds nosniff, DENY, no-store to responses
  |    4. JWT validation        -- OAuth2 resource server (WebFlux)
  |
  |  Routes from routes.yaml:
  |    /api/product/**   -> product-service:8081
  |    /api/inventory/** -> inventory-service:8082
  |
  v
Backend Service (Spring Boot :8081)
  |
  |  WebConfig filter:
  |    - Extracts X-Tenant-ID and X-Correlation-ID from headers
  |    - Places both in SLF4J MDC for structured logging
  |    - Sets TenantContext for the current request
  |
  |  TenantFilterInterceptor:
  |    - Enables Hibernate @Filter on every request
  |    - All JPA queries auto-scoped: WHERE tenant_id = :tenantId
  |
  |  DDD layers:
  |    Controller -> Service -> Repository -> PostgreSQL
  |    (REST)       (business)  (JPA)         (per-service DB)
  |
  v
PostgreSQL (per-service database)
```

## Template Composition

Each template generates an independent project. CLI flags wire them together:

| Template | Role | Wired by |
|----------|------|----------|
| `ui-kit` | Shared React component library (shadcn/ui, Tailwind) | `--uikit` adds as npm dependency |
| `api-client` | Typed fetch wrapper with auth/tenant headers | `--api-client` adds as npm dependency |
| `api-gateway` | Single entry point, JWT validation, routing | `--gateway` registers backend routes |
| `platform-shell` | Host app, Module Federation, auth, org switcher | `--shell` registers MFE remotes |
| `api-domain` | Spring Boot backend with DDD, PostgreSQL, CRUD | `--resources` generates entities, APIs, tests |
| `frontend-app` | React MFE with pages, TanStack Router/Query | `--shell` registers in shell |

## Module Federation

The platform shell is a Module Federation **host**. Each frontend-app is a **remote**.

- The shell reads `public/remotes.json` at startup to discover remotes
- Each remote exposes `./App` via `remoteEntry.js`
- In development, remotes run standalone on their own port
- In production, remotes are served by nginx and loaded cross-origin by the shell
- The shell provides horizontal tabs (one per MFE) and a vertical sidebar (pages within each MFE)

## Gateway Routing

The gateway uses `routes.yaml` to map URL prefixes to backend services. When you run `appgen generate api-domain --gateway ./gateway`, the CLI auto-appends a route entry with an auto-assigned port. The `StripPrefix=2` filter removes `/api/<service>` before forwarding.

## Tenant Isolation

Tenant isolation spans the full stack. See [Multi-Tenancy](multi-tenancy.md) for the complete flow from the browser org switcher down to the Hibernate `@Filter` that auto-scopes every database query.

## Correlation ID Tracing

Every request gets a unique correlation ID that flows through every layer: frontend -> shell nginx -> gateway -> backend -> logs -> error responses. See [Observability](observability.md) for details.
