package {{ basePackage }}.infrastructure.tenant;

import jakarta.persistence.EntityManager;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.hibernate.Session;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * Interceptor that enables the Hibernate tenant filter for every request.
 * <p>
 * When a request carries an {@code X-Tenant-ID} header, this interceptor
 * opens the Hibernate session and enables the {@code tenantFilter} defined
 * in {@link {{ basePackage }}.domain.model.TenantAwareEntity}.
 * <p>
 * After this interceptor runs, <strong>every JPA query</strong> on entities
 * that extend {@code TenantAwareEntity} will automatically include
 * {@code WHERE tenant_id = :tenantId} — even {@code findAll()}, custom
 * JPQL, and Criteria queries.
 */
@Component
public class TenantFilterInterceptor implements HandlerInterceptor {

    private final EntityManager entityManager;

    public TenantFilterInterceptor(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String tenantId = TenantContext.getCurrentTenantId();
        if (tenantId != null && !tenantId.isBlank()) {
            Session session = entityManager.unwrap(Session.class);
            session.enableFilter("tenantFilter").setParameter("tenantId", tenantId);
        }
        return true;
    }
}
