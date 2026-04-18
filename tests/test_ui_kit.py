"""Tests for the ui-kit template — component presence, barrel exports, deps."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template


# ── Fixture: one generated ui-kit per test module ──────────────────────────


@pytest.fixture(scope="module")
def uikit_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a ui-kit project once and return its ``src/`` directory."""
    # mktemp() creates a dir; generate() refuses an existing output dir, so nest a
    # fresh subpath that generate() will create itself.
    parent = tmp_path_factory.mktemp("ui-kit-parent")
    template = resolve_template("ui-kit")
    result = generate(
        template_dir=template.path,
        output_dir=parent / "out",
        cli_values={"projectName": "test-ui"},
        interactive=False,
    )
    return result / "test-ui" / "src"


# ── Core inventory ─────────────────────────────────────────────────────────

# Every component file we expect under src/components/ui/. Keep this in sync
# with the full shadcn catalog we ship.
EXPECTED_COMPONENTS = [
    # Pre-existing (26)
    "alert",
    "avatar",
    "badge",
    "breadcrumb",
    "button",
    "card",
    "chart",
    "checkbox",
    "dialog",
    "dropdown-menu",
    "input",
    "label",
    "pagination",
    "progress",
    "scroll-area",
    "select",
    "separator",
    "sheet",
    "skeleton",
    "switch",
    "table",
    "tabs",
    "textarea",
    "toast",
    "toaster",
    "tooltip",
    # Phase 0 additions (12)
    "accordion",
    "alert-dialog",
    "calendar",
    "collapsible",
    "combobox",
    "command",
    "date-picker",
    "form",
    "navigation-menu",
    "popover",
    "radio-group",
    "sidebar",
]


def test_all_expected_component_files_exist(uikit_src: Path) -> None:
    ui_dir = uikit_src / "components" / "ui"
    missing = [name for name in EXPECTED_COMPONENTS if not (ui_dir / f"{name}.tsx").exists()]
    assert not missing, f"Missing component files: {missing}"


@pytest.mark.parametrize(
    "component,expected_exports",
    [
        ("popover", ["Popover", "PopoverTrigger", "PopoverContent"]),
        ("calendar", ["Calendar"]),
        ("date-picker", ["DatePicker"]),
        ("form", ["Form", "FormField", "FormItem", "FormLabel", "FormControl", "FormMessage"]),
        ("radio-group", ["RadioGroup", "RadioGroupItem"]),
        ("command", ["Command", "CommandInput", "CommandList", "CommandItem"]),
        ("combobox", ["Combobox"]),
        ("alert-dialog", ["AlertDialog", "AlertDialogAction", "AlertDialogCancel"]),
        ("collapsible", ["Collapsible", "CollapsibleTrigger", "CollapsibleContent"]),
        ("accordion", ["Accordion", "AccordionItem", "AccordionTrigger", "AccordionContent"]),
        ("sidebar", ["Sidebar", "SidebarProvider", "SidebarMenu", "SidebarMenuButton"]),
        ("navigation-menu", ["NavigationMenu", "NavigationMenuList", "NavigationMenuTrigger"]),
    ],
)
def test_component_exports_expected_symbols(
    uikit_src: Path, component: str, expected_exports: list[str]
) -> None:
    content = (uikit_src / "components" / "ui" / f"{component}.tsx").read_text()
    for sym in expected_exports:
        assert f"{sym}" in content, f"{component}.tsx missing symbol {sym!r}"


# ── Barrel (index.ts) ──────────────────────────────────────────────────────


def test_index_ts_reexports_phase_0_components(uikit_src: Path) -> None:
    index = (uikit_src / "index.ts").read_text()
    phase_0_symbols = [
        "Popover",
        "Calendar",
        "DatePicker",
        "Form",
        "FormField",
        "RadioGroup",
        "Combobox",
        "Command",
        "AlertDialog",
        "Collapsible",
        "Accordion",
        "Sidebar",
        "SidebarProvider",
        "NavigationMenu",
    ]
    missing = [s for s in phase_0_symbols if s not in index]
    assert not missing, f"index.ts missing re-exports: {missing}"


# ── Dependencies ───────────────────────────────────────────────────────────


def test_phase_0_dependencies_declared(uikit_src: Path) -> None:
    pkg_json = json.loads((uikit_src.parent / "package.json").read_text())
    deps = pkg_json["dependencies"]
    required = [
        "@hookform/resolvers",
        "@radix-ui/react-accordion",
        "@radix-ui/react-alert-dialog",
        "@radix-ui/react-collapsible",
        "@radix-ui/react-navigation-menu",
        "@radix-ui/react-popover",
        "@radix-ui/react-radio-group",
        "cmdk",
        "date-fns",
        "react-day-picker",
        "react-hook-form",
        "zod",
    ]
    missing = [d for d in required if d not in deps]
    assert not missing, f"Missing phase-0 dependencies: {missing}"


# ── Sidebar theme tokens ───────────────────────────────────────────────────


def test_globals_css_has_sidebar_theme_vars(uikit_src: Path) -> None:
    css = (uikit_src / "globals.css").read_text()
    # light + dark both define sidebar vars
    assert css.count("--sidebar-background:") >= 2
    assert "--sidebar-foreground:" in css
    assert "--sidebar-accent:" in css


def test_tailwind_preset_exposes_sidebar_colors(uikit_src: Path) -> None:
    preset = (uikit_src / "tailwind-preset.ts").read_text()
    assert "sidebar:" in preset
    assert "hsl(var(--sidebar-background))" in preset
    assert "accordion-down" in preset


# ── Stories ────────────────────────────────────────────────────────────────


def test_generated_output_has_no_jinja_residue(uikit_src: Path) -> None:
    """Nothing in the generated project should still contain Jinja markers.

    We burned on this once — a ``{% raw %}`` block that was never processed
    leaked into emitted .tsx/.json/.ts files, breaking them at parse time.
    Scan every generated source file for tell-tale Jinja syntax.
    """
    bad_patterns = ["{% raw %}", "{% endraw %}"]
    project_root = uikit_src.parent
    scan_extensions = {".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".md"}
    offenders: list[tuple[str, str]] = []
    for path in project_root.rglob("*"):
        if not path.is_file() or path.suffix not in scan_extensions:
            continue
        # Skip node_modules / dist / .git if a previous run populated them
        if any(part in {"node_modules", "dist", ".git"} for part in path.parts):
            continue
        content = path.read_text(errors="ignore")
        for pat in bad_patterns:
            if pat in content:
                offenders.append((str(path.relative_to(project_root)), pat))
    assert not offenders, f"Jinja residue in generated output: {offenders}"


def test_phase_0_stories_exist(uikit_src: Path) -> None:
    stories_dir = uikit_src.parent / "stories"
    expected_stories = [
        "Popover",
        "Calendar",
        "DatePicker",
        "Form",
        "RadioGroup",
        "Command",
        "Combobox",
        "AlertDialog",
        "Collapsible",
        "Accordion",
        "Sidebar",
        "NavigationMenu",
    ]
    missing = [s for s in expected_stories if not (stories_dir / f"{s}.stories.tsx").exists()]
    assert not missing, f"Missing story files: {missing}"
