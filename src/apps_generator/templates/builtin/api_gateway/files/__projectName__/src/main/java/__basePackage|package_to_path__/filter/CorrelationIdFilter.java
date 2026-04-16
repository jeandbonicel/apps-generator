package {{ basePackage }}.filter;

import org.slf4j.MDC;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

/**
 * Generates a correlation ID for every request and forwards it downstream.
 * <p>
 * If the request already carries an {@code X-Correlation-ID} header (e.g. from
 * an upstream load balancer), it is preserved. Otherwise a new UUID is generated.
 * The ID is added to the MDC for logging and returned in the response header.
 */
@Component
public class CorrelationIdFilter implements GlobalFilter, Ordered {

    public static final String CORRELATION_HEADER = "X-Correlation-ID";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String correlationId = exchange.getRequest().getHeaders().getFirst(CORRELATION_HEADER);
        if (correlationId == null || correlationId.isBlank()) {
            correlationId = UUID.randomUUID().toString();
        }

        MDC.put("correlationId", correlationId);

        // Forward to downstream services
        ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
            .header(CORRELATION_HEADER, correlationId)
            .build();

        // Include in response so the frontend can log it
        String finalCorrelationId = correlationId;
        exchange.getResponse().getHeaders().add(CORRELATION_HEADER, correlationId);

        return chain.filter(exchange.mutate().request(mutatedRequest).build())
            .doFinally(signal -> MDC.remove("correlationId"));
    }

    @Override
    public int getOrder() {
        return -2; // Run before tenant filter
    }
}
