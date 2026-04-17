"""Resource CRUD scaffolding — generates Java entities, services, controllers, DTOs."""

from __future__ import annotations

import json
from pathlib import Path

from apps_generator.utils.console import console
from apps_generator.utils.naming import pascal_case, snake_case, camel_case


# -- Field type mappings ------------------------------------------------------

JAVA_TYPES = {
    "string": "String",
    "text": "String",
    "integer": "Integer",
    "long": "Long",
    "decimal": "BigDecimal",
    "boolean": "Boolean",
    "date": "LocalDate",
    "datetime": "LocalDateTime",
    "enum": "__ENUM__",  # placeholder — replaced by generated enum class name
}

SQL_TYPES = {
    "string": "VARCHAR({maxLength})",
    "text": "TEXT",
    "integer": "INTEGER",
    "long": "BIGINT",
    "decimal": "DECIMAL(19,4)",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMP",
    "enum": "VARCHAR({maxLength})",
}

TS_TYPES = {
    "string": "string",
    "text": "string",
    "integer": "number",
    "long": "number",
    "decimal": "number",
    "boolean": "boolean",
    "date": "string",
    "datetime": "string",
    "enum": "__ENUM__",  # placeholder — replaced by union type
}

JAVA_IMPORTS = {
    "decimal": "java.math.BigDecimal",
    "date": "java.time.LocalDate",
    "datetime": "java.time.LocalDateTime",
}


# -- Parsing ------------------------------------------------------------------


def parse_resources(resources_str: str) -> list[dict]:
    """Parse resources JSON string into a list of resource configs."""
    if not resources_str or resources_str == "[]":
        return []
    try:
        parsed = json.loads(resources_str)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


# -- Java code generation -----------------------------------------------------


def generate_resource_scaffolding(
    java_root: Path,
    res_root: Path,
    resources: list[dict],
    base_package: str,
    project_name: str,
) -> None:
    """Generate Java CRUD files for each resource."""
    from apps_generator.cli.generators.migrations import generate_migration

    for idx, resource in enumerate(resources):
        name = resource.get("name", "")
        fields = resource.get("fields", [])
        if not name:
            continue

        entity_name = pascal_case(name)
        table_name = snake_case(name) + "s"
        migration_seq = idx + 2  # 001-init is already taken

        console.print(f"  Generating resource: [bold]{entity_name}[/bold]")

        # Generate enum classes first (needed by entity)
        for f in fields:
            if f.get("type") == "enum" and f.get("values"):
                _gen_enum_class(java_root, base_package, entity_name, f)

        _gen_entity(java_root, base_package, entity_name, table_name, fields)
        _gen_repository(java_root, base_package, entity_name)
        _gen_service(java_root, base_package, entity_name, name)
        _gen_controller(java_root, base_package, entity_name, name, fields)
        _gen_create_request(java_root, base_package, entity_name, fields)
        _gen_update_request(java_root, base_package, entity_name, fields)
        _gen_response_dto(java_root, base_package, entity_name, fields)
        generate_migration(res_root, entity_name, table_name, fields, migration_seq, name)

        # Integration test (test root mirrors java root: src/main/java → src/test/java)
        test_root = Path(str(java_root).replace("/main/java/", "/test/java/"))
        if test_root.parent.exists():
            _gen_integration_test(test_root, base_package, entity_name, name, fields)


def _collect_imports(fields: list[dict]) -> list[str]:
    """Collect extra Java imports needed for field types."""
    imports = set()
    for f in fields:
        ft = f.get("type", "string")
        if ft in JAVA_IMPORTS:
            imports.add(JAVA_IMPORTS[ft])
    return sorted(imports)


def _gen_enum_class(java_root: Path, pkg: str, entity: str, field: dict) -> str:
    """Generate a Java enum class for an enum field. Returns the enum class name."""
    enum_name = pascal_case(field["name"])
    values = field.get("values", [])
    if not values:
        return "String"

    dest = java_root / "domain" / "model" / f"{enum_name}.java"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        enum_values = ", ".join(v.upper().replace("-", "_").replace(" ", "_") for v in values)
        dest.write_text(f"package {pkg}.domain.model;\n\npublic enum {enum_name} {{\n    {enum_values}\n}}\n")
        console.print(f"    Created: domain/model/{enum_name}.java")
    return enum_name


