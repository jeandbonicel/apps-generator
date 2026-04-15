# {{ projectTitle or projectName }}

Shared API client for the platform. Handles auth tokens, tenant headers, and error handling.

## Usage

```typescript
// Pure TypeScript (no React)
import { createApiClient } from "{{ projectName }}";

const api = createApiClient({
  baseUrl: "/api",
  getToken: async () => "your-jwt-token",
  getTenantId: () => "tenant-123",
});

const orders = await api.get<Order[]>("/order");
await api.post("/order", { name: "New Order" });
```

```typescript
// React hook (reads token + tenant from shell context automatically)
import { useApiClient } from "{{ projectName }}/react";

function OrderList() {
  const api = useApiClient();
  // Use with TanStack Query:
  const { data } = useQuery({
    queryKey: ["orders"],
    queryFn: () => api.get<Order[]>("/order"),
  });
}
```

## Build

```bash
npm install
npm run build    # → dist/index.js + dist/react.js
npm test         # Unit tests
```
