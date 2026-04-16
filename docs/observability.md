# Observability

Apps Generator includes correlation ID tracing and structured logging across the full stack. Every request can be traced from the browser through to backend logs using a single UUID.

## Correlation ID Flow

```
Browser (api-client)
  |  Generates: X-Correlation-ID: <uuid> via crypto.randomUUID()
  |
  v
Shell Nginx
  |  Passes through: proxy_set_header X-Correlation-ID $http_x_correlation_id
  |
  v
API Gateway -- CorrelationIdFilter (order: -2, runs first)
  |  If X-Correlation-ID header exists: preserves it
  |  If missing: generates a new UUID
  |  Adds to SLF4J MDC: MDC.put("correlationId", id)
  |  Forwards to downstream: mutates request with header
  |  Returns in response: X-Correlation-ID header
  |  Cleans up: MDC.remove("correlationId") in doFinally
  |
  v
Backend -- WebConfig tenantContextFilter
  |  Extracts X-Correlation-ID from request header
  |  Adds to SLF4J MDC: MDC.put("correlationId", id)
  |  Cleans up in finally block after request completes
  |
  v
Backend Logs
  [correlationId] [tenantId] LEVEL logger - message
```

### Key Design Decisions

- The **api-client** generates the correlation ID, so it is available before the request leaves the browser
- The **gateway** preserves existing IDs (from the frontend or an upstream load balancer) and only generates if missing
- The **gateway** returns the correlation ID in the response header so the frontend can log it
- Both gateway and backend place the ID in the **SLF4J MDC** for structured logging
- Both clean up the MDC after the request to prevent thread-local leaks

## Log Format

Backend services use Spring Boot's default logging with MDC variables. Configure the log pattern in `application.yaml`:

```yaml
logging:
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss} [%X{correlationId}] [%X{tenantId}] %-5level %logger{36} - %msg%n"
```

Example log output:

```
2025-01-15 10:30:45 [a1b2c3d4-e5f6-7890-abcd-ef1234567890] [org_abc123] INFO  c.e.products.interfaces.rest.ProductController - Listing products page=0 size=20
2025-01-15 10:30:45 [a1b2c3d4-e5f6-7890-abcd-ef1234567890] [org_abc123] DEBUG c.e.products.domain.service.ProductService - Found 15 products for tenant
```

Both log lines share the same correlation ID, making it easy to trace a request across components.

## Error Responses

The `ApiError` class on the frontend includes the correlation ID:

```typescript
class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
    public readonly correlationId?: string,
  ) { ... }
}
```

When an API call fails, the correlation ID is available for debugging:

```typescript
try {
  await api.post("/product", data);
} catch (error) {
  if (error instanceof ApiError) {
    console.error(`Request failed (correlation: ${error.correlationId})`);
    // Show to user: "Error. Reference: a1b2c3d4-e5f6-..."
  }
}
```

Users can report the correlation ID, and operators can search backend logs for the matching request.

## Tenant ID in Logs

The tenant ID is also placed in the MDC by the backend's `WebConfig` filter. This allows log aggregation and filtering by tenant -- useful for debugging tenant-specific issues or auditing access patterns.

## Gateway Filter Ordering

The gateway filters execute in this order:

| Order | Filter | Responsibility |
|-------|--------|---------------|
| -2 | `CorrelationIdFilter` | Generate/forward correlation ID |
| -1 | `TenantHeaderFilter` | Forward X-Tenant-ID |
| 0 | `SecurityHeadersFilter` | Add security response headers |
| -- | Spring Security | JWT validation |
