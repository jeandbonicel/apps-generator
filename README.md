# Apps Generator

A Python CLI that scaffolds full-stack projects from configurable templates. Generate production-ready backends, micro-frontends, and platform shells — with CI/CD, Docker, Kubernetes, and authentication baked in.

## Quick Start

```bash
# Install
pip install -e .

# 1. (Optional) Shared UI kit with shadcn/ui + Storybook
appgen generate ui-kit -o ./ui-kit -s projectName=my-ui-kit

# 2. API Gateway (single entry point for all backends)
appgen generate api-gateway -o ./gateway \
  -s projectName=my-gateway \
  -s groupId=com.example \
  -s basePackage=com.example.gateway

# 3. Backend services (--gateway auto-registers routes)
appgen generate api-domain -o ./order-service \
  -s projectName=order-service \
  -s groupId=com.example \
  -s basePackage=com.example.orders \
  --gateway ./gateway

appgen generate api-domain -o ./inventory-service \
  -s projectName=inventory-service \
  -s groupId=com.example \
  -s basePackage=com.example.inventory \
  --gateway ./gateway

# 4. Platform shell (--uikit links shared components)
appgen generate platform-shell -o ./my-platform \
  -s projectName=my-platform --uikit ./ui-kit

# 5. Micro-frontends (--shell auto-registers in shell)
appgen generate frontend-app -o ./orders -s projectName=orders -s devPort=5001 \
  -s 'pages=[{"path":"overview","label":"Overview"},{"path":"list","label":"Order List"}]' \
  --shell ./my-platform --uikit ./ui-kit

appgen generate frontend-app -o ./users -s projectName=users -s devPort=5002 \
  -s 'pages=[{"path":"directory","label":"Directory"},{"path":"roles","label":"Roles"}]' \
  --shell ./my-platform --uikit ./ui-kit
```

The CLI auto-wires everything:
- `--shell` registers MFEs in the shell's `remotes.json` (tabs, sidebar, routes)
- `--gateway` registers backends in the gateway's `routes.yaml` (API routing)
- `--uikit` links the shared component library (Tailwind theme, shadcn components)

## Built-in Templates

| Template | Description | Docs |
|----------|-------------|------|
| `platform-shell` | React host app with Module Federation, auth (Clerk/OIDC), org switcher, i18n | [README](src/apps_generator/templates/builtin/platform_shell/README.md) |
| `frontend-app` | React micro-frontend (Module Federation remote), Vite, TypeScript | [README](src/apps_generator/templates/builtin/frontend_app/README.md) |
| `api-gateway` | Spring Cloud Gateway (BFF) with JWT validation, route management, tenant forwarding | [README](src/apps_generator/templates/builtin/api_gateway/README.md) |
| `api-domain` | Spring Boot 3 backend with DDD, PostgreSQL, multi-tenant support | [README](src/apps_generator/templates/builtin/api_domain/README.md) |
| `ui-kit` | Shared component library with shadcn/ui, Tailwind CSS, Storybook | [README](src/apps_generator/templates/builtin/ui_kit/README.md) |

### `platform-shell`

React host application that orchestrates micro-frontends.

- **Authentication** — Clerk (default) or generic OIDC (Keycloak, Auth0, Azure AD)
- **Multi-tenant org switcher** — Clerk's `<OrganizationSwitcher />` or custom dropdown
- **Module Federation host** — loads child apps via horizontal tabs
- **Sub-page routing** — each MFE can define pages with a vertical sidebar
- **Runtime remote config** — `public/remotes.json` defines which micro-frontends to load (no rebuild needed)
- Playwright E2E tests, Docker, Kubernetes (Kustomize), GitHub Actions CI/CD

```
┌─────────────────────────────────────────────────────────────┐
│ Header: [Logo] [Org Switcher ▾]                   [User ▾] │
├──────────┬──────────┬───────────┬───────────────────────────┤
│  Orders  │ Inventory│  Users   │          (horizontal tabs) │
├──────────┴──────────┴───────────┴───────────────────────────┤
│ ┌──────────┐ ┌──────────────────────────────────────────┐   │
│ │ Overview │ │                                          │   │
│ │ List     │ │  Content: /orders/list                   │   │
│ │ Create   │ │  (loaded via Module Federation)          │   │
│ │          │ │                                          │   │
│ └──────────┘ └──────────────────────────────────────────┘   │
│ (vertical     (MFE content area)                            │
│  sidebar)                                                   │
└─────────────────────────────────────────────────────────────┘
```

