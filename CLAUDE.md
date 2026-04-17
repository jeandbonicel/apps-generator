# Apps Generator — Claude Context

A Python CLI (`appgen`) that scaffolds full-stack multi-tenant applications from 6 templates.

## CLI Commands

### `appgen generate <template> [OPTIONS]`

| Option | Description | Valid for |
|--------|-------------|-----------|
| `-o, --output` | Output directory | all |
| `-s, --set key=value` | Set parameter (repeatable) | all |
| `--shell <path>` | Register MFE in shell's remotes.json | frontend-app |
| `--uikit <path>` | Link ui-kit (shadcn components + Tailwind theme) | frontend-app, platform-shell |
| `--gateway <path>` | Register route in gateway's routes.yaml | api-domain |
| `--api-client <path>` | Link api-client + generate TS types | frontend-app, platform-shell, api-domain |
| `--force` | Overwrite existing output | all |
| `--no-interactive` | Skip prompts | all |

### `appgen sync types --from <url> --to <path>`
Regenerate TypeScript types from a running backend's OpenAPI spec (`/v3/api-docs`).

### `appgen docker-compose <dir>`
Scan workspace, auto-generate docker-compose.yaml with all services.

### `appgen templates list|describe|validate|package`

## Templates (6)

### ui-kit
Shared component library: 26 shadcn/ui components + Recharts charts + Storybook.

| Param | Default | Description |
|-------|---------|-------------|
| `projectName` | required | Package name (kebab-case) |
| `nodeVersion` | 20 | Node.js version |
| `packageManager` | pnpm | npm, pnpm, yarn |

Components: Alert, Avatar, Badge, Breadcrumb, Button, Card, Chart, Checkbox, Dialog, DropdownMenu, Input, Label, Pagination, Progress, ScrollArea, Select, Separator, Sheet, Skeleton, Switch, Table, Tabs, Textarea, Toast/Toaster, Tooltip.

### api-client
Typed fetch wrapper with auth tokens, tenant headers, correlation IDs.

| Param | Default | Description |
|-------|---------|-------------|
| `projectName` | required | Package name |
| `apiBaseUrl` | /api | Default API base URL |

Exports: `createApiClient()`, `useApiClient()` (React hook), `ApiError`, context helpers. Window globals: `__SHELL_AUTH_TOKEN__`, `__SHELL_TENANT_ID__`.

### api-gateway
Spring Cloud Gateway BFF with JWT validation, tenant forwarding, correlation IDs, security headers.

| Param | Default | Description |
|-------|---------|-------------|
| `projectName` | required | Gateway name |
| `groupId` | com.example | Maven group ID |
| `basePackage` | com.example | Java package |
| `gatewayPort` | 8080 | Listening port |
| `oidcIssuerUri` | https://auth.example.com/realms/main | JWT issuer |

Features: `oauth2` (on), `docker` (on), `kubernetes` (on), `cicd` (on).

Filters: CorrelationIdFilter (UUID generation), TenantHeaderFilter (forwarding), SecurityHeadersFilter (OWASP headers).

### api-domain
Spring Boot 3 backend with DDD, PostgreSQL, Hibernate tenant filter, CRUD scaffolding.

| Param | Default | Description |
|-------|---------|-------------|
| `projectName` | required | Service name |
| `groupId` | com.example | Maven group ID |
| `basePackage` | com.example | Java package |
| `dbName` | (projectName) | PostgreSQL database |
| `oidcIssuerUri` | https://auth.example.com/realms/main | JWT issuer |
| `resources` | [] | JSON array of resource definitions |

Features: `database` (on), `oauth2` (on), `docker` (on), `kubernetes` (on), `cicd` (on), `openapi` (on).

**Resource JSON format:**
```json
[{
  "name": "product",
  "fields": [
    {"name": "name", "type": "string", "required": true, "maxLength": 100},
    {"name": "price", "type": "decimal", "required": true, "min": 0},
    {"name": "stock", "type": "integer"},
    {"name": "active", "type": "boolean"}
  ]
}]
```

**Field types:** string, text, integer, long, decimal, boolean, date, datetime.

**Constraints:** required, unique, maxLength, minLength, min, max, pattern.

**Per resource generates:** Entity (extends TenantAwareEntity with Hibernate @Filter), Repository, Service, Controller (CRUD endpoints), Create/Update/Response DTOs with Bean Validation, Liquibase migration, Integration test (Testcontainers).

**Tenant isolation:** TenantAwareEntity base class with `@FilterDef`/`@Filter` auto-scopes ALL queries by tenant_id. TenantFilterInterceptor enables filter per-request. Service layer sets tenantId on writes.

### frontend-app
React micro-frontend (Module Federation remote) with Vite, TypeScript, Tailwind.

| Param | Default | Description |
|-------|---------|-------------|
| `projectName` | required | App name |
| `devPort` | 5001 | Dev server port |
| `gatewayPort` | 8080 | API gateway port (dev proxy) |
| `pages` | [] | JSON array of page configs |

