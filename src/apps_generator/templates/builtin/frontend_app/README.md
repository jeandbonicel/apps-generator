# frontend-app

React micro-frontend that works as a Module Federation **remote**. Runs standalone for development or loads inside the `platform-shell` host in production.

## What it generates

A Vite + React + TypeScript application that:
- Exposes its root component via `remoteEntry.js` for Module Federation
- Runs as a standalone SPA for independent development
- Reads auth tokens and tenant context from the shell when loaded as a remote
- Generates **data-aware pages** (list tables, create forms) when configured with `resource` + `type`
- Imports typed API client from the shared api-client package when linked via `--api-client`
- Includes Playwright E2E tests

## Usage

```bash
# Generate and auto-register in an existing shell
appgen generate frontend-app -o ./orders \
  -s projectName=orders \
  -s devPort=5001 \
  --shell ./my-platform

# Multiple micro-frontends, each linked to the same shell
appgen generate frontend-app -o ./users -s projectName=users -s devPort=5002 --shell ./my-platform
appgen generate frontend-app -o ./reports -s projectName=reports -s devPort=5003 --shell ./my-platform

# With data-aware pages (dashboard + list + form) and linked api-client
appgen generate frontend-app -o ./catalog \
  -s projectName=catalog \
  -s devPort=5001 \
  -s pages='[
    {"path":"overview","label":"Overview","resource":"product","type":"dashboard","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"active","type":"boolean"}
    ]},
    {"path":"products","label":"Products","resource":"product","type":"list","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"active","type":"boolean"}
    ]},
    {"path":"products/new","label":"Add Product","resource":"product","type":"form","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"description","type":"text"}
    ]}
  ]' \
  --shell ./my-platform \
  --api-client ./my-api-client
```

The `--shell` flag:
1. Generates the frontend app project
2. Appends an entry to the shell's `public/remotes.json`
3. Deduplicates -- running the same command twice won't create duplicates

The `--api-client` flag:
1. Adds the api-client package as a `file:` dependency
2. Enables typed imports: `import type { Product } from "my-api-client"`

You can also generate without `--shell` and manually edit `remotes.json` later:

```bash
appgen generate frontend-app -o ./orders -s projectName=orders -s devPort=5001
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Project name (kebab-case) |
| `projectTitle` | derived | Display name |
| `nodeVersion` | `20` | Node.js version |
| `packageManager` | `pnpm` | npm, pnpm, or yarn |
| `apiBaseUrl` | `/api` | Backend API base URL |
| `exposedModule` | `./App` | Module Federation exposed module name |
| `devPort` | `5001` | Dev server port |
| `gatewayPort` | `8080` | API gateway port (for dev proxy) |
| `pages` | `[]` | JSON array of page configs (see below) |
| `containerRegistry` | `ghcr.io` | Container registry |
| `containerRegistryOrg` | `your-org` | Registry organization |
| `k8sNamespace` | `default` | Kubernetes namespace |

**CLI-only options:**
- `--shell <path>` -- path to an existing platform-shell project
- `--api-client <path>` -- path to an api-client project (adds as dependency)

## Pages parameter

The `pages` parameter accepts a JSON array of page configurations. Each entry generates a route and a React component.

### Simple pages (no data fetching)

```json
[
  {"path": "overview", "label": "Overview"},
  {"path": "settings", "label": "Settings"}
]
```

These generate placeholder components with a heading and description.

### Data-aware pages

Pages with `resource` and `type` fields generate components that fetch data from the backend using `useApiClient()` and TanStack Query. Three page types are supported: `list`, `form`, and `dashboard`.

**List page** (`type: "list"`):

```json
{
  "path": "products",
  "label": "Products",
  "resource": "product",
  "type": "list",
  "fields": [
    {"name": "name", "type": "string", "required": true},
    {"name": "price", "type": "decimal", "required": true},
    {"name": "active", "type": "boolean"}
  ]
}
```

Generates a component with:
- `useApiClient()` from the shared api-client
- `useQuery` from TanStack Query with `PageResponse<Product>` typing
- A table with columns derived from `fields`
- Pagination controls (previous/next) with page state
- Loading and error states
- Type-aware cell rendering (decimals formatted with `.toFixed(2)`, booleans as Yes/No)

Optional `"rowLink": "<sub-path>"` on the page config makes each row clickable and pushes `<sub-path>?id={row.id}` through the MFE router (also supported on `grid`). Absent → rows stay inert, unchanged legacy behaviour.

**Form page** (`type: "form"`):

```json
{
  "path": "products/new",
  "label": "Add Product",
  "resource": "product",
  "type": "form",
  "fields": [
    {"name": "name", "type": "string", "required": true},
    {"name": "price", "type": "decimal", "required": true},
    {"name": "description", "type": "text"}
  ]
}
```

Generates a component with:
- `useApiClient()` from the shared api-client
- `useMutation` from TanStack Query with `CreateProductRequest` typing
- Form inputs derived from `fields` with type-appropriate controls:
  - `string` -- text input
  - `text` -- textarea
  - `integer` / `long` / `decimal` -- number input (decimal uses `step="0.01"`)
  - `boolean` -- checkbox
  - `date` -- date input
- Required field indicators
- Success/error feedback messages
- Automatic query invalidation on successful creation

**Dashboard page** (`type: "dashboard"`):

```json
{
  "path": "overview",
  "label": "Overview",
  "resource": "product",
  "type": "dashboard",
  "fields": [
    {"name": "name", "type": "string", "required": true},
    {"name": "price", "type": "decimal", "required": true},
    {"name": "active", "type": "boolean"}
  ]
}
```

Generates a component with:
- Stat cards showing aggregate counts and totals for the resource
- A bar chart visualizing data -- auto-picks the first numeric field for values and the first string field for category grouping
- A recent items table showing the latest records
- Uses `ChartContainer`, `ChartTooltip`, and `ChartLegend` from the ui-kit
- Recharts (`BarChart`, `Bar`, `XAxis`, `YAxis`) comes as a dependency of the ui-kit -- no extra install needed

### TypeScript types

Data-aware pages import types from the linked api-client:

```typescript
import { useApiClient } from "my-api-client/react";
import type { Product, CreateProductRequest, PageResponse } from "my-api-client";
```

These types are generated when the backend is created with `--api-client` (see the api-client README).

## Feature flags

| Feature | Default | Description |
|---------|---------|-------------|
| `docker` | on | Dockerfile (nginx) + docker-compose |
| `kubernetes` | on | Kustomize base + dev/prod overlays |
| `cicd` | on | GitHub Actions (CI, build-push, deploy) |
| `tailwind` | on | Tailwind CSS + PostCSS |
| `tanstackRouter` | on | TanStack Router for routing |

## Generated structure

```
orders/
├── package.json
├── vite.config.ts               # Module Federation remote (exposes ./App)
├── tsconfig.json
├── playwright.config.ts
├── index.html                    # Standalone dev entry
├── src/
│   ├── main.tsx                  # Standalone bootstrap
│   ├── App.tsx                   # Root component (exposed as remote)
│   ├── pages.ts                  # Page registry (maps paths to components)
│   ├── routes/
│   │   ├── HomePage.tsx
│   │   ├── OverviewPage.tsx      # Generated dashboard page (if type: "dashboard")
│   │   ├── ProductsPage.tsx      # Generated list page (if type: "list")
│   │   └── ProductsNewPage.tsx   # Generated form page (if type: "form")
│   ├── components/
│   ├── router/                   # Lightweight internal MFE router
│   │   ├── MfeRouter.tsx         # Provider + hooks (basePath, subPath, navigate)
│   │   ├── SubRoute.tsx          # Declarative route matching (/:id, /:id/edit)
│   │   ├── Link.tsx              # Internal navigation links
│   │   └── index.ts              # Re-exports
│   ├── hooks/useApi.ts           # Reads shell context or runs standalone
│   ├── services/api.ts
│   └── types/index.ts
├── e2e/                          # Playwright E2E tests
│   ├── app.spec.ts
│   ├── navigation.spec.ts
│   └── api.spec.ts
├── docker/
├── k8s/base/ + overlays/
└── .github/workflows/
```

## How Module Federation works

**As a remote (loaded by shell):**
The shell reads `public/remotes.json` which lists this app's URL. When a user clicks "Orders" in the sidebar, `RemoteAppLoader` lazy-loads `http://localhost:5001/assets/remoteEntry.js` and renders the exposed `./App` component.

