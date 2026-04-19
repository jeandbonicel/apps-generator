"""Tests for ``list`` / ``grid`` row-click-to-detail navigation via ``rowLink``.

Clicking a row (or a card in ``grid``) pushes
``{rowLink}?id=${row.id}`` through the MFE router's ``navigateTo``. The
feature is opt-in: pages without ``rowLink`` behave exactly as before,
which lets the large existing emitter test suite stay green without
edits. The tests below lock in that shape on both branches.
"""

from __future__ import annotations

from pathlib import Path

from apps_generator.cli.generators.pages import generate_page_components
from apps_generator.cli.generators.pages.base import normalize_row_link


# ── normalize_row_link ──────────────────────────────────────────────────────


def test_normalize_row_link_adds_leading_slash() -> None:
    assert normalize_row_link("detail") == "/detail"
    assert normalize_row_link("products/view") == "/products/view"


def test_normalize_row_link_preserves_leading_slash() -> None:
    assert normalize_row_link("/detail") == "/detail"
    assert normalize_row_link("/a/b/c") == "/a/b/c"


def test_normalize_row_link_returns_none_for_empty() -> None:
    assert normalize_row_link(None) is None
    assert normalize_row_link("") is None
    assert normalize_row_link("   ") is None


def test_normalize_row_link_ignores_non_strings() -> None:
    # Page configs come from JSON so we could see numbers or bools if a user
    # mistypes — don't crash, just opt-out.
    assert normalize_row_link(True) is None  # type: ignore[arg-type]
    assert normalize_row_link(123) is None  # type: ignore[arg-type]


# ── Fixtures ────────────────────────────────────────────────────────────────


def _generate_page(tmp_path: Path, page: dict, *, uikit: str = "my-ui") -> str:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name=uikit,
        api_client_name="my-api",
    )
    filename = {
        "list": "ListPage.tsx",
        "grid": "GridPage.tsx",
    }[page["type"]]
    return (project_root / "src" / "routes" / filename).read_text()


LIST_FIELDS = [
    {"name": "name", "type": "string"},
    {"name": "price", "type": "decimal"},
]


# ── list: default (opt-out) ─────────────────────────────────────────────────


def test_list_without_row_link_is_inert(tmp_path: Path) -> None:
    """No ``rowLink`` → no navigation wiring. Existing pages stay untouched."""
    tsx = _generate_page(
        tmp_path,
        {"path": "list", "label": "Products", "resource": "product", "type": "list", "fields": LIST_FIELDS},
    )
    assert "navigateTo" not in tsx
    assert "cursor-pointer" not in tsx
    # The TableRow stays bare — no onClick, no className
    assert "<TableRow key={p.id}>" in tsx


# ── list: ui-kit branch ─────────────────────────────────────────────────────


def test_list_with_row_link_imports_navigate_to(tmp_path: Path) -> None:
    tsx = _generate_page(
        tmp_path,
        {
            "path": "list",
            "label": "Products",
            "resource": "product",
            "type": "list",
            "fields": LIST_FIELDS,
            "rowLink": "products/view",
        },
    )
    assert 'import { navigateTo } from "../router";' in tsx


def test_list_with_row_link_wires_table_row_click(tmp_path: Path) -> None:
    tsx = _generate_page(
        tmp_path,
        {
            "path": "list",
            "label": "Products",
            "resource": "product",
            "type": "list",
            "fields": LIST_FIELDS,
            "rowLink": "products/view",
        },
    )
    # Normalised to a leading-slash path, interpolating p.id
    assert "navigateTo(`/products/view?id=${p.id}`)" in tsx
    # Pointer affordance so the row reads as interactive
    assert "cursor-pointer" in tsx
    # Attributes land on the TableRow, not on cells
    assert '<TableRow key={p.id} className="cursor-pointer hover:bg-accent transition-colors"' in tsx


# ── list: plain-HTML fallback ───────────────────────────────────────────────


def test_list_plain_branch_wires_tr_click(tmp_path: Path) -> None:
    tsx = _generate_page(
        tmp_path,
        {
            "path": "list",
            "label": "Products",
            "resource": "product",
            "type": "list",
            "fields": LIST_FIELDS,
            "rowLink": "/detail",
        },
        uikit="",
    )
    assert 'import { navigateTo } from "../router";' in tsx
    # Fallback uses a <tr> — the hover class must merge with the existing
    # ``border-b`` rather than overwrite it.
    assert 'className="border-b cursor-pointer hover:bg-accent transition-colors"' in tsx
    assert "navigateTo(`/detail?id=${p.id}`)" in tsx


# ── grid: default (opt-out) ─────────────────────────────────────────────────


def test_grid_without_row_link_is_inert(tmp_path: Path) -> None:
    tsx = _generate_page(
        tmp_path,
        {
            "path": "grid",
            "label": "Products",
            "resource": "product",
            "type": "grid",
            "fields": LIST_FIELDS,
        },
    )
    assert "navigateTo" not in tsx
    assert "cursor-pointer" not in tsx


# ── grid: ui-kit branch ─────────────────────────────────────────────────────


def test_grid_with_row_link_wires_card_click(tmp_path: Path) -> None:
    tsx = _generate_page(
        tmp_path,
        {
            "path": "grid",
            "label": "Products",
            "resource": "product",
            "type": "grid",
            "fields": LIST_FIELDS,
            "rowLink": "view",
        },
    )
    assert 'import { navigateTo } from "../router";' in tsx
    # The whole Card is clickable — onClick + className on the Card itself
    assert (
        '<Card key={p.id} className="cursor-pointer hover:shadow-md transition-shadow" '
        "onClick={() => navigateTo(`/view?id=${p.id}`)}>" in tsx
    )


# ── grid: plain-HTML fallback ───────────────────────────────────────────────


def test_grid_plain_branch_wires_div_click(tmp_path: Path) -> None:
    tsx = _generate_page(
        tmp_path,
        {
            "path": "grid",
            "label": "Products",
            "resource": "product",
            "type": "grid",
            "fields": LIST_FIELDS,
            "rowLink": "/inspect",
        },
        uikit="",
    )
    assert 'import { navigateTo } from "../router";' in tsx
    assert "navigateTo(`/inspect?id=${p.id}`)" in tsx
    assert "cursor-pointer" in tsx


# ── Empty rowLink string is treated as opt-out ──────────────────────────────


def test_list_empty_row_link_string_is_treated_as_opt_out(tmp_path: Path) -> None:
    """A blank ``rowLink`` string should not trigger the import path."""
    tsx = _generate_page(
        tmp_path,
        {
            "path": "list",
            "label": "Products",
            "resource": "product",
            "type": "list",
            "fields": LIST_FIELDS,
            "rowLink": "   ",
        },
    )
    assert "navigateTo" not in tsx
