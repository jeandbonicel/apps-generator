# Resources and CRUD

The `resources` parameter on `api-domain` generates complete CRUD scaffolding: JPA entities, services, controllers, DTOs, database migrations, integration tests, and optionally TypeScript types.

## Resource Configuration

Resources are defined as a JSON array passed via the `-s resources='[...]'` parameter or in a YAML parameters file.

```json
[
  {
    "name": "product",
    "fields": [
      {"name": "name", "type": "string", "required": true, "maxLength": 255},
      {"name": "description", "type": "text"},
      {"name": "price", "type": "decimal", "required": true, "min": 0},
      {"name": "sku", "type": "string", "required": true, "unique": true, "maxLength": 50},
      {"name": "active", "type": "boolean"}
    ]
  }
]
```

Each resource has a `name` (used for class names, table names, and URL paths) and a `fields` array.

## Field Types

| Type | Java Type | SQL Type | TypeScript Type | Notes |
|------|-----------|----------|-----------------|-------|
| `string` | `String` | `VARCHAR({maxLength})` | `string` | Default max length from `maxLength` constraint |
| `text` | `String` | `TEXT` | `string` | Unbounded text |
| `integer` | `Integer` | `INTEGER` | `number` | 32-bit integer |
| `long` | `Long` | `BIGINT` | `number` | 64-bit integer |
| `decimal` | `BigDecimal` | `DECIMAL(19,4)` | `number` | Fixed-point with 19 digits, 4 decimal places |
| `boolean` | `Boolean` | `BOOLEAN` | `boolean` | |
| `date` | `LocalDate` | `DATE` | `string` | ISO 8601 date (e.g., `2025-01-15`) |
| `datetime` | `LocalDateTime` | `TIMESTAMP` | `string` | ISO 8601 datetime (e.g., `2025-01-15T10:00:00`) |

## Field Constraints

| Constraint | Applies To | Java Validation | Column Effect |
|------------|-----------|-----------------|---------------|
| `required` | All types | `@NotBlank` (string/text) or `@NotNull` (others) | `nullable = false` |
| `unique` | All types | -- | `unique = true` |
| `maxLength` | string | `@Size(max = N)` | `length = N` on column |
| `minLength` | string | `@Size(min = N)` | -- |
| `min` | integer, long, decimal | `@Min(N)` | -- |
| `max` | integer, long, decimal | `@Max(N)` | -- |
| `pattern` | string | `@Pattern(regexp = "...")` | -- |

## What Gets Generated

For each resource (e.g., `product`), the following files are created:

### Java Backend

| File | Location | Description |
|------|----------|-------------|
| `Product.java` | `domain/model/` | JPA entity extending `TenantAwareEntity`. Inherits `id`, `tenantId`, `createdAt`, `updatedAt` and the Hibernate `@Filter` for tenant scoping. |
| `ProductRepository.java` | `domain/repository/` | Spring Data JPA repository with `findByTenantId`, `findByIdAndTenantId`, `deleteByIdAndTenantId`. |
| `ProductService.java` | `domain/service/` | CRUD operations. `list()` uses `findAll()` (auto-scoped by Hibernate filter). `create()` sets `tenantId` from `TenantContext`. |
| `ProductController.java` | `interfaces/rest/` | REST controller: `GET /product` (paginated list), `GET /product/{id}`, `POST /product`, `PUT /product/{id}`, `DELETE /product/{id}`. |
| `CreateProductRequest.java` | `interfaces/rest/dto/` | Request DTO with Jakarta validation annotations. |
| `UpdateProductRequest.java` | `interfaces/rest/dto/` | Request DTO for updates (same structure as create). |
| `ProductResponse.java` | `interfaces/rest/dto/` | Response DTO with `id`, `tenantId`, user fields, `createdAt`, `updatedAt`. |
| `002-create-products.yaml` | `resources/db/changelog/` | Liquibase migration creating the `products` table with a `tenant_id` column. |
| `ProductIntegrationTest.java` | `test/.../` | Integration test covering CRUD lifecycle, tenant isolation, and validation. |

### TypeScript Types (with `--api-client`)

When `--api-client` is provided, TypeScript interfaces are generated in the api-client package under `src/resources/`:

```typescript
// src/resources/product.ts -- DO NOT EDIT

export interface Product {
  id: number;
  tenantId: string;
  name: string;
  description: string | null;
  price: number;
  sku: string;
  active: boolean | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateProductRequest {
  name: string;
  description?: string;
  price: number;
  sku: string;
  active?: boolean;
}

export interface UpdateProductRequest {
  name: string;
  description?: string;
  price: number;
  sku: string;
  active?: boolean;
}

export interface PageResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  number: number;
  size: number;
}
```

Required fields are non-nullable in the response and required in the request. Optional fields are `T | null` in the response and optional (`?`) in the request.

A barrel export (`src/resources/index.ts`) re-exports all resource types, and the main `src/index.ts` is updated to include the resources export.

## Entity Inheritance

Every generated entity extends `TenantAwareEntity`, which provides:

- `id` (Long, auto-generated)
- `tenantId` (String, set on create, non-updatable)
- `createdAt` / `updatedAt` (LocalDateTime, auto-managed via `@PrePersist` / `@PreUpdate`)
- Hibernate `@FilterDef` + `@Filter` that adds `WHERE tenant_id = :tenantId` to every query

This means `repository.findAll()` in the service layer is automatically tenant-scoped -- no manual filtering needed. See [Multi-Tenancy](multi-tenancy.md) for the full flow.

## Service Layer

The generated service enforces tenant isolation at two levels:

1. **Reads**: Hibernate `@Filter` auto-scopes every SELECT query by tenant
2. **Writes**: `create()` explicitly sets `tenantId` from `TenantContext.requireCurrentTenantId()`; `update()` preserves the original tenant; `delete()` fetches first (scoped by filter) then deletes

## REST Controller

The controller maps to `/{resourceName}` (e.g., `/product`). Through the gateway, this becomes `/api/product/product`.

| Method | Path | Action |
|--------|------|--------|
| `GET` | `/product?page=0&size=20` | Paginated list (auto-tenant-scoped) |
| `GET` | `/product/{id}` | Get by ID |
| `POST` | `/product` | Create (validates request body via `@Valid`) |
| `PUT` | `/product/{id}` | Update |
| `DELETE` | `/product/{id}` | Delete (returns 204) |

## Multiple Resources

You can define multiple resources in a single generate command:

```bash
appgen generate api-domain -o ./service \
  -s projectName=my-service \
  -s groupId=com.example \
  -s basePackage=com.example.myservice \
  -s 'resources=[
    {"name":"product","fields":[{"name":"name","type":"string","required":true}]},
    {"name":"category","fields":[{"name":"name","type":"string","required":true},{"name":"sortOrder","type":"integer"}]},
    {"name":"order","fields":[{"name":"total","type":"decimal","required":true},{"name":"status","type":"string","required":true}]}
  ]' \
  --gateway ./gateway --api-client ./api-client
```

Each resource gets its own entity, repository, service, controller, DTOs, migration, test, and TypeScript types. Migrations are numbered sequentially (002, 003, 004...) after the initial 001-init migration.
