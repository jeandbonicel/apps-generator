After building the same multi-tenant platform architecture over and over -- React shell, micro-frontends, Spring Boot backends, API gateway, shared UI kit, tenant isolation, auth -- I decided to automate it.

**apps-generator** is a Python CLI that scaffolds a complete full-stack tenant app from a few commands. You describe your resources, and it generates everything: backend CRUD with tenant isolation, typed API client, data-fetching frontend pages with charts, Docker Compose, Kubernetes manifests, and CI/CD pipelines.

## What it generates

6 templates that wire together automatically:

- **platform-shell** -- React host app with Module Federation, Clerk/OIDC auth, org switcher, i18n (EN/FR)
- **frontend-app** -- React micro-frontends with data-aware pages (list tables, create forms, dashboards with Recharts)
- **api-domain** -- Spring Boot 3 backends with DDD architecture, PostgreSQL, Hibernate tenant filter, CRUD from resource schema
- **api-gateway** -- Spring Cloud Gateway with JWT validation, tenant header forwarding, correlation IDs
- **api-client** -- Typed TypeScript fetch client shared across all MFEs, with auto-generated types from resource schema
- **ui-kit** -- 26 shadcn/ui components + Recharts charts + Storybook

## How it works

```bash
# Generate infrastructure
appgen generate ui-kit -o ./ui-kit -s projectName=my-ui-kit
appgen generate api-client -o ./api-client -s projectName=my-api-client
appgen generate api-gateway -o ./gateway -s projectName=my-gateway \
  -s basePackage=com.example.gateway

# Generate a backend with CRUD resources
appgen generate api-domain -o ./product-service \
  -s projectName=product-service \
  -s basePackage=com.example.products \
  -s 'resources=[{
    "name": "product",
    "fields": [
      {"name": "name", "type": "string", "required": true},
      {"name": "price", "type": "decimal", "required": true},
      {"name": "stock", "type": "integer"}
    ]
  }]' \
  --gateway ./gateway --api-client ./api-client

# Generate the shell + a micro-frontend with pages
appgen generate platform-shell -o ./shell -s projectName=my-platform \
  --uikit ./ui-kit --api-client ./api-client

appgen generate frontend-app -o ./products -s projectName=products \
  -s 'pages=[
    {"path":"dashboard","label":"Dashboard","resource":"product","type":"dashboard"},
    {"path":"list","label":"Products","resource":"product","type":"list"},
    {"path":"new","label":"New Product","resource":"product","type":"form"}
  ]' \
  --shell ./shell --uikit ./ui-kit --api-client ./api-client

# Generate Docker Compose and start everything
appgen docker-compose .
docker compose up --build
```

Open `http://localhost` and you have a working multi-tenant app with auth, CRUD, tenant isolation, charts, and i18n.

## What makes it different

### Tenant isolation at the ORM level

Every entity extends `TenantAwareEntity` which has a Hibernate `@Filter` that automatically adds `WHERE tenant_id = :tenantId` to every query. Even `findAll()` is tenant-scoped. You cannot leak data across tenants.

### Resource schema is the single source of truth

You define fields once in JSON. The CLI generates:

- Java entity with JPA annotations
- Spring Data repository with tenant-scoped queries
- Service layer with CRUD operations
- REST controller with validation
- Create/Update/Response DTOs with Bean Validation
- Liquibase database migration
- Integration test with Testcontainers
- TypeScript interfaces in the shared API client

Backend and frontend types match by construction -- no manual sync needed.

### Data-aware pages

When you specify `"type": "list"` or `"type": "form"` on a page, the generator creates a real component with data fetching:

- **List pages** get a shadcn Table with pagination and `useQuery`
- **Form pages** get typed inputs with validation and `useMutation`
- **Dashboard pages** get stat cards and Recharts bar charts

### Everything wires together

- `--shell` registers MFEs in the shell's `remotes.json`
- `--gateway` registers routes in the gateway's `routes.yaml`
- `--uikit` links the shared component library with the Tailwind theme
- `--api-client` generates TypeScript types and links the shared fetch client

No manual configuration between projects.

## The stack

| Layer | Technology |
|-------|-----------|
| Shell | React 18, Module Federation, Clerk/OIDC, i18next |
| MFEs | React 18, Vite, TanStack Query, TypeScript |
| UI Kit | 26 shadcn/ui components, Recharts, Tailwind CSS, Storybook |
| Gateway | Spring Cloud Gateway, JWT, correlation IDs, security headers |
| Backend | Spring Boot 3, JPA/Hibernate, PostgreSQL, Liquibase, Testcontainers |
| Infra | Docker Compose, Kubernetes (Kustomize), GitHub Actions CI/CD |

## Built-in security

- Correlation ID tracing across the full stack (shell -> gateway -> backend)
- Security headers: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- CORS configuration with environment-based allowed origins
- OAuth2/JWT validation with dev escape hatch (`@Profile("local")`)
- Structured error responses with correlation IDs for debugging

## Open source

The project is GPL v3 and on GitHub:

**[https://github.com/jeandbonicel/apps-generator](https://github.com/jeandbonicel/apps-generator)**

- 89+ automated tests
- Full EN/FR i18n support
- Comprehensive docs covering architecture, security, multi-tenancy, and deployment
- Contribution guide with PR templates and CI on every PR

If you build multi-tenant SaaS apps and are tired of scaffolding the same architecture every time, give it a try. Feedback and contributions welcome.
