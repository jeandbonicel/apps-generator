package {{ basePackage }}.infrastructure.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.io.IOException;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    public static final String TENANT_HEADER = "X-Tenant-ID";

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
            .allowedOriginPatterns("*")
            .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
            .allowedHeaders("*")
            .exposedHeaders(TENANT_HEADER)
            .allowCredentials(true)
            .maxAge(3600);
    }

    /**
     * Filter that extracts the X-Tenant-ID header and places it in the MDC
     * for logging and downstream processing.
     * <p>
     * The tenant ID is available via {@code TenantContext.getCurrentTenantId()}
     * in services and repositories for tenant-scoped queries.
     */
    @Bean
    public OncePerRequestFilter tenantContextFilter() {
        return new OncePerRequestFilter() {
            @Override
            protected void doFilterInternal(HttpServletRequest request,
                                            HttpServletResponse response,
                                            FilterChain filterChain)
                    throws ServletException, IOException {
                String tenantId = request.getHeader(TENANT_HEADER);
                if (tenantId != null && !tenantId.isBlank()) {
                    MDC.put("tenantId", tenantId);
                }
                try {
                    filterChain.doFilter(request, response);
                } finally {
                    MDC.remove("tenantId");
                }
            }
        };
    }
}
