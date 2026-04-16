"""Tests for backend CRUD resource generation (Java entities, services, controllers, DTOs, migrations)."""

import json
from pathlib import Path

from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template
from apps_generator.cli.generators.resources import parse_resources, generate_resource_scaffolding, JAVA_TYPES, SQL_TYPES
from apps_generator.cli.generators.linking import find_java_root, find_resources_root


# ── Parsing ──────────────────────────────────────────────────────────────────

def test_parse_resources_valid():
    resources = parse_resources('[{"name":"product","fields":[{"name":"name","type":"string"}]}]')
    assert len(resources) == 1
    assert resources[0]["name"] == "product"
    assert resources[0]["fields"][0]["name"] == "name"


def test_parse_resources_multiple():
    resources = parse_resources('[{"name":"product","fields":[]},{"name":"order","fields":[]}]')
    assert len(resources) == 2


def test_parse_resources_empty():
    assert parse_resources("[]") == []
    assert parse_resources("") == []
    assert parse_resources(None) == []


def test_parse_resources_invalid_json():
    assert parse_resources("not json") == []
    assert parse_resources("{invalid}") == []


def test_parse_resources_not_a_list():
    assert parse_resources('{"name":"product"}') == []


# ── Path helpers ─────────────────────────────────────────────────────────────

def test_find_java_root(tmp_path: Path):
    template = resolve_template("api-domain")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "out",
        cli_values={"projectName": "svc", "groupId": "com.test", "basePackage": "com.test.svc"},
        interactive=False,
    )
    java_root = find_java_root(result, "svc", "com.test.svc")
    assert java_root is not None
    assert java_root.exists()
    assert str(java_root).endswith("com/test/svc")


def test_find_resources_root(tmp_path: Path):
    template = resolve_template("api-domain")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "out",
        cli_values={"projectName": "svc", "groupId": "com.test", "basePackage": "com.test.svc"},
        interactive=False,
    )
    res_root = find_resources_root(result, "svc")
    assert res_root is not None
    assert (res_root / "application.yaml").exists()


# ── Full resource scaffolding ────────────────────────────────────────────────

def _generate_with_resource(tmp_path: Path, resource_json: str) -> tuple[Path, Path, Path]:
    """Helper: generate an api-domain project with resources and return (project_dir, java_root, res_root)."""
    template = resolve_template("api-domain")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "gen",
        cli_values={
            "projectName": "test-svc",
            "groupId": "com.test",
            "basePackage": "com.test.app",
            "features.oauth2": "false",
        },
        interactive=False,
    )
    project = result / "test-svc"
    java_root = find_java_root(result, "test-svc", "com.test.app")
    res_root = find_resources_root(result, "test-svc")

    resources = parse_resources(resource_json)
    generate_resource_scaffolding(java_root, res_root, resources, "com.test.app", "test-svc")

    return project, java_root, res_root


def test_resource_generates_entity(tmp_path: Path):
    _, java_root, _ = _generate_with_resource(tmp_path, '[{"name":"product","fields":[{"name":"name","type":"string","required":true}]}]')

    entity = java_root / "domain" / "model" / "Product.java"
    assert entity.exists()
    content = entity.read_text()
    assert "package com.test.app.domain.model;" in content
    assert "@Entity" in content
    assert '@Table(name = "products")' in content
    assert "extends TenantAwareEntity" in content  # tenantId, id, timestamps from base class
    assert "private String name;" in content


def test_resource_generates_repository(tmp_path: Path):
    _, java_root, _ = _generate_with_resource(tmp_path, '[{"name":"product","fields":[{"name":"name","type":"string"}]}]')

    repo = java_root / "domain" / "repository" / "ProductRepository.java"
    assert repo.exists()
    content = repo.read_text()
    assert "extends JpaRepository<Product, Long>" in content
    assert "findByTenantId" in content
    assert "findByIdAndTenantId" in content


def test_resource_generates_service_with_tenant_isolation(tmp_path: Path):
    _, java_root, _ = _generate_with_resource(tmp_path, '[{"name":"product","fields":[{"name":"name","type":"string"}]}]')

    service = java_root / "domain" / "service" / "ProductService.java"
    assert service.exists()
    content = service.read_text()
    assert "TenantContext.requireCurrentTenantId()" in content  # create sets tenant
    assert "entity.setTenantId(" in content
    assert "repository.findAll(pageable)" in content  # Hibernate filter auto-scopes
    assert 'new NotFoundException("Product"' in content
    assert "@Transactional" in content


