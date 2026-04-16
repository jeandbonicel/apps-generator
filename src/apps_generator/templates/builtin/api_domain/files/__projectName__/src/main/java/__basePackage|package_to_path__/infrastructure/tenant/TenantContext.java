package {{ basePackage }}.infrastructure.tenant;

import org.slf4j.MDC;

/**
 * Request-scoped tenant context.
 * <p>
 * The tenant ID is set by the filter in WebConfig from the X-Tenant-ID header
 * and stored in the SLF4J MDC (thread-local). This class provides a convenient
 * static accessor used by services and repositories to scope queries by tenant.
 */
public final class TenantContext {

    private static final String MDC_KEY = "tenantId";

    private TenantContext() {}

    /**
     * Get the current tenant ID for this request.
     *
     * @return tenant ID or {@code null} if not set
     */
    public static String getCurrentTenantId() {
        return MDC.get(MDC_KEY);
    }

    /**
     * Get the current tenant ID, throwing if not present.
     *
     * @return tenant ID (never null)
     * @throws IllegalStateException if no tenant ID is set for this request
     */
    public static String requireCurrentTenantId() {
        String tenantId = MDC.get(MDC_KEY);
        if (tenantId == null || tenantId.isBlank()) {
            throw new IllegalStateException("No tenant ID set for current request. Is the X-Tenant-ID header missing?");
        }
        return tenantId;
    }
}
