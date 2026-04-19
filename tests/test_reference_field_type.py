"""Tests for the ``reference`` field type — FK relations across resources.

Covers the backend side (Java ``Long`` columns + Liquibase
``addForeignKeyConstraint``), the TypeScript side (``number`` in
Create/Update/Response DTOs), the frontend form-rendering side
(auto-promoted to a Combobox lookup, including self-references), and the
``tree`` page's parent-field resolution via explicit ``reference`` fields.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from apps_generator.cli.generators.linking import find_java_root, find_resources_root
from apps_generator.cli.generators.pages import generate_page_components
from apps_generator.cli.generators.pages.base import detect_lookup
from apps_generator.cli.generators.resources import (
    generate_resource_scaffolding,
    parse_resources,
)
from apps_generator.cli.generators.types import generate_resource_types
from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template


# ── Backend: Java entity / DTOs ─────────────────────────────────────────────


def _generate_with_resources(tmp_path: Path, resources_json: str):
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
    java_root = find_java_root(result, "test-svc", "com.test.app")
    res_root = find_resources_root(result, "test-svc")
    resources = parse_resources(resources_json)
    generate_resource_scaffolding(java_root, res_root, resources, "com.test.app", "test-svc")
    return java_root, res_root


def test_reference_field_generates_long_column_on_entity(tmp_path: Path) -> None:
    java_root, _ = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {"name": "department", "fields": [{"name": "name", "type": "string"}]},
                {
                    "name": "employee",
                    "fields": [
                        {"name": "name", "type": "string"},
                        {"name": "departmentId", "type": "reference", "target": "department"},
                    ],
                },
            ]
        ),
    )
    entity = (java_root / "domain" / "model" / "Employee.java").read_text()
    # Stored as a plain Long id — no @ManyToOne navigation object, keeps the
    # DTO shape flat and lets the BFF stay boring.
    assert "private Long departmentId;" in entity
    # Getter/setter use the camelCase field name
    assert "public Long getDepartmentId()" in entity
    assert "public void setDepartmentId(Long departmentId)" in entity


def test_reference_field_dto_uses_number_like_type(tmp_path: Path) -> None:
    java_root, _ = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {"name": "department", "fields": [{"name": "name", "type": "string"}]},
                {
                    "name": "employee",
                    "fields": [
                        {"name": "departmentId", "type": "reference", "target": "department"},
                    ],
                },
            ]
        ),
    )
    create = (java_root / "interfaces" / "rest" / "dto" / "CreateEmployeeRequest.java").read_text()
    patch = (java_root / "interfaces" / "rest" / "dto" / "PatchEmployeeRequest.java").read_text()
    resp = (java_root / "interfaces" / "rest" / "dto" / "EmployeeResponse.java").read_text()
    for dto in (create, patch, resp):
        assert "private Long departmentId;" in dto


def test_reference_required_adds_not_null_on_dto(tmp_path: Path) -> None:
    java_root, _ = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {"name": "department", "fields": [{"name": "name", "type": "string"}]},
                {
                    "name": "employee",
                    "fields": [
                        {
                            "name": "departmentId",
                            "type": "reference",
                            "target": "department",
                            "required": True,
                        },
                    ],
                },
            ]
        ),
    )
    create = (java_root / "interfaces" / "rest" / "dto" / "CreateEmployeeRequest.java").read_text()
    # ``reference`` uses @NotNull, not @NotBlank (it's a Long, not a String)
    assert "@NotNull" in create
    # PATCH drops required-ness — reference field stays but @NotNull goes away
    patch = (java_root / "interfaces" / "rest" / "dto" / "PatchEmployeeRequest.java").read_text()
    assert "@NotNull" not in patch
    assert "private Long departmentId;" in patch


# ── Backend: Liquibase migration ────────────────────────────────────────────


def test_reference_field_emits_fk_constraint_in_migration(tmp_path: Path) -> None:
    _, res_root = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {"name": "department", "fields": [{"name": "name", "type": "string"}]},
                {
                    "name": "employee",
                    "fields": [
                        {"name": "departmentId", "type": "reference", "target": "department"},
                    ],
                },
            ]
        ),
    )
    # Employee is the second resource (seq 003) in the resources array
    changelog = yaml.safe_load((res_root / "db" / "changelog" / "changes" / "003-create-employee.yaml").read_text())
    changes = changelog["databaseChangeLog"][0]["changeSet"]["changes"]
    fk_changes = [c for c in changes if "addForeignKeyConstraint" in c]
    assert len(fk_changes) == 1
    fk = fk_changes[0]["addForeignKeyConstraint"]
    assert fk["baseTableName"] == "employees"
    assert fk["baseColumnNames"] == "department_id"
    assert fk["referencedTableName"] == "departments"
    assert fk["referencedColumnNames"] == "id"
    assert fk["constraintName"] == "fk_employees_department_id"


def test_reference_field_column_is_bigint(tmp_path: Path) -> None:
    _, res_root = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {"name": "department", "fields": [{"name": "name", "type": "string"}]},
                {
                    "name": "employee",
                    "fields": [
                        {"name": "departmentId", "type": "reference", "target": "department"},
                    ],
                },
            ]
        ),
    )
    changelog = yaml.safe_load((res_root / "db" / "changelog" / "changes" / "003-create-employee.yaml").read_text())
    columns = changelog["databaseChangeLog"][0]["changeSet"]["changes"][0]["createTable"]["columns"]
    dep_col = next(c["column"] for c in columns if c["column"]["name"] == "department_id")
    assert dep_col["type"] == "BIGINT"


def test_self_reference_fk_points_back_at_same_table(tmp_path: Path) -> None:
    """Self-referencing resource (hierarchical) gets a FK back to its own id."""
    _, res_root = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {
                    "name": "department",
                    "fields": [
                        {"name": "name", "type": "string"},
                        {"name": "parentId", "type": "reference", "target": "department"},
                    ],
                }
            ]
        ),
    )
    changelog = yaml.safe_load((res_root / "db" / "changelog" / "changes" / "002-create-department.yaml").read_text())
    changes = changelog["databaseChangeLog"][0]["changeSet"]["changes"]
    fk_changes = [c for c in changes if "addForeignKeyConstraint" in c]
    assert len(fk_changes) == 1
    fk = fk_changes[0]["addForeignKeyConstraint"]
    assert fk["baseTableName"] == "departments"
    assert fk["baseColumnNames"] == "parent_id"
    assert fk["referencedTableName"] == "departments"


# ── Backend: integration test ───────────────────────────────────────────────


def test_required_reference_is_skipped_for_validation_test(tmp_path: Path) -> None:
    """Reference fields can't be auto-populated (target row must exist), so the
    "missing required field" validation test picks a simpler required field
    or skips the test entirely. This keeps the generated test suite green.
    """
    java_root, _ = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {"name": "department", "fields": [{"name": "name", "type": "string"}]},
                {
                    "name": "employee",
                    "fields": [
                        {"name": "name", "type": "string", "required": True},
                        {
                            "name": "departmentId",
                            "type": "reference",
                            "target": "department",
                            "required": True,
                        },
                    ],
                },
            ]
        ),
    )
    test = (Path(str(java_root).replace("/main/java/", "/test/java/")) / "EmployeeIntegrationTest.java").read_text()
    # Validation test was generated — but drops ``name``, not ``departmentId``
    assert "withMissingRequiredField_returns400" in test
    # The missing-field JSON must still carry departmentId so the test isn't
    # also tripping the FK-not-null — just not ``name``.
    assert "name" not in test.split("withMissingRequiredField_returns400")[1].split("}")[0]


# ── TypeScript types ────────────────────────────────────────────────────────


def test_reference_field_ts_type_is_number(tmp_path: Path) -> None:
    src = tmp_path / "api-client" / "src"
    src.mkdir(parents=True)
    generate_resource_types(
        src,
        [
            {
                "name": "employee",
                "fields": [
                    {"name": "name", "type": "string", "required": True},
                    {"name": "departmentId", "type": "reference", "target": "department"},
                ],
            }
        ],
    )
    ts = (src / "resources" / "employee.ts").read_text()
    # Response allows null (FK can be absent), Create/Update optional
    assert "departmentId: number | null;" in ts
    assert "departmentId?: number;" in ts


# ── Lookup promotion ────────────────────────────────────────────────────────


def test_detect_lookup_promotes_reference_with_valid_target() -> None:
    field = {"name": "departmentId", "type": "reference", "target": "department"}
    lk = detect_lookup(field, ["department", "employee"], current_resource="employee")
    assert lk == {"resource": "department", "valueField": "id", "labelField": "name"}


def test_detect_lookup_allows_self_reference_for_explicit_reference() -> None:
    """Self-references are the whole point of tree-style configs — the
    heuristic branch filters self out, but the explicit branch must not."""
    field = {"name": "parentId", "type": "reference", "target": "department"}
    lk = detect_lookup(field, ["department"], current_resource="department")
    assert lk is not None
    assert lk["resource"] == "department"


def test_detect_lookup_returns_none_when_reference_target_is_unknown() -> None:
    field = {"name": "xId", "type": "reference", "target": "ghost"}
    assert detect_lookup(field, ["employee", "department"]) is None


def test_detect_lookup_heuristic_still_skips_current_resource() -> None:
    """Legacy heuristic path must not match a field on its own resource."""
    field = {"name": "employeeName", "type": "string"}
    assert detect_lookup(field, ["employee"], current_resource="employee") is None
    # But when ``employee`` is a *different* resource, the match stands
    assert detect_lookup(field, ["employee", "leave"], current_resource="leave") is not None


# ── Form / edit emitter wiring ──────────────────────────────────────────────


def test_form_renders_reference_as_combobox_with_uikit(tmp_path: Path) -> None:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "new",
        "label": "New Employee",
        "resource": "employee",
        "type": "form",
        "fields": [
            {"name": "name", "type": "string", "required": True},
            {"name": "departmentId", "type": "reference", "target": "department"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
        all_resources=["employee", "department"],
    )
    tsx = (project_root / "src" / "routes" / "NewPage.tsx").read_text()
    assert "<Combobox" in tsx
    # Fetches the target resource collection for options
    assert 'api.get("/department"' in tsx
    # departmentOptions is the variable name convention
    assert "departmentOptions" in tsx
    # Body casts the FK id to Number like other numeric fields
    assert "departmentId: form.departmentId ? Number(form.departmentId) : undefined," in tsx


def test_edit_renders_self_reference_as_combobox(tmp_path: Path) -> None:
    """Edit page on a self-referencing resource must offer a parent picker —
    the emitter used to pre-filter ``resource == current`` and blocked this."""
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "edit",
        "label": "Edit Department",
        "resource": "department",
        "type": "edit",
        "fields": [
            {"name": "name", "type": "string", "required": True},
            {"name": "parentId", "type": "reference", "target": "department"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
        all_resources=["department"],
    )
    tsx = (project_root / "src" / "routes" / "EditPage.tsx").read_text()
    assert "<Combobox" in tsx
    # Hydrates the FK id as a string (Combobox value is string)
    assert 'parentId: data.parentId != null ? String(data.parentId) : "",' in tsx
    # And casts back to Number on write
    assert "parentId: form.parentId ? Number(form.parentId) : undefined," in tsx


# ── Tree page: parent-field discovery ───────────────────────────────────────


def test_tree_uses_explicit_reference_field_as_parent(tmp_path: Path) -> None:
    """With an explicit ``reference`` self-ref, the tree uses *that* field —
    not the legacy ``parentId`` literal. This unblocks configs that want
    a different parent-pointer name (``managerId``, ``containerId``, ...)."""
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "org",
        "label": "Org Chart",
        "resource": "employee",
        "type": "tree",
        "fields": [
            {"name": "name", "type": "string"},
            {"name": "managerId", "type": "reference", "target": "employee"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
    )
    tsx = (project_root / "src" / "routes" / "OrgPage.tsx").read_text()
    # The renamed parent pointer flows into the buildTree generic
    assert "managerId?: string | number | null" in tsx
    assert ".managerId" in tsx
    # ``parentId`` must NOT leak through as a hardcoded literal
    assert "parentId" not in tsx


def test_tree_falls_back_to_parent_id_when_no_explicit_reference(tmp_path: Path) -> None:
    """Configs without an explicit reference field keep working via the legacy
    ``parentId`` convention."""
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "org",
        "label": "Org Chart",
        "resource": "department",
        "type": "tree",
        "fields": [
            {"name": "name", "type": "string"},
            {"name": "parentId", "type": "long"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
    )
    tsx = (project_root / "src" / "routes" / "OrgPage.tsx").read_text()
    assert "parentId?: string | number | null" in tsx


def test_tree_reference_to_other_resource_is_not_mistaken_for_parent(tmp_path: Path) -> None:
    """A reference that points to a *different* resource is not a parent
    pointer — the tree must keep looking for a self-ref or fall back to
    the legacy ``parentId`` name."""
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "org",
        "label": "Org Chart",
        "resource": "employee",
        "type": "tree",
        "fields": [
            {"name": "name", "type": "string"},
            {"name": "departmentId", "type": "reference", "target": "department"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
    )
    tsx = (project_root / "src" / "routes" / "OrgPage.tsx").read_text()
    # Fell back to the literal ``parentId`` — the cross-resource reference
    # was correctly ignored as a parent candidate.
    assert "parentId?: string | number | null" in tsx