def test_resource_generates_controller(tmp_path: Path):
    _, java_root, _ = _generate_with_resource(tmp_path, '[{"name":"product","fields":[{"name":"name","type":"string"}]}]')

    ctrl = java_root / "interfaces" / "rest" / "ProductController.java"
    assert ctrl.exists()
    content = ctrl.read_text()
    assert '@RequestMapping("/product")' in content
    assert "@GetMapping" in content
    assert "@PostMapping" in content
    assert '@PutMapping("/{id}")' in content
    assert '@DeleteMapping("/{id}")' in content
    assert "@Valid @RequestBody" in content
    assert "HttpStatus.CREATED" in content
    assert "HttpStatus.NO_CONTENT" in content


def test_resource_generates_dtos(tmp_path: Path):
    _, java_root, _ = _generate_with_resource(tmp_path, '[{"name":"product","fields":[{"name":"name","type":"string","required":true},{"name":"price","type":"decimal","required":true}]}]')

    dto_dir = java_root / "interfaces" / "rest" / "dto"
    assert (dto_dir / "CreateProductRequest.java").exists()
    assert (dto_dir / "UpdateProductRequest.java").exists()
    assert (dto_dir / "ProductResponse.java").exists()

    create_dto = (dto_dir / "CreateProductRequest.java").read_text()
    assert "@NotBlank" in create_dto  # string + required
    assert "@NotNull" in create_dto   # decimal + required
    assert "BigDecimal" in create_dto

    response_dto = (dto_dir / "ProductResponse.java").read_text()
    assert "private Long id;" in response_dto
    assert "private String tenantId;" in response_dto
    assert "private LocalDateTime createdAt;" in response_dto


def test_resource_generates_migration(tmp_path: Path):
    _, _, res_root = _generate_with_resource(tmp_path, '[{"name":"product","fields":[{"name":"name","type":"string","required":true},{"name":"sku","type":"string","unique":true}]}]')

    migration = res_root / "db" / "changelog" / "changes" / "002-create-product.yaml"
    assert migration.exists()
    content = migration.read_text()
    assert "products" in content       # table name
    assert "tenant_id" in content      # tenant column
    assert "created_at" in content     # audit column
    assert "idx_products_tenant_id" in content  # index
    assert "uq_products_sku" in content  # unique constraint


def test_resource_updates_master_changelog(tmp_path: Path):
    _, _, res_root = _generate_with_resource(tmp_path, '[{"name":"product","fields":[{"name":"name","type":"string"}]}]')

    import yaml
    master = res_root / "db" / "changelog" / "db.changelog-master.yaml"
    data = yaml.safe_load(master.read_text())
    files = [e["include"]["file"] for e in data["databaseChangeLog"] if "include" in e]
    assert "db/changelog/changes/002-create-product.yaml" in files


def test_resource_validation_annotations(tmp_path: Path):
    """Field constraints map to correct Java validation annotations."""
    _, java_root, _ = _generate_with_resource(tmp_path, json.dumps([{
        "name": "item",
        "fields": [
            {"name": "title", "type": "string", "required": True, "maxLength": 200, "minLength": 3},
            {"name": "count", "type": "integer", "min": 0, "max": 1000},
            {"name": "email", "type": "string", "pattern": "^[\\w@.]+$"},
        ]
    }]))

    create_dto = (java_root / "interfaces" / "rest" / "dto" / "CreateItemRequest.java").read_text()
    assert "@NotBlank" in create_dto
    assert "@Size(min = 3, max = 200)" in create_dto
    assert "@Min(0)" in create_dto
    assert "@Max(1000)" in create_dto
    assert "@Pattern" in create_dto