**Standalone (development):**
`main.tsx` bootstraps the app with its own `QueryClient` and `BrowserRouter`. The `useApi` hook falls back to defaults when `window.__SHELL_CONTEXT__` is not available.

## How linking works

```
appgen generate frontend-app --shell ./my-platform -s projectName=orders -s devPort=5001

  1. Creates ./orders/ project
  2. Finds ./my-platform/<projectName>/public/remotes.json
  3. Appends: { "name": "orders", "url": "http://localhost:5001", "menuLabel": "Orders" }

Shell startup:
  main.tsx -> loadRemotes() -> fetches /remotes.json
  App.tsx  -> getRemotes()  -> creates <Route path="/orders/*"> for each entry
  Sidebar  -> getRemotes()  -> renders <NavLink to="/orders"> for each entry
```

## Sub-path routing within pages

Each page can have its own internal routes using `<SubRoute>` and `<Link>`:

```tsx
// src/routes/ListPage.tsx
import { SubRoute, Link, useSubPath } from "../router";

export function ListPage() {
  return (
    <>
      <SubRoute path="/">
        <h1>Orders</h1>
        <Link to="/123">View Order 123</Link>
      </SubRoute>

      <SubRoute path="/:id">
        <OrderDetail />
      </SubRoute>

      <SubRoute path="/:id/edit">
        <OrderEdit />
      </SubRoute>
    </>
  );
}

function OrderDetail() {
  const { params, navigate } = useSubPath();
  return (
    <div>
      <h1>Order {params.id}</h1>
      <Link to={`/${params.id}/edit`}>Edit</Link>
    </div>
  );
}
```

**How it works:**
- The shell catches `/orders/list/*` with a wildcard route
- The shell passes `basePath="/orders/list"` to the MFE
- `MfeRouterProvider` derives the sub-path from `window.location.pathname`
- `<SubRoute path="/:id">` matches `/123` and extracts `params.id = "123"`
- `<Link to="/123/edit">` navigates to `/orders/list/123/edit` (basePath + subPath)
- Browser back/forward works via `popstate` listener

**In standalone mode** (`npm run dev`), `basePath="/"` so the full URL is the sub-path. Navigate to `http://localhost:5001/123` to test.

## Running locally

```bash
cd orders
pnpm install
pnpm run dev          # http://localhost:5001
pnpm run e2e          # Playwright tests
pnpm run build        # Production build (includes remoteEntry.js)
```