def _java_type_for_field(f: dict) -> str:
    """Get Java type for a field, handling enum specially."""
    ft = f.get("type", "string")
    if ft == "enum":
        return pascal_case(f["name"])
    return JAVA_TYPES.get(ft, "String")


def _ts_type_for_field(f: dict) -> str:
    """Get TypeScript type for a field, handling enum specially."""
    ft = f.get("type", "string")
    if ft == "enum":
        values = f.get("values", [])
        if values:
            return " | ".join(f'"{v}"' for v in values)
        return "string"
    return TS_TYPES.get(ft, "string")


def _java_field(f: dict, with_validation: bool = False) -> str:
    """Generate a Java field declaration with optional validation annotations."""
    ft = f.get("type", "string")
    java_type = _java_type_for_field(f)
    name = camel_case(f["name"])
    required = f.get("required", False)
    unique = f.get("unique", False)
    max_len = f.get("maxLength")
    min_len = f.get("minLength")
    min_val = f.get("min")
    max_val = f.get("max")
    pattern = f.get("pattern")

    lines = []

    if with_validation:
        if required and ft in ("string", "text"):
            lines.append("    @NotBlank")
        elif required:
            lines.append("    @NotNull")
        if max_len or min_len:
            parts = []
            if min_len:
                parts.append(f"min = {min_len}")
            if max_len:
                parts.append(f"max = {max_len}")
            lines.append(f"    @Size({', '.join(parts)})")
        if min_val is not None:
            lines.append(f"    @Min({min_val})")
        if max_val is not None:
            lines.append(f"    @Max({max_val})")
        if pattern:
            lines.append(f'    @Pattern(regexp = "{pattern}")')

    # Column annotation for entity
    col_parts = []
    if required and not with_validation:
        col_parts.append("nullable = false")
    if unique and not with_validation:
        col_parts.append("unique = true")
    if ft == "decimal" and not with_validation:
        col_parts.append("precision = 19")
        col_parts.append("scale = 4")
    if max_len and not with_validation:
        col_parts.append(f"length = {max_len}")

    if col_parts and not with_validation:
        lines.append(f"    @Column({', '.join(col_parts)})")

    # Enum annotation for entity
    if ft == "enum" and not with_validation:
        lines.append("    @Enumerated(EnumType.STRING)")

    lines.append(f"    private {java_type} {name};")
    return "\n".join(lines)


def _gen_entity(java_root: Path, pkg: str, entity: str, table: str, fields: list[dict]) -> None:
    """Generate JPA entity class extending TenantAwareEntity."""
    dest = java_root / "domain" / "model" / f"{entity}.java"
    if dest.exists():
        return

    extra_imports = _collect_imports(fields)
    import_lines = "\n".join(f"import {i};" for i in extra_imports)
    if import_lines:
        import_lines = "\n" + import_lines

    field_lines = "\n\n".join(_java_field(f) for f in fields)

    # Getters and setters (only for user-defined fields — id/tenantId/timestamps come from base)
    accessors = []
    for f in fields:
        java_type = _java_type_for_field(f)
        name = camel_case(f["name"])
        getter = f"get{pascal_case(f['name'])}"
        setter = f"set{pascal_case(f['name'])}"
        accessors.append(f"    public {java_type} {getter}() {{ return {name}; }}")
        accessors.append(f"    public void {setter}({java_type} {name}) {{ this.{name} = {name}; }}")

    accessor_lines = "\n".join(accessors)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f"package {pkg}.domain.model;\n"
        f"\n"
        f"import jakarta.persistence.*;{import_lines}\n"
        f"\n"
        f"/**\n"
        f" * Extends TenantAwareEntity which provides id, tenantId, createdAt, updatedAt\n"
        f" * and a Hibernate @Filter that auto-scopes all queries by tenant.\n"
        f" */\n"
        f"@Entity\n"
        f'@Table(name = "{table}")\n'
        f"public class {entity} extends TenantAwareEntity {{\n"
        f"\n"
        f"{field_lines}\n"
        f"\n"
        f"{accessor_lines}\n"
        f"}}\n"
    )
    console.print(f"    Created: domain/model/{entity}.java")


