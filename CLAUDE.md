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

**Field types:** string, text, integer, long, decimal, boolean, date, datetime, enum.

**Enum fields** use a `values` array: `{"name": "status", "type": "enum", "values": ["active", "inactive"]}`. Generates Java enum class, `@Enumerated(EnumType.STRING)` on entity, TypeScript union type (`"active" | "inactive"`), and `<select>` dropdown in forms.

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
- `list` — table with useApiClient + useQuery, pagination, Card wrapper. Null-safe rendering (shows "—" for null values).
- `form` — create form with type-aware inputs (datetime picker, number, textarea, checkbox, enum select dropdowns). Resource lookups auto-detected (e.g. `dogName` field renders as dropdown fetching from `/dog` API). useMutation, Card wrapper.
- `dashboard` — stat cards + bar chart (Recharts) + recent items table
- `detail` — read-only single-record view as a definition list inside a Card. Reads `id` from `?id=` query string, fetches `GET /{resource}/{id}` via useQuery. Type-aware value rendering: decimal → `toFixed(2)`, date/datetime → `toLocaleDateString()`, boolean → Badge ("Yes"/"No"), enum → Badge with value, text → `whitespace-pre-wrap`. Shows a Skeleton placeholder per field while loading; falls back to `t("missingId")` when `id` is absent.
- `grid` — responsive card-grid (1 col mobile / 2 md / 3 lg) for a resource collection. Same paginated query as `list`. First string field becomes the CardTitle, second becomes CardDescription; remaining fields drop into the card body as label/value pairs. Enum and boolean values render as Badges for fast visual scanning. Null-safe, shows empty state spanning all grid columns.

**Smart form features:**
- `enum` fields with `values` array → `<select>` dropdown with predefined options
- `datetime` fields → `<input type="datetime-local">`
- `date` fields → `<input type="date">`
- `text` fields → `<textarea>`
- `boolean` fields → checkbox
- Resource lookups: when a field name matches `{resource}Name` or `{resource}Id` and that resource exists in the pages config, the form auto-generates a `<select>` dropdown populated from the API, with "Create one first" message when empty.

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
│       ├── pages/            # React page generation package
│       │   ├── __init__.py   # parse_pages, find_project_root, dispatcher
│       │   ├── registry.py   # PageTypeRegistry + PageContext
│       │   ├── base.py       # page_target() + detect_lookup() helpers
│       │   ├── list_type.py
│       │   ├── form_type.py
│       │   ├── dashboard_type.py
│       │   ├── detail_type.py
│       │   └── grid_type.py
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
| enum | Java enum class | VARCHAR | union type (e.g. `"a" \| "b"`) |

## CSS theme

All templates use the shadcn neutral theme (near-black primary, not blue):
- `--primary: 240 5.9% 10%` (near-black)
- `--radius: 0.5rem`
- `--chart-1..5` for Recharts colors

## i18n / Translations

- Both shell and frontend-app use `i18next` + `react-i18next`
- Supported languages: English (en), French (fr). Fallback: en
- Translation files: `src/i18n/locales/en.json` and `fr.json`
- Shell syncs language to MFEs via `window.__SHELL_LANGUAGE__` + event
- All UI strings use `t("key")` — no hardcoded English in components
- Generated pages (list/form/dashboard/detail/grid) use `useTranslation()` for all UI text
- Translation keys: loading, noDataFound, previous, next, create, creating, createdSuccessfully, failedToLoad, etc.

**Adding a new language:** Copy `en.json` to `<lang>.json`, translate values, add to `i18n/index.ts` resources.

**Translation tests:** `test_translations.py` verifies EN/FR key parity, no empty values, essential keys present, no hardcoded English in components.

## Testing

89+ tests in `tests/`. Run: `.venv/bin/pytest tests/ -v`

Key test modules:
- `test_translations.py` — EN/FR completeness, no hardcoded English
- `test_resources.py` — CRUD scaffolding, tenant isolation
- `test_types_and_pages.py` — TypeScript types, data-aware pages
- `test_gateway_and_linking.py` — Gateway routes, api-client linking
- `test_e2e_generation.py` — Full-stack workflow
- `test_error_boundary_and_toast.py` — ErrorBoundary, ToastProvider

## Conventions

- Template files use Jinja2 (`{{ variable }}`, `{% if %}`). For GitHub Actions `${{ }}` expressions, use `{{ '${{ ... }}' }}` (NOT `{% raw %}` which breaks with `trim_blocks`).
- `.conditions.yaml` controls file inclusion based on feature flags
- Filenames support `__var__` and `__var|filter__` patterns
- All entities extend TenantAwareEntity (Hibernate @Filter for tenant isolation)
- Generated pages use inline styles for spacing (reliable across Module Federation)
- ui-kit Tailwind classes are safelisted in consumer builds (linking.py)
- All UI strings must use i18n `t("key")` — tests enforce this
- Every EN key must have a matching FR translation — tests enforce this
