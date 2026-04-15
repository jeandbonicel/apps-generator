package {{ basePackage }}.filter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Component
public class TenantHeaderFilter implements GlobalFilter, Ordered {
    private static final Logger log = LoggerFactory.getLogger(TenantHeaderFilter.class);
    private static final String TENANT_HEADER = "X-Tenant-ID";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String tenantId = exchange.getRequest().getHeaders().getFirst(TENANT_HEADER);

        if (tenantId != null) {
            MDC.put("tenantId", tenantId);
            log.debug("Routing request for tenant: {}", tenantId);

            // Ensure tenant header is forwarded downstream
            ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                .header(TENANT_HEADER, tenantId)
                .build();

            return chain.filter(exchange.mutate().request(mutatedRequest).build())
                .doFinally(signal -> MDC.remove("tenantId"));
        }

        return chain.filter(exchange);
    }

    @Override
    public int getOrder() {
        return -1; // Run before other filters
    }
}