def _gen_repository(java_root: Path, pkg: str, entity: str) -> None:
    """Generate Spring Data JPA repository."""
    dest = java_root / "domain" / "repository" / f"{entity}Repository.java"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f"package {pkg}.domain.repository;\n"
        f"\n"
        f"import {pkg}.domain.model.{entity};\n"
        f"import org.springframework.data.domain.Page;\n"
        f"import org.springframework.data.domain.Pageable;\n"
        f"import org.springframework.data.jpa.repository.JpaRepository;\n"
        f"\n"
        f"import java.util.Optional;\n"
        f"\n"
        f"public interface {entity}Repository extends JpaRepository<{entity}, Long> {{\n"
        f"\n"
        f"    Page<{entity}> findByTenantId(String tenantId, Pageable pageable);\n"
        f"\n"
        f"    Optional<{entity}> findByIdAndTenantId(Long id, String tenantId);\n"
        f"\n"
        f"    void deleteByIdAndTenantId(Long id, String tenantId);\n"
        f"}}\n"
    )
    console.print(f"    Created: domain/repository/{entity}Repository.java")


def _gen_service(java_root: Path, pkg: str, entity: str, name: str) -> None:
    """Generate service with CRUD operations."""
    dest = java_root / "domain" / "service" / f"{entity}Service.java"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f"package {pkg}.domain.service;\n"
        f"\n"
        f"import {pkg}.domain.exception.NotFoundException;\n"
        f"import {pkg}.domain.model.{entity};\n"
        f"import {pkg}.domain.repository.{entity}Repository;\n"
        f"import {pkg}.infrastructure.tenant.TenantContext;\n"
        f"import org.springframework.data.domain.Page;\n"
        f"import org.springframework.data.domain.Pageable;\n"
        f"import org.springframework.stereotype.Service;\n"
        f"import org.springframework.transaction.annotation.Transactional;\n"
        f"\n"
        f"/**\n"
        f" * Tenant isolation is enforced at two levels:\n"
        f" * 1. Hibernate @Filter on TenantAwareEntity auto-scopes every SELECT query\n"
        f" * 2. Explicit tenantId checks in create/update/delete for writes\n"
        f" */\n"
        f"@Service\n"
        f"@Transactional\n"
        f"public class {entity}Service {{\n"
        f"\n"
        f"    private final {entity}Repository repository;\n"
        f"\n"
        f"    public {entity}Service({entity}Repository repository) {{\n"
        f"        this.repository = repository;\n"
        f"    }}\n"
        f"\n"
        f"    @Transactional(readOnly = true)\n"
        f"    public Page<{entity}> list(Pageable pageable) {{\n"
        f"        // Hibernate tenant filter auto-scopes this query\n"
        f"        return repository.findAll(pageable);\n"
        f"    }}\n"
        f"\n"
        f"    @Transactional(readOnly = true)\n"
        f"    public {entity} getById(Long id) {{\n"
        f"        // Hibernate tenant filter ensures only current tenant's data is visible\n"
        f"        return repository.findById(id)\n"
        f'            .orElseThrow(() -> new NotFoundException("{entity}", id));\n'
        f"    }}\n"
        f"\n"
        f"    public {entity} create({entity} entity) {{\n"
        f"        entity.setTenantId(TenantContext.requireCurrentTenantId());\n"
        f"        return repository.save(entity);\n"
        f"    }}\n"
        f"\n"
        f"    public {entity} update(Long id, {entity} updated) {{\n"
        f"        {entity} existing = getById(id);\n"
        f"        updated.setId(existing.getId());\n"
        f"        updated.setTenantId(existing.getTenantId());\n"
        f"        return repository.save(updated);\n"
        f"    }}\n"
        f"\n"
        f"    public void delete(Long id) {{\n"
        f"        {entity} existing = getById(id);\n"
        f"        repository.delete(existing);\n"
        f"    }}\n"
        f"}}\n"
    )
    console.print(f"    Created: domain/service/{entity}Service.java")


