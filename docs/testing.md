# Testing

Apps Generator produces integration tests for every generated CRUD resource and includes a Python test suite for the generators themselves.

## Generated Integration Tests

When you generate an `api-domain` with `resources`, each resource gets an integration test class that extends `AbstractIntegrationTest`.

### What Gets Tested

Each `<Entity>IntegrationTest` covers:

**CRUD Lifecycle** (`crud_lifecycle` test):
1. **CREATE** -- POST with valid JSON body, asserts 201 Created, verifies `id` is a number and `tenantId` matches
2. **READ** -- GET by ID, asserts 200 OK and correct ID
3. **LIST** -- GET paginated list, asserts `totalElements` is 1 for the creating tenant
4. **TENANT ISOLATION** -- GET list as a different tenant, asserts `totalElements` is 0
5. **UPDATE** -- PUT with modified body, asserts 200 OK and updated field value
6. **DELETE** -- DELETE by ID, asserts 204 No Content
7. **READ after DELETE** -- GET by deleted ID, asserts 404 Not Found

**Cross-Tenant Access** (`getById_wrongTenant_returns404` test):
- Creates a record as tenant A
- Attempts to read it as tenant B
- Asserts 404 Not Found (the Hibernate filter prevents cross-tenant access)

**Validation** (`create_withMissingRequiredField_returns400` test, generated when the resource has required fields):
- Sends a POST with a required field missing
- Asserts 400 Bad Request

### Example Test

For a resource named `product` with a required `name` field:

```java
class ProductIntegrationTest extends AbstractIntegrationTest {

    private static final String TENANT_A = "tenant-a";
    private static final String TENANT_B = "tenant-b";

    @Test
    void crud_lifecycle() throws Exception {
        // CREATE
        String response = mockMvc.perform(post("/product")
                .header("X-Tenant-ID", TENANT_A)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{ \"name\": \"test-value\", ... }"))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.id").isNumber())
            .andExpect(jsonPath("$.tenantId").value(TENANT_A))
            .andReturn().getResponse().getContentAsString();

        long id = JsonPath.parse(response).read("$.id", Long.class);

        // LIST -- tenant A sees 1, tenant B sees 0
        // UPDATE, DELETE, etc.
    }

    @Test
    void getById_wrongTenant_returns404() throws Exception {
        // Create as tenant A, read as tenant B -> 404
    }

    @Test
    void create_withMissingRequiredField_returns400() throws Exception {
        // POST without 'name' -> 400
    }
}
```

## AbstractIntegrationTest

The base test class configures the test environment:

```java
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Testcontainers
public abstract class AbstractIntegrationTest {

    @Container
    static final PostgreSQLContainer<?> postgres =
        new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("testdb")
            .withUsername("test")
            .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    protected MockMvc mockMvc;
}
```

Key details:
- **Testcontainers** starts a real PostgreSQL 16 (Alpine) container -- no H2 or mocks
- **`@DynamicPropertySource`** wires Spring's datasource to the container's JDBC URL
- **`@ActiveProfiles("test")`** activates `application-test.yaml` (disables JWT validation, enables test DB)
- **MockMvc** is used for HTTP request testing without starting a real server
- The `DevSecurityConfig` with `@Profile("local")` is not active; tests use the test profile which also permits all requests

## Test Profile

The `application-test.yaml` configuration typically disables security and uses the Testcontainers database:

```yaml
spring:
  security:
    enabled: false
  liquibase:
    change-log: classpath:db/changelog/db.changelog-master.yaml
```

Liquibase migrations run automatically against the test database, so the schema matches production.

## Running Backend Tests

```bash
cd product-service/product-service
./gradlew test
```

Requirements:
- **Docker must be running** -- Testcontainers starts a PostgreSQL container
- Java 21+ (or whichever `javaVersion` was configured)

Gradle outputs test results to `build/reports/tests/test/index.html`.

## Python Test Suite

The generator itself has a comprehensive test suite:

```bash
cd apps-generator
pip install -e ".[dev]"
pytest tests/ -v
```

The Python tests cover:
- Template resolution and validation
- Parameter parsing and defaults
- File generation and Jinja2 rendering
- Filename variable substitution and filters
- Shell linking (`--shell` registration in `remotes.json`)
- Gateway linking (`--gateway` registration in `routes.yaml`)
- UI kit linking (`--uikit` dependency and Tailwind config)
- API client linking (`--api-client` dependency registration)
- Resource parsing and CRUD scaffolding
- TypeScript type generation
- Docker Compose generation
- Page component generation
- Feature flag conditional file inclusion
- End-to-end generation of each template

Run with coverage:

```bash
pytest tests/ -v --cov=apps_generator --cov-report=term-missing
```

## Frontend E2E Tests

Each generated frontend project includes Playwright E2E tests:

```bash
cd my-platform/my-platform
npx playwright install chromium    # First time only
pnpm run e2e                       # Headless
pnpm run e2e:ui                    # Interactive UI
pnpm run e2e:debug                 # Step-through debugger
```
