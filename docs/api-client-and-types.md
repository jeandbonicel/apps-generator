# API Client and Types

The `api-client` template generates a shared TypeScript package that provides a typed HTTP client for frontend applications. It handles authentication, tenant identification, correlation IDs, and error handling in a single place.

## What the Package Provides

### `createApiClient(config)`

A factory function that returns a typed HTTP client with `get`, `post`, `put`, `patch`, and `delete` methods. Every request automatically includes:

- `Authorization: Bearer <token>` -- from `config.getToken()`
- `X-Tenant-ID: <id>` -- from `config.getTenantId()`
- `X-Correlation-ID: <uuid>` -- generated per request via `crypto.randomUUID()`
- `Content-Type: application/json` and `Accept: application/json`

### `ApiError`

A typed error class thrown on non-2xx responses. Includes:

- `status` -- HTTP status code
- `body` -- response body text
- `correlationId` -- the correlation ID for this request (useful for debugging with backend logs)
- Helper getters: `isUnauthorized`, `isForbidden`, `isNotFound`, `isServerError`

### Shell Context Helpers

- `getShellToken()` -- reads `window.__SHELL_AUTH_TOKEN__` (set by the platform shell after login)
- `getShellTenantId()` -- reads `window.__SHELL_TENANT_ID__` (set by the shell's org switcher)

These allow MFEs loaded via Module Federation to access the shell's auth state without direct imports.

### `ApiConfig` Interface

```typescript
interface ApiConfig {
  baseUrl: string;                         // e.g., "/api"
  getToken: () => Promise<string | null>;  // auth token provider
  getTenantId: () => string | null;        // tenant ID provider
  onUnauthorized?: () => void;             // called on 401
  onForbidden?: () => void;                // called on 403
}
```

## Using in MFEs

After generating with `--api-client`, the api-client is added as an npm dependency. Import types and the client:

```typescript
import { createApiClient, getShellToken, getShellTenantId } from "my-api-client";
import type { Product, CreateProductRequest, PageResponse } from "my-api-client";

const api = createApiClient({
  baseUrl: "/api/product",
  getToken: getShellToken,
  getTenantId: getShellTenantId,
});

// Typed list
const products = await api.get<PageResponse<Product>>("/product?page=0&size=20");

// Typed create
const newProduct = await api.post<Product>("/product", {
  name: "Widget",
  price: 9.99,
  sku: "WDG-001",
} satisfies CreateProductRequest);
```

## Generated TypeScript Types

When you generate an `api-domain` with `--api-client`, TypeScript interfaces are created in the api-client's `src/resources/` directory. For each resource, three interfaces are generated:

| Interface | Description |
|-----------|-------------|
| `Product` | Response type with `id`, `tenantId`, user fields, `createdAt`, `updatedAt` |
| `CreateProductRequest` | Request type. Required fields are non-optional; optional fields use `?` |
| `UpdateProductRequest` | Same structure as create request |
| `PageResponse<T>` | Generic paginated response with `content`, `totalElements`, `totalPages`, `number`, `size` |

Type mapping from resource field types:

| Resource Type | TypeScript Type | Required | Optional |
|---------------|-----------------|----------|----------|
| string, text, date, datetime | `string` | `field: string` | `field: string \| null` |
| integer, long, decimal | `number` | `field: number` | `field: number \| null` |
| boolean | `boolean` | `field: boolean` | `field: boolean \| null` |

The types file includes a `DO NOT EDIT` header. Regenerate them with `appgen sync types` or by re-running the generate command.

## The `appgen sync types` Command

After your backend evolves (new fields, renamed properties, etc.), you can regenerate TypeScript types from the live backend's OpenAPI spec:

```bash
appgen sync types \
  --from http://localhost:8081/v3/api-docs \
  --to ./api-client
```

This command:

1. Fetches the OpenAPI JSON from the running Spring Boot service (requires SpringDoc)
2. Parses `components/schemas` and groups them by resource (heuristic: `ProductResponse`, `CreateProductRequest`, etc.)
3. Generates TypeScript interfaces in `src/resources/`
4. Updates the barrel export (`src/resources/index.ts`)
5. Bumps the `patch` version in `package.json` automatically

After syncing, rebuild the api-client and downstream consumers will pick up the new types:

```bash
cd api-client/my-api-client
npm run build
```

## Versioning

The api-client uses semantic versioning in its `package.json`. The `sync types` command automatically bumps the patch version (e.g., `0.1.0` -> `0.1.1`) so that downstream projects can detect the change.

For local development with npm workspaces or linked packages, the version bump ensures that build tools recognize the dependency has changed.
