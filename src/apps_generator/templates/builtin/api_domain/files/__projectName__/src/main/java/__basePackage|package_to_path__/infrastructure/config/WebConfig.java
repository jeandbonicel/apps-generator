package {{ basePackage }}.infrastructure.config;

import {{ basePackage }}.infrastructure.tenant.TenantFilterInterceptor;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.io.IOException;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    public static final String TENANT_HEADER = "X-Tenant-ID";
    public static final String CORRELATION_HEADER = "X-Correlation-ID";

    private final TenantFilterInterceptor tenantFilterInterceptor;

    public WebConfig(TenantFilterInterceptor tenantFilterInterceptor) {
        this.tenantFilterInterceptor = tenantFilterInterceptor;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
            .allowedOriginPatterns("*")
            .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
            .allowedHeaders("*")
            .exposedHeaders(TENANT_HEADER, CORRELATION_HEADER)
            .allowCredentials(true)
            .maxAge(3600);
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(tenantFilterInterceptor);
    }

    /**
     * Filter that extracts the X-Tenant-ID and X-Correlation-ID headers and
     * places them in the MDC for logging. Runs before the interceptor so
     * TenantContext is available when the Hibernate filter is enabled.
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
                String correlationId = request.getHeader(CORRELATION_HEADER);
                if (correlationId != null && !correlationId.isBlank()) {
                    MDC.put("correlationId", correlationId);
                }
                try {
                    filterChain.doFilter(request, response);
                } finally {
                    MDC.remove("tenantId");
                    MDC.remove("correlationId");
                }
            }
        };
    }
}
