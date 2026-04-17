# Getting Started

This tutorial walks through generating a complete multi-tenant application from scratch: a product management system with a backend API, typed client, and data-aware frontend.

## Prerequisites

- Python 3.10+
- Node.js 20+
- Java 21 (for backends)
- Docker (for PostgreSQL and deployment)

## Install the CLI

```bash
cd apps-generator
pip install -e .
```

Verify it works:

```bash
appgen templates list
```

## Step 1: Generate a UI Kit

The shared component library provides Tailwind CSS theming and shadcn/ui components used by the shell and all MFEs.

```bash
appgen generate ui-kit -o ./workspace/ui-kit -s projectName=my-ui-kit
```

Build it so other projects can depend on it:

```bash
cd workspace/ui-kit/my-ui-kit
npm install
npm run build
cd ../../..
```

## Step 2: Generate an API Client

The API client is a shared TypeScript package that provides a typed fetch wrapper. It automatically attaches `Authorization`, `X-Tenant-ID`, and `X-Correlation-ID` headers to every request.

```bash
appgen generate api-client -o ./workspace/api-client -s projectName=my-api-client
```

Build it:

```bash
cd workspace/api-client/my-api-client
npm install
npm run build
cd ../../..
```

## Step 3: Generate an API Gateway

The gateway is a Spring Cloud Gateway application that serves as the single entry point for all backend services. It validates JWTs, forwards tenant headers, and adds correlation IDs.

```bash
appgen generate api-gateway -o ./workspace/gateway \
  -s projectName=my-gateway \
  -s groupId=com.example \
  -s basePackage=com.example.gateway
```

## Step 4: Generate the Platform Shell

The platform shell is the React host application. It handles authentication (Clerk or OIDC), the organization/tenant switcher, and loads micro-frontends via Module Federation.

```bash
appgen generate platform-shell -o ./workspace/my-platform \
  -s projectName=my-platform \
  -s clerkPublishableKey=pk_test_xxxxx \
  --uikit ./workspace/ui-kit \
  --api-client ./workspace/api-client
```

The `--uikit` flag adds the UI kit as an npm dependency and extends the Tailwind config. The `--api-client` flag adds the typed API client as a dependency.

## Step 5: Generate a Backend with CRUD Resources

Generate a backend service with fully scaffolded CRUD resources. The `resources` parameter defines entities, fields, types, and constraints. The `--api-client` flag generates matching TypeScript types in the shared client package.

```bash
appgen generate api-domain -o ./workspace/product-service \
  -s projectName=product-service \
  -s groupId=com.example \
  -s basePackage=com.example.products \
  -s 'resources=[
    {
      "name": "product",
      "fields": [
        {"name": "name", "type": "string", "required": true, "maxLength": 255},
        {"name": "description", "type": "text"},
        {"name": "price", "type": "decimal", "required": true, "min": 0},
        {"name": "sku", "type": "string", "required": true, "unique": true, "maxLength": 50},
        {"name": "active", "type": "boolean"}
      ]
    },
    {
      "name": "category",
      "fields": [
        {"name": "name", "type": "string", "required": true, "maxLength": 100},
        {"name": "sortOrder", "type": "integer", "min": 0}
      ]
    }
  ]' \
  --gateway ./workspace/gateway \
  --api-client ./workspace/api-client
```

This generates per resource:
- JPA entity extending `TenantAwareEntity` (auto-scoped by tenant)
- Spring Data repository
- Service with CRUD operations
- REST controller with validation
- Create/Update/Response DTOs
- Liquibase migration
- Integration test (CRUD lifecycle + tenant isolation)
- TypeScript types in the api-client (`Product`, `CreateProductRequest`, `UpdateProductRequest`, `PageResponse`)

The `--gateway` flag registers `product-service` in the gateway's `routes.yaml` at `/api/product/**`.

## Step 6: Generate a Frontend with Data-Aware Pages

```bash
appgen generate frontend-app -o ./workspace/products -s projectName=products -s devPort=5001 \
  -s 'pages=[
    {"path":"overview","label":"Overview","resource":"product","type":"dashboard","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"active","type":"boolean"}
    ]},
    {"path":"list","label":"Products","resource":"product","type":"list","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"active","type":"boolean"}
    ]},
    {"path":"create","label":"New Product","resource":"product","type":"form","fields":[
      {"name":"name","type":"string","required":true},
      {"name":"price","type":"decimal","required":true},
      {"name":"description","type":"text"}
    ]}
  ]' \
  --shell ./workspace/my-platform \
  --uikit ./workspace/ui-kit \
  --api-client ./workspace/api-client
```

The `--shell` flag registers this MFE in the platform shell's `remotes.json`. The pages appear as a vertical sidebar inside the "Products" tab. The three page types are:
- **dashboard** -- stat cards, a bar chart (auto-picks the first numeric field), and a recent items table
- **list** -- paginated table with type-aware cell rendering
- **form** -- create form with validation and mutation

## Step 7: Build Shared Libraries

Before running Docker Compose, rebuild shared libs to include the generated types:

```bash
cd workspace/api-client/my-api-client && npm install && npm run build && cd ../../..
cd workspace/ui-kit/my-ui-kit && npm install && npm run build && cd ../../..
```

## Step 8: Generate Docker Compose

```bash
appgen docker-compose ./workspace
```

This scans the workspace and generates a `docker-compose.yaml` with:
- PostgreSQL with per-service databases (auto-created via init script)
- Backend services with correct database URLs
- API gateway with Docker service names
- Micro-frontends with CORS headers for Module Federation
- Platform shell with correct dependencies

## Step 9: Start Everything

```bash
cd workspace
docker compose up --build
```

## Step 10: Verify

Open `http://localhost:5173` in your browser.

1. Sign in with Clerk (or your OIDC provider)
2. Select an organization from the org switcher
3. Click the "Products" tab
4. The "Overview" dashboard page loads -- it shows stat cards, a bar chart of prices by product name, and a recent items table
5. Click "Products" in the sidebar to see the paginated list page
6. Click "New Product" in the sidebar to see the create form

API requests flow: Browser -> Shell nginx -> Gateway (:8080) -> product-service (:8081) -> PostgreSQL.

Every request carries `Authorization`, `X-Tenant-ID`, and `X-Correlation-ID` headers. The backend auto-scopes all queries by tenant.

## Running Without Docker

For local development without Docker Compose:

```bash
# Start PostgreSQL
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=product_service \
  postgres:16-alpine

# Start the backend
cd workspace/product-service/product-service
./gradlew bootRun --args='--server.port=8081 --spring.profiles.active=local'

# Start the gateway
cd workspace/gateway/my-gateway
./gradlew bootRun --args='--spring.profiles.active=local'

# Start the MFE
cd workspace/products/products
npm install && npm run dev  # http://localhost:5001

# Start the shell
cd workspace/my-platform/my-platform
npm install && npm run dev  # http://localhost:5173
```

The `local` Spring profile disables JWT validation so you can develop without a running OIDC provider.

## Next Steps

- [Resources and CRUD](resources-and-crud.md) -- field types, constraints, what gets generated
- [Multi-Tenancy](multi-tenancy.md) -- how tenant isolation works end-to-end
- [API Client and Types](api-client-and-types.md) -- typed client, generated types, sync command
- [Deployment](deployment.md) -- Docker Compose, Kubernetes, GitHub Actions