def _gen_create_request(java_root: Path, pkg: str, entity: str, fields: list[dict]) -> None:
    """Generate CreateXxxRequest DTO with validation."""
    dest = java_root / "interfaces" / "rest" / "dto" / f"Create{entity}Request.java"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)

    extra_imports = _collect_imports(fields)
    validation_imports = set()
    for f in fields:
        req = f.get("required", False)
        ft = f.get("type", "string")
        if req and ft in ("string", "text"):
            validation_imports.add("jakarta.validation.constraints.NotBlank")
        elif req:
            validation_imports.add("jakarta.validation.constraints.NotNull")
        if f.get("maxLength") or f.get("minLength"):
            validation_imports.add("jakarta.validation.constraints.Size")
        if f.get("min") is not None:
            validation_imports.add("jakarta.validation.constraints.Min")
        if f.get("max") is not None:
            validation_imports.add("jakarta.validation.constraints.Max")
        if f.get("pattern"):
            validation_imports.add("jakarta.validation.constraints.Pattern")

    all_imports = sorted(set(extra_imports) | validation_imports)
    import_lines = "\n".join(f"import {i};" for i in all_imports)
    if import_lines:
        import_lines = "\n" + import_lines

    field_lines = "\n\n".join(_java_field(f, with_validation=True) for f in fields)

    # Getters/setters
    accessors = []
    for f in fields:
        java_type = _java_type_for_field(f)
        name = camel_case(f["name"])
        getter = f"get{pascal_case(f['name'])}"
        setter = f"set{pascal_case(f['name'])}"
        accessors.append(f"    public {java_type} {getter}() {{ return {name}; }}")
        accessors.append(f"    public void {setter}({java_type} {name}) {{ this.{name} = {name}; }}")

    dest.write_text(
        f"package {pkg}.interfaces.rest.dto;\n"
        f"{import_lines}\n"
        f"\n"
        f"public class Create{entity}Request {{\n"
        f"\n"
        f"{field_lines}\n"
        f"\n"
        f"{''.join(chr(10) + a + chr(10) for a in accessors)}"
        f"}}\n"
    )
    console.print(f"    Created: interfaces/rest/dto/Create{entity}Request.java")


def _gen_update_request(java_root: Path, pkg: str, entity: str, fields: list[dict]) -> None:
    """Generate UpdateXxxRequest DTO — same as Create for now."""
    dest = java_root / "interfaces" / "rest" / "dto" / f"Update{entity}Request.java"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)

    extra_imports = _collect_imports(fields)
    validation_imports = set()
    for f in fields:
        req = f.get("required", False)
        ft = f.get("type", "string")
        if req and ft in ("string", "text"):
            validation_imports.add("jakarta.validation.constraints.NotBlank")
        elif req:
            validation_imports.add("jakarta.validation.constraints.NotNull")
        if f.get("maxLength") or f.get("minLength"):
            validation_imports.add("jakarta.validation.constraints.Size")
        if f.get("min") is not None:
            validation_imports.add("jakarta.validation.constraints.Min")
        if f.get("max") is not None:
            validation_imports.add("jakarta.validation.constraints.Max")
        if f.get("pattern"):
            validation_imports.add("jakarta.validation.constraints.Pattern")

    all_imports = sorted(set(extra_imports) | validation_imports)
    import_lines = "\n".join(f"import {i};" for i in all_imports)
    if import_lines:
        import_lines = "\n" + import_lines

    field_lines = "\n\n".join(_java_field(f, with_validation=True) for f in fields)

    accessors = []
    for f in fields:
        java_type = _java_type_for_field(f)
        name = camel_case(f["name"])
        getter = f"get{pascal_case(f['name'])}"
        setter = f"set{pascal_case(f['name'])}"
        accessors.append(f"    public {java_type} {getter}() {{ return {name}; }}")
        accessors.append(f"    public void {setter}({java_type} {name}) {{ this.{name} = {name}; }}")

    dest.write_text(
        f"package {pkg}.interfaces.rest.dto;\n"
        f"{import_lines}\n"
        f"\n"
        f"public class Update{entity}Request {{\n"
        f"\n"
        f"{field_lines}\n"
        f"\n"
        f"{''.join(chr(10) + a + chr(10) for a in accessors)}"
        f"}}\n"
    )
    console.print(f"    Created: interfaces/rest/dto/Update{entity}Request.java")


