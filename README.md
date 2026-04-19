# Apps Generator

A Python CLI that scaffolds full-stack, multi-tenant applications from templates. Generate production-ready backends (Spring Boot), micro-frontends (React + Module Federation), API gateways, shared UI kits, and typed API clients -- with CRUD resources, tenant isolation, CI/CD, Docker, and Kubernetes baked in.

## Quick Start

```bash
pip install -e .

# 1. Shared UI kit (shadcn/ui + Tailwind + Storybook)
appgen generate ui-kit -o ./ui-kit -s projectName=my-ui-kit

# 2. Typed API client (shared fetch wrapper + TypeScript types)
appgen generate api-client -o ./api-client -s projectName=my-api-client

# 3. API Gateway (JWT validation, tenant forwarding, correlation IDs)
appgen generate api-gateway -o ./gateway \
  -s projectName=my-gateway \
  -s groupId=com.example \
  -s basePackage=com.example.gateway

# 4. Platform shell (host app, auth, org switcher, Module Federation)
appgen generate platform-shell -o ./my-platform \
  -s projectName=my-platform \
  -s clerkPublishableKey=pk_test_xxxxx \
  --uikit ./ui-kit --api-client ./api-client

# 5. Backend with CRUD resources + TypeScript types in api-client
appgen generate api-domain -o ./product-service \
  -s projectName=product-service \
  -s groupId=com.example \
  -s basePackage=com.example.products \
  -s 'resources=[{"name":"category","fields":[{"name":"name","type":"string","required":true}]},{"name":"product","fields":[{"name":"name","type":"string","required":true,"maxLength":255},{"name":"price","type":"decimal","required":true,"min":0},{"name":"status","type":"enum","required":true,"values":["active","inactive","archived"]},{"name":"categoryId","type":"reference","target":"category"},{"name":"active","type":"boolean"}]}]' \
  --gateway ./gateway --api-client ./api-client

# 6. Micro-frontend with data-aware pages (dashboard + list + grid + form + detail + edit)
appgen generate frontend-app -o ./products -s projectName=products -s devPort=5001 \
  -s 'pages=[
    {"path":"overview","label":"Overview","resource":"product","type":"dashboard","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"active","type":"boolean"}
    ]},
    {"path":"list","label":"Products","resource":"product","type":"list","rowLink":"view","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"active","type":"boolean"}
    ]},
    {"path":"catalog","label":"Catalog","resource":"product","type":"grid","rowLink":"view","fields":[
      {"name":"name","type":"string"},
      {"name":"description","type":"string"},
      {"name":"price","type":"decimal"},
      {"name":"active","type":"boolean"}
    ]},
    {"path":"view","label":"Product Details","resource":"product","type":"detail","fields":[
      {"name":"name","type":"string"},
      {"name":"price","type":"decimal"},
      {"name":"active","type":"boolean"},
      {"name":"description","type":"text"}
    ]},
    {"path":"create","label":"New Product","resource":"product","type":"form","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"description","type":"text"}
    ]},
    {"path":"edit","label":"Edit Product","resource":"product","type":"edit","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"description","type":"text"}
    ]}
  ]' \
  --shell ./my-platform --uikit ./ui-kit --api-client ./api-client

# 7. Generate Docker Compose and start (shared libs auto-build during linking)
appgen docker-compose .
docker compose up --build
```

The CLI auto-wires everything:
- `--shell` registers MFEs in the shell's `remotes.json` (tabs, sidebar, routes)
- `--gateway` registers backends in the gateway's `routes.yaml` (API routing)
- `--uikit` links the shared component library (Tailwind theme, shadcn components)
- `--api-client` links the typed API client and generates TypeScript types from `resources`

## Built-in Templates

| Template | Description | Docs |
|----------|-------------|------|
| `platform-shell` | React host app with Module Federation, auth (Clerk/OIDC), org switcher, i18n | [README](src/apps_generator/templates/builtin/platform_shell/README.md) |
| `frontend-app` | React micro-frontend (Module Federation remote), Vite, TypeScript | [README](src/apps_generator/templates/builtin/frontend_app/README.md) |
| `api-gateway` | Spring Cloud Gateway with JWT, route management, tenant forwarding, security headers | [README](src/apps_generator/templates/builtin/api_gateway/README.md) |
| `api-domain` | Spring Boot 3 backend with DDD, PostgreSQL, multi-tenant, CRUD resources | [README](src/apps_generator/templates/builtin/api_domain/README.md) |
| `api-client` | Typed fetch client with auth/tenant headers, correlation IDs, React context | [README](src/apps_generator/templates/builtin/api_client/README.md) |
| `ui-kit` | Shared component library with shadcn/ui, Tailwind CSS, Storybook | [README](src/apps_generator/templates/builtin/ui_kit/README.md) |