Features: `docker` (on), `kubernetes` (on), `cicd` (on), `tailwind` (on).

**Page config format:**
```json
[
  {"path": "dashboard", "label": "Dashboard", "resource": "product", "type": "dashboard",
   "fields": [{"name": "name", "type": "string"}, {"name": "price", "type": "decimal"}]},
  {"path": "list", "label": "All Products", "resource": "product", "type": "list",
   "fields": [{"name": "name", "type": "string"}, {"name": "price", "type": "decimal"}]},
  {"path": "new", "label": "New Product", "resource": "product", "type": "form",
   "fields": [{"name": "name", "type": "string", "required": true}, {"name": "price", "type": "decimal", "required": true}]}
]
```

**Page types:**
- `list` — table with useApiClient + useQuery, pagination, Card wrapper
- `form` — create form with validation, useMutation, Card wrapper
- `dashboard` — stat cards + bar chart (Recharts) + recent items table

When `--uikit` is linked, pages import shadcn components (Button, Input, Table, Card, etc.). Without ui-kit, falls back to plain HTML with matching Tailwind classes.

### platform-shell
React host app with Module Federation, OAuth2/Clerk auth, tenant switcher, i18n.

| Param | Default | Description |
|-------|---------|-------------|
| `projectName` | required | Platform name |
| `authProvider` | clerk | clerk or oidc |
| `clerkPublishableKey` | pk_test_REPLACE_ME | Clerk key |
| `oidcAuthority` | https://auth.example.com/realms/main | OIDC issuer |
| `apiBaseUrl` | /api | Backend API base URL |
| `devPort` | 5173 | Dev server port |
| `gatewayPort` | 8080 | Gateway port (dev proxy) |

Features: `docker` (on), `kubernetes` (on), `cicd` (on), `tailwind` (on).

Shell components: ShellContextSync (syncs auth/tenant to window globals), ErrorBoundary (catches MFE crashes), ToastProvider (with/without ui-kit).

Nginx: proxies /api/ to gateway via GATEWAY_URL env var. Security headers (CSP, X-Frame-Options).

## Auto-wiring

```
platform-shell ──(--uikit)──→ ui-kit
               ──(--api-client)──→ api-client
               ──(remotes.json)──→ frontend-app(s)
                                    ──(--uikit)──→ ui-kit
                                    ──(--api-client)──→ api-client

api-domain ──(--gateway)──→ api-gateway (routes.yaml)
           ──(--api-client)──→ api-client (TS types)
```

## Code structure

```
src/apps_generator/
├── cli/
│   ├── main.py              # Root CLI (Typer)
│   ├── generate.py          # Generate command + post-hooks orchestration
│   ├── sync.py              # Sync types from OpenAPI
│   ├── docker_compose.py    # Docker compose generation
│   └── generators/
│       ├── pages.py          # React page generation (list/form/dashboard)
│       ├── resources.py      # Java CRUD scaffolding
│       ├── types.py          # TypeScript type generation
│       ├── migrations.py     # Liquibase migrations
│       ├── shell.py          # Shell registration (remotes.json)
│       ├── gateway.py        # Gateway route registration
│       ├── linking.py        # Dependency linking (uikit/api-client)
│       └── toast.py          # Toast provider generation
├── core/
│   ├── generator.py          # Main generation orchestrator
│   ├── engine.py             # Jinja2 template rendering
│   ├── manifest.py           # Manifest parsing
│   └── parameters.py         # Parameter validation + context
├── templates/builtin/        # 6 template directories
├── models/                   # TemplateInfo, GenerationContext
└── utils/naming.py           # camel_case, pascal_case, snake_case, etc.
```

## Type mappings (resources.py constants)

| Type | Java | SQL | TypeScript |
|------|------|-----|-----------|
| string | String | VARCHAR(maxLength\|255) | string |
| text | String | TEXT | string |
| integer | Integer | INTEGER | number |
| long | Long | BIGINT | number |
| decimal | BigDecimal | DECIMAL(19,4) | number |
| boolean | Boolean | BOOLEAN | boolean |
| date | LocalDate | DATE | string |
| datetime | LocalDateTime | TIMESTAMP | string |

## CSS theme

All templates use the shadcn neutral theme (near-black primary, not blue):
- `--primary: 240 5.9% 10%` (near-black)
- `--radius: 0.5rem`
- `--chart-1..5` for Recharts colors

## Testing

78+ tests in `tests/`. Run: `.venv/bin/pytest tests/ -v`

## Conventions

- Template files use Jinja2 (`{{ variable }}`, `{% if %}`, `{% raw %}`)
- `.conditions.yaml` controls file inclusion based on feature flags
- Filenames support `__var__` and `__var|filter__` patterns
- All entities extend TenantAwareEntity (Hibernate @Filter for tenant isolation)
- Generated pages use inline styles for spacing (reliable across Module Federation)
- ui-kit Tailwind classes are safelisted in consumer builds (linking.py)