def test_multiple_resources(tmp_path: Path):
    """Multiple resources in one generation create separate files and sequential migrations."""
    _, java_root, res_root = _generate_with_resource(tmp_path, json.dumps([
        {"name": "product", "fields": [{"name": "name", "type": "string"}]},
        {"name": "category", "fields": [{"name": "label", "type": "string"}]},
    ]))

    assert (java_root / "domain" / "model" / "Product.java").exists()
    assert (java_root / "domain" / "model" / "Category.java").exists()
    assert (java_root / "interfaces" / "rest" / "ProductController.java").exists()
    assert (java_root / "interfaces" / "rest" / "CategoryController.java").exists()

    assert (res_root / "db" / "changelog" / "changes" / "002-create-product.yaml").exists()
    assert (res_root / "db" / "changelog" / "changes" / "003-create-category.yaml").exists()


def test_all_field_types(tmp_path: Path):
    """All supported field types generate correct Java types."""
    _, java_root, _ = _generate_with_resource(tmp_path, json.dumps([{
        "name": "everything",
        "fields": [
            {"name": "a_string", "type": "string"},
            {"name": "a_text", "type": "text"},
            {"name": "an_int", "type": "integer"},
            {"name": "a_long", "type": "long"},
            {"name": "a_decimal", "type": "decimal"},
            {"name": "a_bool", "type": "boolean"},
            {"name": "a_date", "type": "date"},
            {"name": "a_datetime", "type": "datetime"},
        ]
    }]))

    entity = (java_root / "domain" / "model" / "Everything.java").read_text()
    assert "private String aString;" in entity
    assert "private String aText;" in entity
    assert "private Integer anInt;" in entity
    assert "private Long aLong;" in entity
    assert "private BigDecimal aDecimal;" in entity
    assert "private Boolean aBool;" in entity
    assert "private LocalDate aDate;" in entity
    assert "private LocalDateTime aDatetime;" in entity


def test_hibernate_tenant_filter_infra(tmp_path: Path):
    """TenantAwareEntity, TenantFilterInterceptor, and WebConfig form the ORM-level tenant isolation."""
    template = resolve_template("api-domain")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "infra",
        cli_values={"projectName": "svc", "groupId": "com.test", "basePackage": "com.test.svc"},
        interactive=False,
    )

    base = result / "svc" / "src" / "main" / "java" / "com" / "test" / "svc"

    # TenantAwareEntity has Hibernate filter
    tenant_entity = (base / "domain" / "model" / "TenantAwareEntity.java").read_text()
    assert "@MappedSuperclass" in tenant_entity
    assert '@FilterDef' in tenant_entity
    assert 'name = "tenantFilter"' in tenant_entity
    assert "tenant_id = :tenantId" in tenant_entity
    assert '@Filter(name = "tenantFilter")' in tenant_entity
    assert "private String tenantId;" in tenant_entity
    assert "private Long id;" in tenant_entity
    assert "private LocalDateTime createdAt;" in tenant_entity

    # TenantFilterInterceptor enables the filter
    interceptor = (base / "infrastructure" / "tenant" / "TenantFilterInterceptor.java").read_text()
    assert "implements HandlerInterceptor" in interceptor
    assert 'enableFilter("tenantFilter")' in interceptor
    assert 'setParameter("tenantId", tenantId)' in interceptor

    # WebConfig registers the interceptor
    web_config = (base / "infrastructure" / "config" / "WebConfig.java").read_text()
    assert "TenantFilterInterceptor" in web_config
    assert "addInterceptor" in web_config


def test_shared_infra_generated(tmp_path: Path):
    """TenantContext, GlobalExceptionHandler, NotFoundException are always generated."""
    template = resolve_template("api-domain")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "out",
        cli_values={"projectName": "svc", "groupId": "com.test", "basePackage": "com.test.svc"},
        interactive=False,
    )

    base = result / "svc" / "src" / "main" / "java" / "com" / "test" / "svc"
    assert (base / "infrastructure" / "tenant" / "TenantContext.java").exists()
    assert (base / "infrastructure" / "web" / "GlobalExceptionHandler.java").exists()
    assert (base / "domain" / "exception" / "NotFoundException.java").exists()

    tenant_ctx = (base / "infrastructure" / "tenant" / "TenantContext.java").read_text()
    assert "getCurrentTenantId" in tenant_ctx
    assert "requireCurrentTenantId" in tenant_ctx

    handler = (base / "infrastructure" / "web" / "GlobalExceptionHandler.java").read_text()
    assert "@RestControllerAdvice" in handler
    assert "MethodArgumentNotValidException" in handler
    assert "NotFoundException" in handler