### `frontend-app`

React micro-frontend that works as a Module Federation **remote**.

- Runs **standalone** for development (own `index.html` + dev server)
- Loads inside the **platform-shell** in production via `remoteEntry.js`
- Use `--shell` to **auto-register** in an existing shell project
- Use `--pages` to define **sub-pages** with a vertical sidebar (Overview, List, Create, etc.)
- Vite, TypeScript, Tailwind CSS, TanStack Router/Query
- Playwright E2E tests, Docker, Kubernetes, GitHub Actions

### `api-gateway`

Spring Cloud Gateway — single entry point for all backend services.

- **Route management** — `routes.yaml` auto-updated by `--gateway` flag
- **JWT validation** — OAuth2 resource server (reactive/WebFlux)
- **Tenant forwarding** — `X-Tenant-ID` header passed to all downstream services
- **CORS** — configured for all routes
- Docker, Kubernetes, GitHub Actions

### `api-domain`

Spring Boot 3 backend with Domain-Driven Design.

- **DDD layers**: domain, application, infrastructure, interfaces
- **PostgreSQL** + Liquibase migrations
- **OAuth2 resource server** with JWT validation
- **Multi-tenant** via `X-Tenant-ID` header (matches the shell's tenant switcher)
- Use `--gateway` to **auto-register** routes in an existing gateway
- OpenAPI/Swagger docs, Docker, Kubernetes, GitHub Actions

---

## Shell Linking — How `--shell` Works

When you generate a `frontend-app` with `--shell`, the CLI:

1. Generates the frontend app project with page components
2. Finds the shell's `public/remotes.json`
3. Appends a new entry with name, URL, menu label, and **pages metadata**
4. Deduplicates — running the same command twice won't create duplicates

```bash
# Generate shell (creates empty remotes.json)
appgen generate platform-shell -o ./my-platform -s projectName=my-platform

# Add apps with sub-pages (each updates remotes.json)
appgen generate frontend-app -o ./orders -s projectName=orders -s devPort=5001 \
  -s 'pages=[{"path":"overview","label":"Overview"},{"path":"list","label":"Order List"},{"path":"create","label":"Create Order"}]' \
  --shell ./my-platform
```

**Result in `my-platform/my-platform/public/remotes.json`:**
```json
[
  {
    "name": "orders",
    "url": "http://localhost:5001",
    "menuLabel": "Orders",
    "pages": [
      { "path": "overview", "label": "Overview" },
      { "path": "list", "label": "Order List" },
      { "path": "create", "label": "Create Order" }
    ]
  }
]
```

The shell reads this at startup:
- **Horizontal tabs** (below header): one per MFE app
- **Vertical sidebar** (inside each MFE): one link per page
- **Routes**: `/orders/overview`, `/orders/list`, `/orders/create`

Clicking the "Orders" tab navigates to `/orders/overview` (first page). The vertical sidebar lets you switch between pages. The MFE receives `activePage` and renders the matching page component.

You can also edit `remotes.json` manually to add, remove, or reorder apps without regenerating.

---

## Gateway Linking — How `--gateway` Works

When you generate an `api-domain` with `--gateway`, the CLI:

1. Generates the backend project as normal
2. Finds the gateway's `routes.yaml`
3. Adds a route entry with auto-assigned port
4. Derives the API path from the service name (`order-service` → `/api/order/**`)

```bash
appgen generate api-gateway -o ./gateway -s projectName=my-gateway

appgen generate api-domain -o ./order-service \
  -s projectName=order-service --gateway ./gateway

appgen generate api-domain -o ./inventory-service \
  -s projectName=inventory-service --gateway ./gateway
```

**Result in `gateway/my-gateway/src/main/resources/routes.yaml`:**
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: http://localhost:8081
          predicates:
            - Path=/api/order/**
          filters:
            - StripPrefix=2
        - id: inventory-service
          uri: http://localhost:8082
          predicates:
            - Path=/api/inventory/**
          filters:
            - StripPrefix=2
```

The gateway validates JWT tokens, forwards `X-Tenant-ID`, and routes to the correct backend. Ports are auto-assigned (8081, 8082, ...).

---

## Architecture

```
Browser → Shell (:5173)
  ├─ Static assets (HTML, JS, CSS)
  ├─ Auth: Clerk / OIDC
  ├─ i18n: EN / FR language switcher
  ├─ MFEs loaded via Module Federation:
  │   ├─ orders (:5001) → /orders/overview, /orders/list
  │   └─ users (:5002) → /users/directory, /users/roles
  └─ API calls → Gateway (:8080)
                   ├─ /api/order/**     → order-service (:8081)
                   ├─ /api/inventory/** → inventory-service (:8082)
                   └─ JWT validation + X-Tenant-ID forwarding
```

---

## Authentication

The platform shell supports two auth providers, selected via the `authProvider` parameter.

### Clerk (default)

The simplest option. Clerk handles login UI, user management, and organizations out of the box.

```bash
appgen generate platform-shell -o ./my-platform \
  -s projectName=my-platform \
  -s clerkPublishableKey=pk_test_xxxxx
```

**Setup:**
1. Create an account at [clerk.com](https://clerk.com)
2. Create an application, copy the **Publishable Key**
3. Enable **Organizations** in the Clerk dashboard
4. Create organizations and invite users

**What you get:**
- `@clerk/clerk-react` — single dependency
- `<ClerkProvider>` wraps the app
- `<SignInButton mode="modal">` — Clerk's hosted sign-in (no redirect, no Keycloak)
- `<UserButton />` — avatar + sign-out in the header
- `<OrganizationSwitcher />` — Clerk's built-in org/tenant dropdown
- `getToken()` for API calls (JWT with org claims)

**Environment variable:** set `VITE_CLERK_PUBLISHABLE_KEY` in `.env` to override the baked-in key.

### Generic OIDC (Keycloak, Auth0, Azure AD)

For self-hosted or enterprise identity providers.

```bash
appgen generate platform-shell -o ./my-platform \
  -s projectName=my-platform \
  -s authProvider=oidc \
  -s oidcAuthority=https://your-keycloak.com/realms/main \
  -s oidcClientId=my-platform
```

**What you get:**
- `oidc-client-ts` + `react-oidc-context`
- OAuth2 Authorization Code + PKCE flow
- Custom `<TenantSwitcher>` dropdown (fetches tenant list from your API)
- Custom `<TenantProvider>` with localStorage persistence
- Silent token renewal via iframe

**Local dev with Keycloak:**
```bash
docker run -d --name keycloak -p 8180:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:25.0 start-dev
```
Then create a realm, a public client with redirect URI `http://localhost:5173/*`, and test users.

### Auth flow

```
Browser → Shell (localhost:5173)
  ├─ Clerk: <SignInButton> opens modal → Clerk handles login → returns JWT
  │   OR
  ├─ OIDC: redirect to Keycloak/Auth0 → user logs in → redirect back with code → exchange for JWT
  │
  ├─ Tenant loaded:
  │   Clerk: useOrganization() reads active org from Clerk
  │   OIDC: TenantProvider fetches GET /api/tenants with Bearer token
  │
  └─ All API calls via useApi() include:
      Authorization: Bearer <jwt>
      X-Tenant-ID: <org-id>
```

---

## Local Development

### 1. Generate the full stack

```bash
# UI Kit
appgen generate ui-kit -o ./ui-kit -s projectName=my-ui-kit

# Gateway
appgen generate api-gateway -o ./gateway -s projectName=my-gateway \
  -s groupId=com.example -s basePackage=com.example.gateway

# Backends (auto-register in gateway)
appgen generate api-domain -o ./order-service \
  -s projectName=order-service -s groupId=com.example \
  -s basePackage=com.example.orders --gateway ./gateway

# Shell
appgen generate platform-shell -o ./my-platform \
  -s projectName=my-platform \
  -s clerkPublishableKey=pk_test_xxxxx --uikit ./ui-kit

# MFEs (auto-register in shell)
appgen generate frontend-app -o ./orders -s projectName=orders -s devPort=5001 \
  -s 'pages=[{"path":"overview","label":"Overview"},{"path":"list","label":"Order List"}]' \
  --shell ./my-platform --uikit ./ui-kit
```

### 2. Start the gateway + backends

```bash
cd order-service
docker compose -f docker/docker-compose.yaml up -d   # PostgreSQL
./gradlew bootRun --args='--server.port=8081'         # http://localhost:8081

cd gateway
./gradlew bootRun                                      # http://localhost:8080 (routes to backends)
```

### 3. Start the micro-frontends

```bash
cd orders && npm install && npm run build && npx vite preview --port 5001
```

### 4. Start the platform shell

```bash
cd my-platform && npm install && npm run build && npx vite preview --port 5173
```

### 5. Open `http://localhost:5173`

Sign in with Clerk. The shell proxies API calls through the gateway (`/api` → `:8080` → `:8081`).

### Running E2E tests

```bash
cd my-platform
npx playwright install chromium    # first time only
pnpm run e2e                        # headless
pnpm run e2e:ui                     # interactive UI
pnpm run e2e:debug                  # step-through debugger
```

### Ports reference

| Service | Port | Description |
|---------|------|-------------|
| Platform Shell | `5173` | Vite preview (host) |
| Orders MFE | `5001` | Vite preview (remote) |
| Users MFE | `5002` | Vite preview (remote) |
| API Gateway | `8080` | Spring Cloud Gateway (routes to backends) |
| Order Service | `8081` | Spring Boot backend |
| Inventory Service | `8082` | Spring Boot backend |
| PostgreSQL | `5432` | Database |
| pgAdmin | `5050` | DB admin UI |
| Storybook | `6006` | UI Kit component browser |
| Keycloak | `8180` | OIDC provider (if using `authProvider=oidc`) |

---

## Deployment

### Docker Compose

The CLI auto-generates a complete `docker-compose.yaml` from your workspace:

```bash
# After generating all projects in a directory:
appgen docker-compose .
```

This scans the workspace, detects all projects, and generates:
- **PostgreSQL** with per-service databases (auto-creates via init script)
- **Backend services** with correct DB URLs
- **API Gateway** with Docker service names (not localhost)
- **Micro-frontends** with CORS headers for Module Federation
- **Platform shell** with correct dependencies

Then run:
```bash
docker compose up --build
```

### Kubernetes

Each project has `k8s/` with Kustomize overlays:

```bash
# Deploy to dev
kubectl apply -k ./my-platform/k8s/overlays/dev
kubectl apply -k ./orders/k8s/overlays/dev
kubectl apply -k ./order-service/k8s/overlays/dev

# Deploy to prod (more replicas, higher limits)
kubectl apply -k ./my-platform/k8s/overlays/prod
```

### GitHub Actions CI/CD

Each project includes 3 workflows:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci.yaml` | PR to main | Build, lint, test, Playwright E2E |
| `build-and-push.yaml` | Push to main / tags | Docker build + push to container registry |
| `deploy.yaml` | Manual dispatch | Kustomize set-image + kubectl apply |

---

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
| `--shell` | Path to a platform-shell project. Auto-registers this frontend app in the shell (frontend-app only) |
| `--uikit` | Path to a ui-kit project. Adds it as a dependency and extends Tailwind config (frontend-app + platform-shell) |
| `--gateway` | Path to an api-gateway project. Auto-registers this backend's route in the gateway (api-domain only) |
| `--force` | Overwrite existing output directory |
| `--dry-run` | Show what would be generated without writing |
| `--no-interactive` | Disable interactive prompts for missing params |

### Inspect templates

```bash
appgen templates list                       # List all templates
appgen templates describe platform-shell    # Show parameters and features
appgen templates validate ./my-template     # Validate a custom template
appgen templates package ./my-template      # Package as tar.gz
```

### Generate Docker infrastructure

```bash
appgen docker-compose <workspace-dir>    # Scan and generate docker-compose.yaml
```

Scans the directory for all generated projects and produces a complete `docker-compose.yaml` with PostgreSQL (per-service databases), gateway (Docker service names), and all frontends/backends.

### Manage repositories

```bash
appgen repo add company https://templates.example.com/index.yaml
appgen repo add local /path/to/templates --type local
appgen repo list
appgen repo remove company
```

---

## Template Parameters

### platform-shell

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Project name (kebab-case) |
| `projectTitle` | derived | Display name |
| `authProvider` | `clerk` | Auth provider: `clerk` or `oidc` |
| `clerkPublishableKey` | `pk_test_REPLACE_ME` | Clerk publishable key (clerk only) |
| `oidcAuthority` | `https://auth.example.com/realms/main` | OIDC issuer URL (oidc only) |
| `oidcClientId` | `platform-shell` | OAuth2 client ID (oidc only) |
| `oidcScopes` | `openid profile email` | OAuth2 scopes (oidc only) |
| `apiBaseUrl` | `/api` | Backend API base URL |
| `tenantsEndpoint` | `/api/tenants` | Tenant list API endpoint (oidc only) |
| `nodeVersion` | `20` | Node.js version |
| `packageManager` | `pnpm` | npm, pnpm, or yarn |
| `containerRegistry` | `ghcr.io` | Container registry |
| `containerRegistryOrg` | `your-org` | Registry organization |
| `k8sNamespace` | `default` | Kubernetes namespace |

**Feature flags:** `docker`, `kubernetes`, `cicd`, `tailwind` (all default: on)

### frontend-app

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Project name (kebab-case) |
| `projectTitle` | derived | Display name |
| `exposedModule` | `./App` | Module Federation exposed module |
| `devPort` | `5001` | Dev server port |
| `pages` | `[]` | JSON array of `{"path","label"}` page configs for sub-routing |
| `apiBaseUrl` | `/api` | Backend API base URL |
| `nodeVersion` | `20` | Node.js version |
| `packageManager` | `pnpm` | npm, pnpm, or yarn |

**CLI-only option:** `--shell <path>` — auto-register in an existing platform-shell project (includes pages metadata)

**Feature flags:** `docker`, `kubernetes`, `cicd`, `tailwind`, `tanstackRouter` (all default: on)

### api-gateway

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Gateway name (kebab-case) |
| `groupId` **(required)** | `com.example` | Maven/Gradle group ID |
| `basePackage` **(required)** | `com.example` | Java base package |
| `javaVersion` | `21` | Java version (17 or 21) |
| `springBootVersion` | `3.3.0` | Spring Boot version |
| `springCloudVersion` | `2023.0.2` | Spring Cloud version |
| `gatewayPort` | `8080` | Gateway listening port |
| `oidcIssuerUri` | `https://auth.example.com/realms/main` | OIDC issuer URI |

**Feature flags:** `oauth2`, `docker`, `kubernetes`, `cicd` (all default: on)

### api-domain

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Project name (kebab-case) |
| `groupId` **(required)** | `com.example` | Maven/Gradle group ID |
| `basePackage` **(required)** | `com.example` | Java base package |
| `javaVersion` | `21` | Java version (17 or 21) |
| `springBootVersion` | `3.3.0` | Spring Boot version |
| `dbName` | derived | PostgreSQL database name |
| `oidcIssuerUri` | `https://auth.example.com/realms/main` | OIDC issuer URI |

**CLI-only option:** `--gateway <path>` — auto-register route in an existing api-gateway

**Feature flags:** `database`, `oauth2`, `docker`, `kubernetes`, `cicd`, `openapi` (all default: on)

---

## Creating Custom Templates

A template is a directory with this structure:

```
my-template/
├── manifest.yaml              # Template metadata and configuration
├── parameters-schema.json     # JSON Schema for parameter validation
├── parameters-defaults.yaml   # Default parameter values
└── files/                     # Template files (processed by Jinja2)
    └── __projectName__/       # Filename variables: __var__ or __var|filter__
        ├── src/
        └── ...
```

### Filename variables

| Pattern | Example input | Result |
|---------|---------------|--------|
| `__projectName__` | `order-service` | `order-service` |
| `__projectName\|pascal_case__` | `order-service` | `OrderService` |
| `__basePackage\|package_to_path__` | `com.example.orders` | `com/example/orders` |

### Available Jinja2 filters

`camel_case`, `pascal_case`, `snake_case`, `kebab_case`, `upper_snake_case`, `package_to_path`, `capitalize_first`, `title_case`

### Conditional files

Create a `.conditions.yaml` in any directory:

```yaml
docker: "features.docker"
SecurityConfig.java: "features.oauth2"
```

### Feature flags

```yaml
# manifest.yaml
features:
  - name: docker
    description: "Dockerfile and docker-compose"
    default: true
```

Toggle with: `-s features.docker=false`

---

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/ -v
ruff check src/
```

