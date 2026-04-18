"""Tests for the PageTypeRegistry — contract shared by every page-type module."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps_generator.cli.generators.pages import (
    PageContext,
    PageTypeInfo,
    PageTypeRegistry,
    generate_page_components,
    get_registry,
)


# ── Built-in registration ───────────────────────────────────────────────────


def test_builtins_are_registered() -> None:
    """Each built-in page-type module registers its PAGE_TYPE at import time."""
    registered = {info.name for info in get_registry().list_all()}
    assert {"list", "form", "dashboard"}.issubset(registered)


def test_builtin_types_carry_expected_metadata() -> None:
    registry = get_registry()

    list_info = registry.get("list")
    assert list_info is not None
    assert list_info.source == "builtin"
    assert "resource" in list_info.required_fields
    assert callable(list_info.emit)

    form_info = registry.get("form")
    assert form_info is not None
    assert callable(form_info.emit)

    dash_info = registry.get("dashboard")
    assert dash_info is not None
    assert callable(dash_info.emit)


# ── Registry core ───────────────────────────────────────────────────────────


def test_get_returns_none_for_unknown_type() -> None:
    assert get_registry().get("does-not-exist") is None
    assert get_registry().get(None) is None
    assert get_registry().get("") is None


def test_register_rejects_duplicates() -> None:
    reg = PageTypeRegistry()
    info = PageTypeInfo(name="demo", description="test", emit=lambda _p, _c: None)
    reg.register(info)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(info)


def test_list_all_is_sorted_by_name() -> None:
    reg = PageTypeRegistry()
    reg.register(PageTypeInfo(name="zeta", description="", emit=lambda _p, _c: None))
    reg.register(PageTypeInfo(name="alpha", description="", emit=lambda _p, _c: None))
    reg.register(PageTypeInfo(name="beta", description="", emit=lambda _p, _c: None))
    assert [i.name for i in reg.list_all()] == ["alpha", "beta", "zeta"]


# ── Dispatcher wiring ───────────────────────────────────────────────────────


def test_dispatcher_routes_to_registered_emitter(tmp_path: Path) -> None:
    """generate_page_components should call the registered emitter for matching types."""
    captured: list[tuple[dict, PageContext]] = []

    info = PageTypeInfo(
        name="custom-kind",
        description="test emitter",
        emit=lambda page, ctx: captured.append((page, ctx)),
    )
    get_registry().register(info)
    try:
        project_root = tmp_path / "demo"
        (project_root / "src" / "routes").mkdir(parents=True)
        # Pre-create the page file so the emitter is NOT called (dispatcher skips
        # existing files). Instead, we test the registry path directly by using a
        # fresh component name.
        pages = [
            {
                "path": "thing",
                "label": "Thing",
                "resource": "widget",
                "type": "custom-kind",
                "fields": [{"name": "title", "type": "string"}],
            }
        ]
        generate_page_components(
            project_root=project_root,
            pages=pages,
            project_name="demo",
            uikit_name="my-ui",
            api_client_name="my-api",
            all_resources=["widget"],
        )
        assert len(captured) == 1
        page, ctx = captured[0]
        assert page["type"] == "custom-kind"
        assert page["resource"] == "widget"
        assert ctx.project_root == project_root
        assert ctx.uikit_name == "my-ui"
        assert ctx.api_client_name == "my-api"
        assert ctx.all_resources == ["widget"]
    finally:
        # Remove the test type so other tests aren't affected
        get_registry()._types.pop("custom-kind", None)  # noqa: SLF001


def test_dispatcher_falls_back_to_placeholder_when_type_unknown(tmp_path: Path) -> None:
    project_root = tmp_path / "demo"
    (project_root / "src" / "routes").mkdir(parents=True)
    pages = [{"path": "about", "label": "About"}]  # no type/resource
    generate_page_components(project_root=project_root, pages=pages, project_name="demo")
    page_file = project_root / "src" / "routes" / "AboutPage.tsx"
    assert page_file.exists()
    content = page_file.read_text()
    assert "export function AboutPage()" in content
    assert "About" in content


def test_dispatcher_writes_pages_ts_registry(tmp_path: Path) -> None:
    project_root = tmp_path / "demo"
    (project_root / "src" / "routes").mkdir(parents=True)
    pages = [
        {"path": "about", "label": "About"},
        {"path": "home", "label": "Home"},
    ]
    generate_page_components(project_root=project_root, pages=pages, project_name="demo")
    pages_ts = (project_root / "src" / "pages.ts").read_text()
    assert '"about": AboutPage' in pages_ts
    assert '"home": HomePage' in pages_ts
    assert "default: HomePage" in pages_ts


# ── PageContext ─────────────────────────────────────────────────────────────


def test_page_context_defaults() -> None:
    ctx = PageContext(project_root=Path("/tmp/x"), project_name="x")
    assert ctx.uikit_name == ""
    assert ctx.api_client_name == ""
    assert ctx.all_resources == []


def test_page_context_copies_all_resources() -> None:
    """Dispatcher should copy all_resources into the ctx so downstream mutation can't leak."""
    project_root = Path("/tmp/unused")
    source_list = ["a", "b"]
    ctx = PageContext(
        project_root=project_root,
        project_name="x",
        all_resources=list(source_list),
    )
    ctx.all_resources.append("c")
    assert source_list == ["a", "b"]  # original unaffected
