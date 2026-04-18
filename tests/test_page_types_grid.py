"""Tests for the ``grid`` page type — card-grid view of a resource collection."""

from __future__ import annotations

from pathlib import Path

from apps_generator.cli.generators.pages import (
    generate_page_components,
    get_registry,
)


# ── Registration ───────────────────────────────────────────────────────────


def test_grid_type_is_registered() -> None:
    info = get_registry().get("grid")
    assert info is not None
    assert info.source == "builtin"
    assert info.required_fields == ["resource"]
    assert info.description


# ── Emitter output ─────────────────────────────────────────────────────────


def _generate_employee_grid(tmp_path: Path, *, uikit: str = "my-ui") -> str:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "team",
        "label": "Team Members",
        "resource": "employee",
        "type": "grid",
        "fields": [
            {"name": "firstName", "type": "string"},
            {"name": "lastName", "type": "string"},
            {"name": "email", "type": "string"},
            {"name": "hireDate", "type": "date"},
            {"name": "salary", "type": "decimal"},
            {"name": "active", "type": "boolean"},
            {"name": "status", "type": "enum", "values": ["active", "inactive"]},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name=uikit,
        api_client_name="my-api",
    )
    return (project_root / "src" / "routes" / "TeamPage.tsx").read_text()


def test_grid_uses_paginated_query(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path)
    assert "useQuery<PageResponse<Employee>>" in tsx
    assert '"/employee"' in tsx
    assert 'size: "20"' in tsx
    # Separate queryKey from the list page so caches don't collide
    assert '"employee", "grid", page' in tsx


def test_grid_uses_responsive_grid_container(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path)
    # 1 col mobile -> 2 md -> 3 lg is the canonical shadcn dashboard grid
    assert "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" in tsx
    assert "gap-4" in tsx


def test_grid_renders_cards_with_title_and_description(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path)
    # First string field becomes CardTitle, second becomes CardDescription
    assert "<CardTitle>{p.firstName ?? p.id}</CardTitle>" in tsx
    assert "<CardDescription>" in tsx
    assert "{p.lastName ?? null}" in tsx


def test_grid_body_skips_title_and_description_fields(tmp_path: Path) -> None:
    """firstName and lastName are consumed by title/description; shouldn't reappear in body."""
    tsx = _generate_employee_grid(tmp_path)
    # Each body row emits `<dt>{label}</dt>` — check neither of the promoted fields is in one
    assert ">First Name<" not in tsx
    assert ">Last Name<" not in tsx
    # But remaining fields are rendered as <dt> labels
    for expected in ["Email", "Hire Date", "Salary", "Active", "Status"]:
        assert f">{expected}<" in tsx, f"missing dt label: {expected!r}"


def test_grid_formats_types_correctly(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path)
    assert "p.salary.toFixed(2)" in tsx
    assert "new Date(p.hireDate).toLocaleDateString()" in tsx
    assert 't("yes")' in tsx
    assert 't("no")' in tsx


def test_grid_uikit_uses_badges_for_enum_and_boolean(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path, uikit="my-ui")
    assert '<Badge variant="secondary">' in tsx
    assert '<Badge variant="default">' in tsx
    assert '<Badge variant="outline">' in tsx


def test_grid_uikit_imports_card_and_badge(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path, uikit="my-ui")
    assert 'from "my-ui"' in tsx
    for sym in ["Card", "CardContent", "CardHeader", "CardTitle", "CardDescription", "Badge", "Button"]:
        assert sym in tsx, f"missing ui-kit import: {sym}"


def test_grid_pagination_controls(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path)
    assert 't("previous")' in tsx
    assert 't("next")' in tsx
    assert "page === 0" in tsx  # previous disabled at page 0
    assert "page >= totalPages - 1" in tsx  # next disabled at last page


def test_grid_shows_empty_state_spanning_grid_columns(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path)
    assert "col-span-full" in tsx
    assert 't("noDataFound")' in tsx


# ── Plain-HTML fallback ────────────────────────────────────────────────────


def test_grid_plain_branch_uses_raw_divs(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path, uikit="")
    # No ui-kit imports
    assert 'from ""' not in tsx  # defensive: never emit empty import path
    assert "Card" not in tsx
    assert "Badge" not in tsx
    # But the responsive grid container is still there
    assert "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" in tsx
    # And the card-like divs use matching Tailwind classes
    assert "rounded-lg border bg-card p-4" in tsx


def test_grid_plain_branch_boolean_uses_t_helper(tmp_path: Path) -> None:
    tsx = _generate_employee_grid(tmp_path, uikit="")
    assert 't("yes")' in tsx
    assert 't("no")' in tsx


# ── Single-string-field edge case ──────────────────────────────────────────


def test_grid_with_only_one_string_field_has_no_description(tmp_path: Path) -> None:
    """When there's only one string field, title is set but description is omitted."""
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "things",
        "label": "Things",
        "resource": "thing",
        "type": "grid",
        "fields": [
            {"name": "name", "type": "string"},
            {"name": "count", "type": "integer"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
    )
    tsx = (project_root / "src" / "routes" / "ThingsPage.tsx").read_text()
    assert "<CardTitle>{p.name ?? p.id}</CardTitle>" in tsx
    assert "<CardDescription>" not in tsx
    # And `count` (non-string) drops into the card body
    assert ">Count<" in tsx
