"""Tests for the ``detail`` page type — read-only single-record view."""

from __future__ import annotations

from pathlib import Path

from apps_generator.cli.generators.pages import (
    generate_page_components,
    get_registry,
)


# ── Registration ───────────────────────────────────────────────────────────


def test_detail_type_is_registered() -> None:
    info = get_registry().get("detail")
    assert info is not None
    assert info.source == "builtin"
    assert info.required_fields == ["resource"]
    assert info.description  # non-empty human description


# ── Emitted output — ui-kit branch ─────────────────────────────────────────


def _generate_employee_detail(tmp_path: Path, *, uikit: str = "my-ui") -> str:
    """Run the dispatcher for a single detail page and return the emitted .tsx."""
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "view",
        "label": "Employee Detail",
        "resource": "employee",
        "type": "detail",
        "fields": [
            {"name": "firstName", "type": "string"},
            {"name": "lastName", "type": "string"},
            {"name": "email", "type": "string"},
            {"name": "hireDate", "type": "date"},
            {"name": "salary", "type": "decimal"},
            {"name": "active", "type": "boolean"},
            {"name": "status", "type": "enum", "values": ["active", "inactive"]},
            {"name": "notes", "type": "text"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name=uikit,
        api_client_name="my-api",
    )
    return (project_root / "src" / "routes" / "ViewPage.tsx").read_text()


def test_detail_emits_react_query_hook(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path)
    # Fetch via useQuery<Employee> against /employee/{id}
    assert "useQuery<Employee>" in tsx
    assert "`/employee/${id}`" in tsx
    # Query is disabled until id is known
    assert "enabled: !!id" in tsx


def test_detail_reads_id_from_query_string(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path)
    assert 'new URLSearchParams(window.location.search).get("id")' in tsx
    # Graceful handling when id is missing
    assert 't("missingId")' in tsx


def test_detail_renders_every_field_label(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path)
    # Field labels are rendered as <dt> text using title-case conversion.
    for expected in ["First Name", "Last Name", "Email", "Hire Date", "Salary", "Active", "Status", "Notes"]:
        assert f">{expected}<" in tsx, f"missing dt label: {expected!r}"


def test_detail_formats_types_correctly(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path)
    # decimal -> toFixed(2)
    assert "data.salary.toFixed(2)" in tsx
    # date -> new Date(...).toLocaleDateString()
    assert "new Date(data.hireDate).toLocaleDateString()" in tsx
    # boolean -> Yes/No via t() — ui-kit branch uses Badge
    assert 't("yes")' in tsx
    assert 't("no")' in tsx


def test_detail_uikit_branch_imports_shadcn(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path, uikit="my-ui")
    assert 'from "my-ui"' in tsx
    for sym in ["Card", "CardContent", "CardHeader", "CardTitle", "Badge", "Skeleton"]:
        assert sym in tsx, f"missing ui-kit import: {sym}"


def test_detail_uikit_branch_uses_badges_for_enum_and_boolean(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path, uikit="my-ui")
    # Enum values rendered as a secondary Badge
    assert '<Badge variant="secondary">' in tsx
    # Boolean rendered as default Badge for true, outline for false
    assert '<Badge variant="default">' in tsx
    assert '<Badge variant="outline">' in tsx


# ── Plain-HTML fallback ────────────────────────────────────────────────────


def test_detail_plain_branch_has_no_shadcn_imports(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path, uikit="")
    # No ui-kit import line
    assert "Card" not in tsx
    assert "Badge" not in tsx
    # But the page still works — semantics via <dl>/<dt>/<dd>
    assert "<dl" in tsx
    assert "<dt" in tsx
    assert "<dd" in tsx


def test_detail_plain_branch_boolean_uses_t_helper(tmp_path: Path) -> None:
    """Without ui-kit we can't render Badges — fall back to t('yes')/t('no')."""
    tsx = _generate_employee_detail(tmp_path, uikit="")
    assert 't("yes")' in tsx
    assert 't("no")' in tsx


# ── Loading & error states ─────────────────────────────────────────────────


def test_detail_shows_loading_skeleton(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path, uikit="my-ui")
    # One Skeleton label + value pair per field (8 fields => 16 skeletons)
    assert tsx.count("<Skeleton") == 16


def test_detail_shows_error_state(tmp_path: Path) -> None:
    tsx = _generate_employee_detail(tmp_path)
    assert 't("failedToLoad")' in tsx
    assert "(error as Error).message" in tsx
