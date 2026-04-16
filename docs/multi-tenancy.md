# Multi-Tenancy

Apps Generator produces a full-stack multi-tenant system where every database query is automatically scoped to the current tenant. No data can leak between tenants -- even a raw `findAll()` returns only the current tenant's rows.

## End-to-End Flow

The tenant ID flows through seven layers, from the browser to the database:

### 1. Frontend: ShellContextSync

After the user logs in and selects an organization, the platform shell syncs the tenant ID to a window global:

```typescript
// ShellContextSync.tsx (generated in platform-shell)
useEffect(() => {
  window.__SHELL_TENANT_ID__ = currentTenant?.id ?? null;
}, [currentTenant]);
```

With Clerk, `currentTenant` comes from `useOrganization()`. With OIDC, it comes from the custom `TenantProvider` that fetches `/api/tenants`.

### 2. API Client: X-Tenant-ID Header

The shared api-client package reads the window global and attaches it to every request:

```typescript
// context.ts (generated in api-client)
export function getShellTenantId(): string | null {
  return window.__SHELL_TENANT_ID__ || null;
}
```

```typescript
// client.ts (generated in api-client)
const tenantId = config.getTenantId();
if (tenantId) {
  headers["X-Tenant-ID"] = tenantId;
}
```

Every API call carries `X-Tenant-ID: <org-id>` alongside `Authorization: Bearer <jwt>`.

### 3. Shell Nginx: Header Pass-Through

The shell's nginx config proxies API requests to the gateway and passes tenant headers through:

```nginx
location /api/ {
    proxy_pass ${GATEWAY_URL};
    proxy_set_header X-Tenant-ID $http_x_tenant_id;
    proxy_set_header X-Correlation-ID $http_x_correlation_id;
}
```

### 4. Gateway: TenantHeaderFilter

The API gateway's `TenantHeaderFilter` (a `GlobalFilter`) extracts the tenant ID from the incoming request and forwards it to downstream backend services. It also adds the tenant ID to the SLF4J MDC for structured logging.

### 5. Backend WebConfig: Header Extraction

The backend's `WebConfig` defines a `OncePerRequestFilter` that extracts `X-Tenant-ID` from the request header and puts it into:
- The SLF4J **MDC** (for log correlation)
- The **TenantContext** (a thread-local holder used by the service and interceptor layers)

```java
String tenantId = request.getHeader("X-Tenant-ID");
if (tenantId != null && !tenantId.isBlank()) {
    MDC.put("tenantId", tenantId);
}
```

The filter cleans up MDC in a `finally` block after the request completes.

### 6. TenantFilterInterceptor: Hibernate @Filter

The `TenantFilterInterceptor` is a Spring `HandlerInterceptor` that runs before every controller method. It enables the Hibernate `tenantFilter` on the current session:

```java
@Override
public boolean preHandle(HttpServletRequest request, ...) {
    String tenantId = TenantContext.getCurrentTenantId();
    if (tenantId != null && !tenantId.isBlank()) {
        Session session = entityManager.unwrap(Session.class);
        session.enableFilter("tenantFilter")
               .setParameter("tenantId", tenantId);
    }
    return true;
}
```

Once enabled, the filter applies to all JPA queries in this request.

### 7. TenantAwareEntity: @FilterDef + @Filter

Every generated entity extends `TenantAwareEntity`, which defines the Hibernate filter:

```java
@MappedSuperclass
@FilterDef(
    name = "tenantFilter",
    parameters = @ParamDef(name = "tenantId", type = String.class),
    defaultCondition = "tenant_id = :tenantId"
)
@Filter(name = "tenantFilter")
public abstract class TenantAwareEntity {
    @Column(name = "tenant_id", nullable = false, updatable = false)
    private String tenantId;
    // ...
}
```

This causes Hibernate to automatically append `WHERE tenant_id = :tenantId` to every SELECT query on entities that extend `TenantAwareEntity`. This includes:
- `findAll()` (paginated or not)
- `findById()` (even by primary key)
- Custom JPQL queries
- Criteria API queries

## Service Layer: Write Isolation

For write operations, the generated service explicitly enforces tenant isolation:

- **Create**: Sets `tenantId` from `TenantContext.requireCurrentTenantId()` -- the caller cannot choose a different tenant
- **Update**: Fetches the existing entity (tenant-scoped by filter), then preserves the original `tenantId`
- **Delete**: Fetches first (tenant-scoped), then deletes -- a tenant cannot delete another tenant's data

## Integration Test Verification

The generated integration tests verify tenant isolation:

```java
// Create as tenant A
mockMvc.perform(post("/product")
    .header("X-Tenant-ID", "tenant-a")
    .content("{...}"))
    .andExpect(status().isCreated());

// Tenant B cannot see tenant A's data
mockMvc.perform(get("/product")
    .header("X-Tenant-ID", "tenant-b"))
    .andExpect(jsonPath("$.totalElements").value(0));

// Tenant B cannot access tenant A's record by ID
mockMvc.perform(get("/product/1")
    .header("X-Tenant-ID", "tenant-b"))
    .andExpect(status().isNotFound());
```

## Database Schema

Every tenant-scoped table includes a `tenant_id` column that is:
- `NOT NULL` -- every row must belong to a tenant
- `NOT UPDATABLE` -- the tenant cannot be changed after creation
- Indexed for query performance (via the Liquibase migration)

There is no separate tenant table. The `tenant_id` is an opaque string (typically the Clerk organization ID or OIDC tenant identifier) that flows from the frontend org switcher through to the database.