def _gen_response_dto(java_root: Path, pkg: str, entity: str, fields: list[dict]) -> None:
    """Generate response DTO with all fields including id and timestamps."""
    dest = java_root / "interfaces" / "rest" / "dto" / f"{entity}Response.java"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)

    extra_imports = _collect_imports(fields)
    import_lines = "\n".join(f"import {i};" for i in extra_imports)
    if import_lines:
        import_lines = "\n" + import_lines

    field_defs = []
    accessors = []

    # Standard fields
    for fname, ftype in [("id", "Long"), ("tenantId", "String")]:
        field_defs.append(f"    private {ftype} {fname};")
        g = f"get{pascal_case(fname)}"
        s = f"set{pascal_case(fname)}"
        accessors.append(f"    public {ftype} {g}() {{ return {fname}; }}")
        accessors.append(f"    public void {s}({ftype} {fname}) {{ this.{fname} = {fname}; }}")

    # User fields
    for f in fields:
        java_type = _java_type_for_field(f)
        name = camel_case(f["name"])
        field_defs.append(f"    private {java_type} {name};")
        g = f"get{pascal_case(f['name'])}"
        s = f"set{pascal_case(f['name'])}"
        accessors.append(f"    public {java_type} {g}() {{ return {name}; }}")
        accessors.append(f"    public void {s}({java_type} {name}) {{ this.{name} = {name}; }}")

    # Timestamps
    for fname in ["createdAt", "updatedAt"]:
        field_defs.append(f"    private LocalDateTime {fname};")
        g = f"get{pascal_case(fname)}"
        s = f"set{pascal_case(fname)}"
        accessors.append(f"    public LocalDateTime {g}() {{ return {fname}; }}")
        accessors.append(f"    public void {s}(LocalDateTime {fname}) {{ this.{fname} = {fname}; }}")

    dest.write_text(
        f"package {pkg}.interfaces.rest.dto;\n"
        f"\n"
        f"import java.time.LocalDateTime;{import_lines}\n"
        f"\n"
        f"public class {entity}Response {{\n"
        f"\n"
        f"{''.join(chr(10) + d + chr(10) for d in field_defs)}"
        f"\n"
        f"{''.join(chr(10) + a + chr(10) for a in accessors)}"
        f"}}\n"
    )
    console.print(f"    Created: interfaces/rest/dto/{entity}Response.java")


def _gen_controller(java_root: Path, pkg: str, entity: str, name: str, fields: list[dict]) -> None:
    """Generate REST controller with CRUD endpoints."""
    dest = java_root / "interfaces" / "rest" / f"{entity}Controller.java"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)

    camel_case(name)

    # Build the mapping from request DTO to entity
    set_lines = []
    resp_lines = []
    for f in fields:
        camel_case(f["name"])
        pc = pascal_case(f["name"])
        set_lines.append(f"        entity.set{pc}(request.get{pc}());")
        resp_lines.append(f"        response.set{pc}(entity.get{pc}());")

    to_entity = "\n".join(set_lines)
    to_response = "\n".join(resp_lines)

    dest.write_text(
        f"package {pkg}.interfaces.rest;\n"
        f"\n"
        f"import {pkg}.domain.model.{entity};\n"
        f"import {pkg}.domain.service.{entity}Service;\n"
        f"import {pkg}.interfaces.rest.dto.Create{entity}Request;\n"
        f"import {pkg}.interfaces.rest.dto.Update{entity}Request;\n"
        f"import {pkg}.interfaces.rest.dto.{entity}Response;\n"
        f"import jakarta.validation.Valid;\n"
        f"import org.springframework.data.domain.Page;\n"
        f"import org.springframework.data.domain.PageRequest;\n"
        f"import org.springframework.http.HttpStatus;\n"
        f"import org.springframework.http.ResponseEntity;\n"
        f"import org.springframework.web.bind.annotation.*;\n"
        f"\n"
        f"@RestController\n"
        f'@RequestMapping("/{name}")\n'
        f"public class {entity}Controller {{\n"
        f"\n"
        f"    private final {entity}Service service;\n"
        f"\n"
        f"    public {entity}Controller({entity}Service service) {{\n"
        f"        this.service = service;\n"
        f"    }}\n"
        f"\n"
        f"    @GetMapping\n"
        f"    public ResponseEntity<Page<{entity}Response>> list(\n"
        f'            @RequestParam(defaultValue = "0") int page,\n'
        f'            @RequestParam(defaultValue = "20") int size) {{\n'
        f"        Page<{entity}Response> result = service.list(PageRequest.of(page, size))\n"
        f"            .map(this::toResponse);\n"
        f"        return ResponseEntity.ok(result);\n"
        f"    }}\n"
        f"\n"
        f'    @GetMapping("/{{id}}")\n'
        f"    public ResponseEntity<{entity}Response> getById(@PathVariable Long id) {{\n"
        f"        return ResponseEntity.ok(toResponse(service.getById(id)));\n"
        f"    }}\n"
        f"\n"
        f"    @PostMapping\n"
        f"    public ResponseEntity<{entity}Response> create(@Valid @RequestBody Create{entity}Request request) {{\n"
        f"        {entity} entity = new {entity}();\n"
        f"{to_entity}\n"
        f"        {entity} saved = service.create(entity);\n"
        f"        return ResponseEntity.status(HttpStatus.CREATED).body(toResponse(saved));\n"
        f"    }}\n"
        f"\n"
        f'    @PutMapping("/{{id}}")\n'
        f"    public ResponseEntity<{entity}Response> update(\n"
        f"            @PathVariable Long id,\n"
        f"            @Valid @RequestBody Update{entity}Request request) {{\n"
        f"        {entity} entity = new {entity}();\n"
        f"{to_entity.replace('Create', 'Update')}\n"
        f"        {entity} saved = service.update(id, entity);\n"
        f"        return ResponseEntity.ok(toResponse(saved));\n"
        f"    }}\n"
        f"\n"
        f'    @DeleteMapping("/{{id}}")\n'
        f"    @ResponseStatus(HttpStatus.NO_CONTENT)\n"
        f"    public void delete(@PathVariable Long id) {{\n"
        f"        service.delete(id);\n"
        f"    }}\n"
        f"\n"
        f"    private {entity}Response toResponse({entity} entity) {{\n"
        f"        {entity}Response response = new {entity}Response();\n"
        f"        response.setId(entity.getId());\n"
        f"        response.setTenantId(entity.getTenantId());\n"
        f"{to_response}\n"
        f"        response.setCreatedAt(entity.getCreatedAt());\n"
        f"        response.setUpdatedAt(entity.getUpdatedAt());\n"
        f"        return response;\n"
        f"    }}\n"
        f"}}\n"
    )
    console.print(f"    Created: interfaces/rest/{entity}Controller.java")