## Architecture

```
Browser
  |
  v
Shell (nginx :80)  -----> Gateway (:8080) -----> product-service (:8081) --> PostgreSQL
  |                          |                    inventory-service (:8082) --> PostgreSQL
  |  Security headers:       |  Filters:
  |  CSP, HSTS, X-Frame      |  CorrelationIdFilter (generates/forwards X-Correlation-ID)
  |                          |  TenantHeaderFilter  (forwards X-Tenant-ID)
  |  Module Federation:      |  SecurityHeadersFilter (nosniff, DENY, no-store)
  |  MFE remotes loaded      |  JWT validation (OAuth2 resource server)
  |  cross-origin via        |
  |  remoteEntry.js          |  Route config: routes.yaml
  |                          |    /api/product/** -> product-service
  |  Auth: Clerk/OIDC        |    /api/inventory/** -> inventory-service
  |  Tenant: org switcher    |
  |                          |  Backend layers:
  |  API Client:             |    Controller -> Service -> Repository -> DB
  |  X-Correlation-ID        |    TenantFilterInterceptor enables Hibernate @Filter
  |  X-Tenant-ID             |    Every query auto-scoped: WHERE tenant_id = :tenantId
  |  Authorization: Bearer   |
```

See [docs/architecture.md](docs/architecture.md) for the full request flow.

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | Step-by-step tutorial: generate a complete app from scratch |
| [Resources and CRUD](docs/resources-and-crud.md) | Resource config, field types, constraints, generated code |
| [Multi-Tenancy](docs/multi-tenancy.md) | How tenant isolation works end-to-end |
| [API Client and Types](docs/api-client-and-types.md) | Typed API client, generated TypeScript types, sync command |
| [Security](docs/security.md) | Security headers, CORS, OAuth2/JWT configuration |
| [Observability](docs/observability.md) | Correlation IDs, structured logging, error tracing |
| [Testing](docs/testing.md) | Integration tests, Testcontainers, Python test suite |
| [Deployment](docs/deployment.md) | Docker Compose, Kubernetes, GitHub Actions |

## CLI Reference

### Generate a project

```bash
appgen generate <template> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-o, --output` | Output directory (default: `./<projectName>`) |
| `-p, --parameters` | YAML file with parameter values |
| `-s, --set` | Set a parameter: `-s key=value` (repeatable) |
| `--shell` | Path to platform-shell. Auto-registers this MFE (frontend-app only) |
| `--uikit` | Path to ui-kit. Adds as dependency (frontend-app, platform-shell) |
| `--gateway` | Path to api-gateway. Auto-registers route (api-domain only) |
| `--api-client` | Path to api-client. Adds as dependency and generates TS types from resources (frontend-app, platform-shell, api-domain) |
| `--force` | Overwrite existing output directory |
| `--dry-run` | Show what would be generated without writing |
| `--no-interactive` | Disable interactive prompts for missing params |

### Sync types from a running backend

```bash
appgen sync types --from http://localhost:8081/v3/api-docs --to ./api-client
```

Fetches the OpenAPI spec from a running Spring Boot service and regenerates TypeScript interfaces in the api-client package. Bumps the patch version automatically.

### Inspect templates

```bash
appgen templates list                       # List all templates
appgen templates describe platform-shell    # Show parameters and features
appgen templates validate ./my-template     # Validate a custom template
appgen templates package ./my-template      # Package as tar.gz
```

### Generate Docker Compose

```bash
appgen docker-compose <workspace-dir>
```

Scans the directory for all generated projects and produces a complete `docker-compose.yaml` with PostgreSQL, gateway, backends, and frontends.

### Manage repositories

```bash
appgen repo add company https://templates.example.com/index.yaml
appgen repo list
appgen repo remove company
```

## Creating Custom Templates

A template is a directory with `manifest.yaml`, `parameters-schema.json`, `parameters-defaults.yaml`, and a `files/` directory processed by Jinja2. Filename variables use `__var__` or `__var|filter__` syntax. Conditional files use `.conditions.yaml`.

Available Jinja2 filters: `camel_case`, `pascal_case`, `snake_case`, `kebab_case`, `upper_snake_case`, `package_to_path`, `capitalize_first`, `title_case`.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/ -v        # 76+ tests covering all generators
ruff check src/         # Linting
```
