# Security

Apps Generator adds security headers, CORS configuration, and OAuth2/JWT authentication across the full stack. Each layer adds its own defenses.

## Security Headers

### Shell Nginx

The platform shell's nginx config adds these headers to all responses:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Frame-Options` | `DENY` | Prevents clickjacking by blocking iframe embedding |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits referrer information to same-origin |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Disables access to sensitive browser APIs |
| `Content-Security-Policy` | See below | Restricts resource loading sources |

The CSP policy allows:
- Scripts and styles from `'self'` (styles also allow `'unsafe-inline'` for Tailwind)
- Images from `'self'`, `data:` URIs, and `https:`
- Connections to `'self'` and Clerk domains (`*.clerk.accounts.dev`, `*.clerk.com`)
- Frames blocked via `frame-ancestors 'none'`

### MFE Nginx

Each micro-frontend's nginx adds minimal security headers:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

MFE nginx also sets CORS headers (`Access-Control-Allow-Origin: *`) because Module Federation loads `remoteEntry.js` cross-origin from the shell.

### Gateway SecurityHeadersFilter

The API gateway adds security headers to every API response via a `GlobalFilter`:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Cache-Control` | `no-store` |

The `no-store` directive prevents caching of API responses that may contain tenant-specific data.

## CORS Configuration

### Gateway CorsConfig

The gateway defines a reactive `CorsWebFilter` with environment-based origin configuration:

```yaml
# application.yaml
cors:
  allowed-origin-patterns: "*"  # Override in production
```

The configuration allows:
- All standard HTTP methods (GET, POST, PUT, PATCH, DELETE, OPTIONS)
- All headers
- Credentials (cookies and Authorization headers)
- Exposed headers: `X-Tenant-ID`, `X-Correlation-ID`
- Preflight cache: 3600 seconds

In production, set `cors.allowed-origin-patterns` to your actual domain(s): `https://app.example.com,https://admin.example.com`.

### Backend CORS

Each backend's `WebConfig` also configures CORS via Spring MVC:
- `allowedOriginPatterns("*")` -- override in production
- Exposes `X-Tenant-ID` and `X-Correlation-ID` headers
- Allows credentials

## OAuth2 / JWT Authentication

### Gateway (WebFlux)

The gateway uses Spring Security's reactive OAuth2 resource server:

```java
// SecurityConfig.java (active when NOT "local" profile)
http.oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
```

- Health and actuator endpoints are public: `/actuator/health/**`, `/actuator/info`
- All other routes require a valid JWT
- JWT issuer is configured via `spring.security.oauth2.resourceserver.jwt.issuer-uri`

### Backend (Servlet)

Each backend service has its own `SecurityConfig`:

```java
// SecurityConfig.java (active when NOT "local" profile)
http.oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> {}))
```

- Health endpoints are public: `/actuator/health`, `/actuator/info`, `/api/health`
- OpenAPI endpoints are public (when enabled): `/v3/api-docs/**`, `/swagger-ui/**`
- All other endpoints require authentication
- Stateless session management (no server-side sessions)

### DevSecurityConfig (Local Development)

Both gateway and backend include a `DevSecurityConfig` activated by the `local` profile:

```java
@Profile("local")
public class DevSecurityConfig {
    // Permits all requests -- no JWT required
}
```

Run with `--spring.profiles.active=local` to develop without a running OIDC provider. Never use the `local` profile in production.

## Frontend Authentication

The platform shell supports two auth providers selected at generation time:

### Clerk (default)

- `@clerk/clerk-react` handles login, session management, and organizations
- `<SignInButton mode="modal">` opens Clerk's hosted sign-in
- `getToken()` returns a JWT with organization claims
- Set `VITE_CLERK_PUBLISHABLE_KEY` in `.env`

### Generic OIDC (Keycloak, Auth0, Azure AD)

- `oidc-client-ts` + `react-oidc-context` implement Authorization Code + PKCE
- Silent token renewal via iframe
- Custom `TenantSwitcher` dropdown fetches tenant list from your API
- Set `oidcAuthority` and `oidcClientId` at generation time

## Adding HTTPS

Generated projects do not include TLS configuration. In production, HTTPS is typically handled by:
- A reverse proxy or load balancer (nginx, AWS ALB, Cloudflare)
- Kubernetes Ingress with cert-manager
- A cloud provider's managed TLS termination

Add HSTS headers at the TLS termination point: `Strict-Transport-Security: max-age=63072000; includeSubDomains`.