def _gen_integration_test(test_root: Path, pkg: str, entity: str, name: str, fields: list[dict]) -> None:
    """Generate an integration test for the resource CRUD endpoints."""
    dest = test_root / f"{entity}IntegrationTest.java"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Build a sample JSON body from fields for POST (escaped for Java string literals)
    json_fields = []
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        if ft in ("string", "text"):
            json_fields.append(f'\\"{fname}\\": \\"test-value\\"')
        elif ft in ("integer", "long"):
            json_fields.append(f'\\"{fname}\\": 1')
        elif ft == "decimal":
            json_fields.append(f'\\"{fname}\\": 9.99')
        elif ft == "boolean":
            json_fields.append(f'\\"{fname}\\": true')
        elif ft == "date":
            json_fields.append(f'\\"{fname}\\": \\"2025-01-15\\"')
        elif ft == "datetime":
            json_fields.append(f'\\"{fname}\\": \\"2025-01-15T10:00:00\\"')
    json_body = "{ " + ", ".join(json_fields) + " }"

    # Find a required string field for update test
    update_field = None
    for f in fields:
        if f.get("required") and f.get("type") in ("string", "text"):
            update_field = f
            break

    update_assertion = ""
    update_json = json_body
    if update_field:
        uf = camel_case(update_field["name"])
        update_json = json_body.replace('\\"test-value\\"', '\\"updated-value\\"', 1)
        update_assertion = f'\n            .andExpect(jsonPath("$.{uf}").value("updated-value"));'
    else:
        update_assertion = ";"

    # Find a required field name for validation test
    required_field = None
    for f in fields:
        if f.get("required"):
            required_field = f
            break
    validation_test = ""
    if required_field:
        # Build JSON with required field missing
        missing_fields = [jf for jf in json_fields if camel_case(required_field["name"]) not in jf]
        missing_json = "{ " + ", ".join(missing_fields) + " }" if missing_fields else "{}"
        validation_test = f"""

    @Test
    void create_withMissingRequiredField_returns400() throws Exception {{
        mockMvc.perform(post("/{name}")
                .header("X-Tenant-ID", TENANT_A)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{missing_json}"))
            .andExpect(status().isBadRequest());
    }}"""

    dest.write_text(
        f"package {pkg};\n"
        f"\n"
        f"import org.junit.jupiter.api.Test;\n"
        f"import org.springframework.http.MediaType;\n"
        f"\n"
        f"import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;\n"
        f"import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;\n"
        f"\n"
        f"/**\n"
        f" * Integration tests for /{name} CRUD endpoints.\n"
        f" * Uses a real PostgreSQL via Testcontainers (see AbstractIntegrationTest).\n"
        f" */\n"
        f"class {entity}IntegrationTest extends AbstractIntegrationTest {{\n"
        f"\n"
        f'    private static final String TENANT_A = "tenant-a";\n'
        f'    private static final String TENANT_B = "tenant-b";\n'
        f"\n"
        f"    @Test\n"
        f"    void crud_lifecycle() throws Exception {{\n"
        f"        // CREATE\n"
        f'        String response = mockMvc.perform(post("/{name}")\n'
        f'                .header("X-Tenant-ID", TENANT_A)\n'
        f"                .contentType(MediaType.APPLICATION_JSON)\n"
        f'                .content("{json_body}"))\n'
        f"            .andExpect(status().isCreated())\n"
        f'            .andExpect(jsonPath("$.id").isNumber())\n'
        f'            .andExpect(jsonPath("$.tenantId").value(TENANT_A))\n'
        f"            .andReturn().getResponse().getContentAsString();\n"
        f"\n"
        f"        // Extract ID from response\n"
        f'        long id = com.jayway.jsonpath.JsonPath.parse(response).read("$.id", Long.class);\n'
        f"\n"
        f"        // READ\n"
        f'        mockMvc.perform(get("/{name}/" + id)\n'
        f'                .header("X-Tenant-ID", TENANT_A))\n'
        f"            .andExpect(status().isOk())\n"
        f'            .andExpect(jsonPath("$.id").value(id));\n'
        f"\n"
        f"        // LIST — tenant A should see 1 item\n"
        f'        mockMvc.perform(get("/{name}")\n'
        f'                .header("X-Tenant-ID", TENANT_A))\n'
        f"            .andExpect(status().isOk())\n"
        f'            .andExpect(jsonPath("$.totalElements").value(1));\n'
        f"\n"
        f"        // LIST — tenant B should see 0 items (isolation)\n"
        f'        mockMvc.perform(get("/{name}")\n'
        f'                .header("X-Tenant-ID", TENANT_B))\n'
        f"            .andExpect(status().isOk())\n"
        f'            .andExpect(jsonPath("$.totalElements").value(0));\n'
        f"\n"
        f"        // UPDATE\n"
        f'        mockMvc.perform(put("/{name}/" + id)\n'
        f'                .header("X-Tenant-ID", TENANT_A)\n'
        f"                .contentType(MediaType.APPLICATION_JSON)\n"
        f'                .content("{update_json}"))\n'
        f"            .andExpect(status().isOk()){update_assertion}\n"
        f"\n"
        f"        // DELETE\n"
        f'        mockMvc.perform(delete("/{name}/" + id)\n'
        f'                .header("X-Tenant-ID", TENANT_A))\n'
        f"            .andExpect(status().isNoContent());\n"
        f"\n"
        f"        // READ after delete — 404\n"
        f'        mockMvc.perform(get("/{name}/" + id)\n'
        f'                .header("X-Tenant-ID", TENANT_A))\n'
        f"            .andExpect(status().isNotFound());\n"
        f"    }}\n"
        f"\n"
        f"    @Test\n"
        f"    void getById_wrongTenant_returns404() throws Exception {{\n"
        f"        // Create as tenant A\n"
        f'        String response = mockMvc.perform(post("/{name}")\n'
        f'                .header("X-Tenant-ID", TENANT_A)\n'
        f"                .contentType(MediaType.APPLICATION_JSON)\n"
        f'                .content("{json_body}"))\n'
        f"            .andExpect(status().isCreated())\n"
        f"            .andReturn().getResponse().getContentAsString();\n"
        f"\n"
        f'        long id = com.jayway.jsonpath.JsonPath.parse(response).read("$.id", Long.class);\n'
        f"\n"
        f"        // Try to read as tenant B — should not find it\n"
        f'        mockMvc.perform(get("/{name}/" + id)\n'
        f'                .header("X-Tenant-ID", TENANT_B))\n'
        f"            .andExpect(status().isNotFound());\n"
        f"    }}"
        f"{validation_test}\n"
        f"}}\n"
    )
    console.print(f"    Created: test/{entity}IntegrationTest.java")
