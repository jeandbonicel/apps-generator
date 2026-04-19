"""Tests for ``stringArray`` / ``enumArray`` field types + MultiSelect / TagInput.

Covers three layers:

1. **ui-kit** — ``MultiSelect`` and ``TagInput`` component files exist and
   re-exported from the barrel ``index.ts``.
2. **api-domain** — Java entity uses ``@ElementCollection`` + a
   ``@CollectionTable`` join table; Liquibase migration emits the join
   table + CASCADE FK; DTOs round-trip as plain ``List<...>``; TypeScript
   types surface as ``string[]`` / ``(union)[]``.
3. **frontend-app** — ``form`` / ``edit`` emitters render TagInput for
   ``stringArray`` and MultiSelect for ``enumArray`` when ``--uikit`` is
   linked, with plain-HTML fallback otherwise.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from apps_generator.cli.generators.linking import find_java_root, find_resources_root
from apps_generator.cli.generators.pages import generate_page_components
from apps_generator.cli.generators.resources import (
    generate_resource_scaffolding,
    parse_resources,
)
from apps_generator.cli.generators.types import generate_resource_types
from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template


# ── ui-kit: MultiSelect + TagInput components ───────────────────────────────


def test_ui_kit_ships_multi_select_component() -> None:
    path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "apps_generator"
        / "templates"
        / "builtin"
        / "ui_kit"
        / "files"
        / "__projectName__"
        / "src"
        / "components"
        / "ui"
        / "multi-select.tsx"
    )
    assert path.exists()
    content = path.read_text()
    assert "export { MultiSelect }" in content
    # MultiSelect composes Command + Popover + Badge — all three primitives
    # are what makes it a "typeahead with selected chips" experience.
    for sym in ["Command", "Popover", "Badge"]:
        assert sym in content, f"multi-select.tsx missing import of {sym}"
    # Value / onChange contract is an array
    assert "value?: string[]" in content
    assert "onChange?: (value: string[]) => void" in content


def test_ui_kit_ships_tag_input_component() -> None:
    path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "apps_generator"
        / "templates"
        / "builtin"
        / "ui_kit"
        / "files"
        / "__projectName__"
        / "src"
        / "components"
        / "ui"
        / "tag-input.tsx"
    )
    assert path.exists()
    content = path.read_text()
    assert "export { TagInput }" in content
    # Enter + comma commit the draft; Backspace peels off the last tag —
    # these are the keyboard semantics users expect from chip inputs.
    assert '"Enter"' in content
    assert '"Backspace"' in content


def test_ui_kit_index_reexports_multi_select_and_tag_input() -> None:
    path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "apps_generator"
        / "templates"
        / "builtin"
        / "ui_kit"
        / "files"
        / "__projectName__"
        / "src"
        / "index.ts"
    )
    content = path.read_text()
    assert "MultiSelect" in content
    assert "MultiSelectOption" in content
    assert "TagInput" in content


# ── api-domain: Java entity ─────────────────────────────────────────────────


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


def test_string_array_entity_uses_element_collection(tmp_path: Path) -> None:
    java_root, _ = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {
                    "name": "product",
                    "fields": [
                        {"name": "name", "type": "string"},
                        {"name": "tags", "type": "stringArray"},
                    ],
                }
            ]
        ),
    )
    entity = (java_root / "domain" / "model" / "Product.java").read_text()
    # Collection mapping — fetch eagerly so the DTO mapping sees the list
    # without LazyInitializationException wobbles in the controller.
    assert "@ElementCollection(fetch = FetchType.EAGER)" in entity
    # Collection-table name + FK column spelled explicitly so schema and
    # mapping can never drift.
    assert '@CollectionTable(name = "products_tags"' in entity
    assert '@JoinColumn(name = "product_id")' in entity
    # Value column
    assert '@Column(name = "tags")' in entity
    # Default initializer so callers don't have to null-check
    assert "private List<String> tags = new ArrayList<>()" in entity
    # Required imports
    assert "import java.util.List;" in entity
    assert "import java.util.ArrayList;" in entity


def test_enum_array_entity_uses_element_collection_plus_enumerated(tmp_path: Path) -> None:
    java_root, _ = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {
                    "name": "post",
                    "fields": [
                        {"name": "title", "type": "string"},
                        {
                            "name": "channels",
                            "type": "enumArray",
                            "values": ["email", "sms", "push"],
                        },
                    ],
                }
            ]
        ),
    )
    entity = (java_root / "domain" / "model" / "Post.java").read_text()
    # Same ElementCollection shape...
    assert "@ElementCollection(fetch = FetchType.EAGER)" in entity
    assert '@CollectionTable(name = "posts_channels"' in entity
    # ...plus @Enumerated so each row stores the enum's string name
    assert "@Enumerated(EnumType.STRING)" in entity
    # Typed as a List of the generated enum class (named after the field)
    assert "private List<Channels> channels = new ArrayList<>()" in entity
    # The enum class itself was generated
    assert (java_root / "domain" / "model" / "Channels.java").exists()


def test_array_fields_in_dto_are_plain_lists(tmp_path: Path) -> None:
    """DTOs strip the JPA annotations — just a plain ``List<...>`` the
    JSON deserializer can populate from a request array body."""
    java_root, _ = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {
                    "name": "product",
                    "fields": [
                        {"name": "name", "type": "string"},
                        {"name": "tags", "type": "stringArray"},
                    ],
                }
            ]
        ),
    )
    create = (java_root / "interfaces" / "rest" / "dto" / "CreateProductRequest.java").read_text()
    patch = (java_root / "interfaces" / "rest" / "dto" / "PatchProductRequest.java").read_text()
    resp = (java_root / "interfaces" / "rest" / "dto" / "ProductResponse.java").read_text()
    for dto in (create, patch, resp):
        assert "private List<String> tags;" in dto
        # DTOs must NOT leak the entity-side JPA annotations
        assert "@ElementCollection" not in dto
        assert "@CollectionTable" not in dto


def test_enum_array_dto_imports_generated_enum_class(tmp_path: Path) -> None:
    """Enum classes live under ``{pkg}.domain.model`` — DTOs need the
    explicit import or they fail to compile (same fix as the scalar
    ``enum`` regression the suite already guards)."""
    java_root, _ = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {
                    "name": "post",
                    "fields": [
                        {
                            "name": "channels",
                            "type": "enumArray",
                            "values": ["email", "sms"],
                        }
                    ],
                }
            ]
        ),
    )
    for dto in ["CreatePostRequest", "UpdatePostRequest", "PatchPostRequest", "PostResponse"]:
        content = (java_root / "interfaces" / "rest" / "dto" / f"{dto}.java").read_text()
        assert "import com.test.app.domain.model.Channels;" in content
        assert "private List<Channels> channels;" in content


# ── api-domain: migration ───────────────────────────────────────────────────


def test_string_array_migration_emits_join_table(tmp_path: Path) -> None:
    _, res_root = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {
                    "name": "product",
                    "fields": [
                        {"name": "name", "type": "string"},
                        {"name": "tags", "type": "stringArray"},
                    ],
                }
            ]
        ),
    )
    changelog = yaml.safe_load((res_root / "db" / "changelog" / "changes" / "002-create-product.yaml").read_text())
    changes = changelog["databaseChangeLog"][0]["changeSet"]["changes"]

    # Main table: ``tags`` column must NOT appear — it lives in the join
    # table, not on ``products``.
    main_cols = changes[0]["createTable"]["columns"]
    assert all(c["column"]["name"] != "tags" for c in main_cols)

    # Join-table createTable
    join_creates = [
        c["createTable"] for c in changes if "createTable" in c and c["createTable"]["tableName"] == "products_tags"
    ]
    assert len(join_creates) == 1
    join_cols = join_creates[0]["columns"]
    assert any(c["column"]["name"] == "product_id" for c in join_cols)
    assert any(c["column"]["name"] == "tags" for c in join_cols)

    # FK with CASCADE so deleting the parent cleans up element rows
    fks = [
        c["addForeignKeyConstraint"]
        for c in changes
        if "addForeignKeyConstraint" in c and c["addForeignKeyConstraint"]["baseTableName"] == "products_tags"
    ]
    assert len(fks) == 1
    assert fks[0]["onDelete"] == "CASCADE"
    assert fks[0]["referencedTableName"] == "products"


def test_enum_array_migration_sizes_column_from_longest_value(tmp_path: Path) -> None:
    _, res_root = _generate_with_resources(
        tmp_path,
        json.dumps(
            [
                {
                    "name": "post",
                    "fields": [
                        {
                            "name": "channels",
                            "type": "enumArray",
                            "values": ["email", "push-notification"],
                        }
                    ],
                }
            ]
        ),
    )
    changelog = yaml.safe_load((res_root / "db" / "changelog" / "changes" / "002-create-post.yaml").read_text())
    changes = changelog["databaseChangeLog"][0]["changeSet"]["changes"]
    join_create = next(
        c["createTable"] for c in changes if "createTable" in c and c["createTable"]["tableName"] == "posts_channels"
    )
    value_col = next(c["column"] for c in join_create["columns"] if c["column"]["name"] == "channels")
    # len("push-notification") == 17 → VARCHAR(17)
    assert value_col["type"] == "VARCHAR(17)"


# ── TypeScript types ────────────────────────────────────────────────────────


def test_string_array_ts_type_is_array(tmp_path: Path) -> None:
    src = tmp_path / "api-client" / "src"
    src.mkdir(parents=True)
    generate_resource_types(
        src,
        [
            {
                "name": "product",
                "fields": [
                    {"name": "name", "type": "string", "required": True},
                    {"name": "tags", "type": "stringArray"},
                ],
            }
        ],
    )
    ts = (src / "resources" / "product.ts").read_text()
    # Response allows null; Create uses optional — same pattern as scalars
    assert "tags: string[] | null;" in ts
    assert "tags?: string[];" in ts


def test_enum_array_ts_type_is_parenthesised_union_array(tmp_path: Path) -> None:
    src = tmp_path / "api-client" / "src"
    src.mkdir(parents=True)
    generate_resource_types(
        src,
        [
            {
                "name": "post",
                "fields": [
                    {
                        "name": "channels",
                        "type": "enumArray",
                        "values": ["email", "sms", "push"],
                    }
                ],
            }
        ],
    )
    ts = (src / "resources" / "post.ts").read_text()
    # The union is parenthesised so ``[]`` binds to the whole thing — without
    # that, TS parses ``"a" | "b"[]`` as ``"a" | ("b"[])``.
    assert 'channels: ("email" | "sms" | "push")[] | null;' in ts


# ── Form emitter: ui-kit branch ─────────────────────────────────────────────


def _emit_form(tmp_path: Path, fields: list[dict], *, uikit: str = "my-ui") -> str:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    generate_page_components(
        project_root=project_root,
        pages=[
            {
                "path": "new",
                "label": "New",
                "resource": "product",
                "type": "form",
                "fields": fields,
            }
        ],
        project_name="demo",
        uikit_name=uikit,
        api_client_name="my-api",
    )
    return (project_root / "src" / "routes" / "NewPage.tsx").read_text()


def test_form_renders_string_array_as_tag_input_with_uikit(tmp_path: Path) -> None:
    tsx = _emit_form(
        tmp_path,
        [
            {"name": "name", "type": "string"},
            {"name": "tags", "type": "stringArray"},
        ],
    )
    # TagInput imported from ui-kit + wired with value / onChange
    assert "TagInput" in tsx
    assert "<TagInput" in tsx
    assert "value={form.tags}" in tsx
    # Form state default for arrays is [] not ""
    assert "tags: [] as string[]" in tsx
    # Body builder passes the array through (no Number cast, no || undefined)
    assert "tags: form.tags," in tsx


def test_form_renders_enum_array_as_multi_select_with_uikit(tmp_path: Path) -> None:
    tsx = _emit_form(
        tmp_path,
        [
            {"name": "title", "type": "string"},
            {
                "name": "channels",
                "type": "enumArray",
                "values": ["email", "sms", "push"],
            },
        ],
    )
    assert "MultiSelect" in tsx
    assert "<MultiSelect" in tsx
    # Options built from the field's ``values`` list — keyed by value, labelled
    # with the title-cased enum name so display stays human-readable.
    assert '{ value: "email", label: "Email" }' in tsx
    assert '{ value: "sms", label: "Sms" }' in tsx
    assert "channels: [] as string[]" in tsx


# ── Form emitter: plain-HTML fallback ───────────────────────────────────────


def test_form_plain_branch_uses_comma_input_for_string_array(tmp_path: Path) -> None:
    """Without --uikit, there's no TagInput — fall back to a comma-separated
    ``<input>``. Ugly but unambiguous and the form still submits an array."""
    tsx = _emit_form(
        tmp_path,
        [
            {"name": "tags", "type": "stringArray"},
        ],
        uikit="",
    )
    assert "TagInput" not in tsx
    # Value is joined with ", " for display; on edit we split + trim + drop blanks
    assert "form.tags.join(', ')" in tsx
    assert ".split(',').map((s: string) => s.trim()).filter(Boolean)" in tsx


def test_form_plain_branch_uses_multi_select_element_for_enum_array(tmp_path: Path) -> None:
    tsx = _emit_form(
        tmp_path,
        [
            {
                "name": "channels",
                "type": "enumArray",
                "values": ["email", "sms"],
            }
        ],
        uikit="",
    )
    assert "MultiSelect" not in tsx
    # Native ``<select multiple>`` with Array.from(selectedOptions, ...)
    assert "<select multiple" in tsx
    assert "Array.from(e.target.selectedOptions" in tsx


# ── Edit emitter: hydrate + body ────────────────────────────────────────────


def test_edit_hydrates_array_fields_from_fetched_record(tmp_path: Path) -> None:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    generate_page_components(
        project_root=project_root,
        pages=[
            {
                "path": "edit",
                "label": "Edit Product",
                "resource": "product",
                "type": "edit",
                "fields": [
                    {"name": "name", "type": "string"},
                    {"name": "tags", "type": "stringArray"},
                    {
                        "name": "channels",
                        "type": "enumArray",
                        "values": ["email", "sms"],
                    },
                ],
            }
        ],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
    )
    tsx = (project_root / "src" / "routes" / "EditPage.tsx").read_text()
    # Null-safe hydration — falls back to [] so the controlled widget never
    # flips through ``undefined``.
    assert "tags: data.tags ?? []," in tsx
    assert "channels: data.channels ?? []," in tsx
    # Both widgets imported and rendered
    assert "TagInput" in tsx
    assert "MultiSelect" in tsx
    # PUT body passes arrays straight through
    assert "tags: form.tags," in tsx
    assert "channels: form.channels," in tsx
