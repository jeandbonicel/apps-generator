# api-client

Shared TypeScript API client library with auth token injection, tenant headers, correlation IDs, and structured error handling. Used by the platform shell, micro-frontends, and any other TypeScript consumer in the stack.

## What it generates

A Vite library-mode package that exports:
- `createApiClient()` -- factory for a typed fetch wrapper (pure TypeScript, no React dependency)
- `useApiClient()` -- React hook that reads auth/tenant from the shell's window globals
- `ApiError` -- error class with status, body, correlationId, and helper getters
- `getShellToken()` / `getShellTenantId()` -- context helpers for reading window globals
- `ApiConfig`, `RequestOptions` -- TypeScript interfaces for configuration

The package has two entry points:
- `"my-api-client"` -- core client + types + context helpers (no React)
- `"my-api-client/react"` -- the `useApiClient()` hook (React peer dependency)

## Usage

```bash
# Generate the api-client
appgen generate api-client -o ./my-api-client \
  -s projectName=my-api-client

# Link it to a frontend-app or platform-shell
appgen generate frontend-app -o ./orders \
  -s projectName=orders --shell ./my-platform --api-client ./my-api-client

# Generate TypeScript types from a backend's resources
appgen generate api-domain -o ./catalog-service \
  -s projectName=catalog-service \
  -s resources='[{"name":"product","fields":[{"name":"name","type":"string","required":true},{"name":"price","type":"decimal","required":true}]}]' \
  --api-client ./my-api-client
```

### Pure TypeScript (no React)

```typescript
import { createApiClient, ApiError } from "my-api-client";

const api = createApiClient({
  baseUrl: "/api",
  getToken: async () => "your-jwt-token",
  getTenantId: () => "tenant-123",
  onUnauthorized: () => console.warn("Session expired"),
});

const orders = await api.get<Order[]>("/order");
await api.post("/order", { name: "New Order" });
```

### React hook (reads from shell context)

```typescript
import { useApiClient } from "my-api-client/react";

function OrderList() {
  const api = useApiClient();
  const { data } = useQuery({
    queryKey: ["orders"],
    queryFn: () => api.get<Order[]>("/order"),
  });
}
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Package name (kebab-case) |
| `projectTitle` | derived from projectName | Display name |
| `apiBaseUrl` | `/api` | Default API base URL |
| `nodeVersion` | `20` | Node.js version |

## Generated structure

```
my-api-client/
├── package.json              # Dual entry points: . and ./react
├── tsconfig.json
├── vite.config.ts            # Library mode, ESM output, .d.ts generation
├── src/
│   ├── index.ts              # Barrel: createApiClient, ApiError, context helpers
│   ├── client.ts             # createApiClient() factory + fetch wrapper
│   ├── types.ts              # ApiConfig, RequestOptions, ApiError class
│   ├── context.ts            # getShellToken(), getShellTenantId()
│   ├── react.ts              # useApiClient() hook
│   └── resources/            # Generated when --api-client is used with api-domain
│       ├── index.ts          # Barrel export for all resource types
│       └── product.ts        # Product, CreateProductRequest, UpdateProductRequest, PageResponse
├── tests/
│   └── client.test.ts
├── .gitignore
└── README.md
```

## Window globals contract

The api-client reads auth and tenant information from two window globals set by the platform shell:

| Global | Type | Set by |
|--------|------|--------|
| `window.__SHELL_AUTH_TOKEN__` | `string` or `() => Promise<string>` | `ShellContextSync` in the shell |
| `window.__SHELL_TENANT_ID__` | `string` | `ShellContextSync` in the shell |

The `getShellToken()` helper handles both sync (string) and async (function) values. The `getShellTenantId()` helper reads the string directly.

When running standalone (outside the shell), these globals are undefined and the client sends requests without auth/tenant headers.

## How it connects to the shell

The platform shell renders a `<ShellContextSync>` component that syncs React auth/tenant state to the window globals above. This happens via `useEffect` hooks that update whenever the token or selected organization changes.

The flow:
1. Shell authenticates user (Clerk or OIDC) and gets a JWT
2. `ShellContextSync` writes the token getter to `window.__SHELL_AUTH_TOKEN__`
3. User selects an organization -- `ShellContextSync` writes the org ID to `window.__SHELL_TENANT_ID__`
4. MFE calls `useApiClient()` which reads both globals via `getShellToken()` / `getShellTenantId()`
5. Every fetch call includes `Authorization: Bearer <jwt>`, `X-Tenant-ID: <org-id>`, and `X-Correlation-ID: <uuid>`

## TypeScript types from api-domain

When you generate an `api-domain` with `--api-client`, the CLI generates TypeScript interfaces matching the backend's resource schema:

```bash
appgen generate api-domain -o ./catalog-service \
  -s projectName=catalog-service \
  -s resources='[{"name":"product","fields":[{"name":"name","type":"string","required":true},{"name":"price","type":"decimal","required":true}]}]' \
  --api-client ./my-api-client
```

This creates `src/resources/product.ts` in the api-client:

```typescript
export interface Product {
  id: number;
  tenantId: string;
  name: string;
  price: number;
  createdAt: string;
  updatedAt: string;
}

export interface CreateProductRequest {
  name: string;
  price: number;
}

export interface UpdateProductRequest {
  name: string;
  price: number;
}

export interface PageResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  number: number;
  size: number;
}
```

Frontend apps then import these types directly:

```typescript
import type { Product, CreateProductRequest, PageResponse } from "my-api-client";
```

## Syncing types from a running backend

The `appgen sync types` command regenerates types from a live backend's OpenAPI spec (SpringDoc):

```bash
appgen sync types \
  --from http://localhost:8082/v3/api-docs \
  --to ./my-api-client
```

This fetches the OpenAPI JSON, parses the schemas, generates TypeScript interfaces in `src/resources/`, updates the barrel export, and bumps the package patch version.

Use this after modifying your backend API to keep the frontend types in sync.

## Building and distributing

```bash
cd my-api-client
npm install
npm run build    # Outputs dist/index.js, dist/react.js, and .d.ts files
npm test         # Run unit tests
```

The generated `package.json` uses `"file:"` dependencies (local-deps pattern) when linked via `--api-client`. Consumer projects reference the api-client by its local path:

```json
{
  "dependencies": {
    "my-api-client": "file:../my-api-client"
  }
}
```

For production, publish to npm or GitHub Packages and replace `file:` references with version ranges.

## Correlation IDs

Every request sent by the api-client includes an `X-Correlation-ID` header with a generated UUID. This ID flows through the gateway and backend, appears in log entries, and is included in error responses. The `ApiError` class captures this ID so frontend error handlers can display it for support tickets.

## Error handling

The `ApiError` class provides structured error information:

```typescript
try {
  await api.get("/orders");
} catch (err) {
  if (err instanceof ApiError) {
    console.log(err.status);        // 404
    console.log(err.body);          // "Not Found"
    console.log(err.correlationId); // "a1b2c3d4-..."
    console.log(err.isNotFound);    // true
    console.log(err.isServerError); // false
  }
}
```

401 and 403 responses trigger optional `onUnauthorized` / `onForbidden` callbacks. The `useApiClient()` hook dispatches a `"api-unauthorized"` custom event on 401 so the shell can handle session expiry globally.
