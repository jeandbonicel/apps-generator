"""Tests for i18n translation completeness.

Ensures:
1. Every EN key has a matching FR translation
2. Every FR key exists in EN (no orphaned translations)
3. Generated shell and frontend-app templates have consistent translations
4. No hardcoded English strings in generated components (spot check)
"""

import json
from pathlib import Path

from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template


TEMPLATE_BASE = Path(__file__).parent.parent / "src" / "apps_generator" / "templates" / "builtin"


# ── Translation key completeness ─────────────────────────────────────────────

def _load_locale(template_name: str, lang: str) -> dict:
    """Load a locale JSON file from a template."""
    if template_name == "platform_shell":
        path = TEMPLATE_BASE / "platform_shell" / "files" / "__projectName__" / "src" / "i18n" / "locales" / f"{lang}.json"
    elif template_name == "frontend_app":
        path = TEMPLATE_BASE / "frontend_app" / "files" / "__projectName__" / "src" / "i18n" / "locales" / f"{lang}.json"
    else:
        return {}
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def test_shell_en_fr_keys_match():
    """Every EN key in platform-shell has a matching FR translation."""
    en = _load_locale("platform_shell", "en")
    fr = _load_locale("platform_shell", "fr")

    missing_in_fr = set(en.keys()) - set(fr.keys())
    missing_in_en = set(fr.keys()) - set(en.keys())

    assert not missing_in_fr, f"Keys in EN but missing in FR: {missing_in_fr}"
    assert not missing_in_en, f"Keys in FR but missing in EN (orphaned): {missing_in_en}"


def test_frontend_en_fr_keys_match():
    """Every EN key in frontend-app has a matching FR translation."""
    en = _load_locale("frontend_app", "en")
    fr = _load_locale("frontend_app", "fr")

    missing_in_fr = set(en.keys()) - set(fr.keys())
    missing_in_en = set(fr.keys()) - set(en.keys())

    assert not missing_in_fr, f"Keys in EN but missing in FR: {missing_in_fr}"
    assert not missing_in_en, f"Keys in FR but missing in EN (orphaned): {missing_in_en}"


def test_shell_fr_values_not_empty():
    """No empty FR translation values in platform-shell."""
    fr = _load_locale("platform_shell", "fr")
    empty = [k for k, v in fr.items() if not v or not v.strip()]
    assert not empty, f"Empty FR translations: {empty}"


def test_frontend_fr_values_not_empty():
    """No empty FR translation values in frontend-app."""
    fr = _load_locale("frontend_app", "fr")
    empty = [k for k, v in fr.items() if not v or not v.strip()]
    assert not empty, f"Empty FR translations: {empty}"


def test_shell_has_essential_keys():
    """Platform-shell EN locale has all essential UI keys."""
    en = _load_locale("platform_shell", "en")
    essential = [
        "welcome", "home", "signIn", "signOut", "organization",
        "loading", "loadingModule", "selectOrganization",
        "errorTitle", "tryAgain", "pageNotFound",
        "previous", "next", "create", "creating", "createdSuccessfully",
        "noDataFound", "failedToLoad",
    ]
    missing = [k for k in essential if k not in en]
    assert not missing, f"Missing essential keys in shell EN: {missing}"


def test_frontend_has_essential_keys():
    """Frontend-app EN locale has all essential UI keys."""
    en = _load_locale("frontend_app", "en")
    essential = [
        "title", "welcome", "pageNotFound", "loading",
        "previous", "next", "create", "creating", "createdSuccessfully",
        "noDataFound", "failedToLoad",
    ]
    missing = [k for k in essential if k not in en]
    assert not missing, f"Missing essential keys in frontend EN: {missing}"


# ── No hardcoded English in generated shell ──────────────────────────────────

def test_shell_header_uses_i18n(tmp_path: Path):
    """Shell Header component uses t() and has no hardcoded English strings."""
    template = resolve_template("platform-shell")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "sh",
        cli_values={"projectName": "test-shell", "authProvider": "oidc"},
        interactive=False,
    )
    header = (result / "test-shell" / "src" / "layout" / "Header.tsx").read_text()
    # OIDC branch has a Sign Out button that must use t()
    assert "useTranslation" in header
    assert 't("signOut")' in header
    assert '"Sign Out"' not in header


def test_shell_error_boundary_uses_i18n(tmp_path: Path):
    """ErrorBoundary uses i18n for error title and try again button."""
    template = resolve_template("platform-shell")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "sh2",
        cli_values={"projectName": "test-shell2"},
        interactive=False,
    )
    eb = (result / "test-shell2" / "src" / "shell" / "ErrorBoundary.tsx").read_text()
    assert "errorTitle" in eb
    assert "tryAgain" in eb


def test_shell_remote_loader_uses_i18n(tmp_path: Path):
    """RemoteAppLoader uses t() for loading text."""
    template = resolve_template("platform-shell")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "sh3",
        cli_values={"projectName": "test-shell3"},
        interactive=False,
    )
    loader = (result / "test-shell3" / "src" / "layout" / "RemoteAppLoader.tsx").read_text()
    assert "useTranslation" in loader
    assert 't("loadingModule")' in loader
    assert '"Loading module..."' not in loader


def test_frontend_app_uses_i18n(tmp_path: Path):
    """Frontend-app App.tsx uses t() for page not found text."""
    template = resolve_template("frontend-app")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "fe",
        cli_values={"projectName": "test-fe", "devPort": "5001"},
        interactive=False,
    )
    app = (result / "test-fe" / "src" / "App.tsx").read_text()
    assert "useTranslation" in app
    assert 't("pageNotFound")' in app
    assert '"Page not found"' not in app


# ── Generated pages use i18n ─────────────────────────────────────────────────

def test_generated_list_page_uses_i18n(tmp_path: Path):
    """Generated list pages use t() for UI strings."""
    from apps_generator.cli.generators.pages import parse_pages, find_project_root, generate_page_components

    template = resolve_template("frontend-app")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "fe2",
        cli_values={"projectName": "test-fe2", "devPort": "5001"},
        interactive=False,
    )
    root = find_project_root(result, "test-fe2")
    pages = parse_pages('[{"path":"list","label":"Items","resource":"item","type":"list","fields":[{"name":"name","type":"string"}]}]')
    generate_page_components(root, pages, "test-fe2")

    content = (root / "src" / "routes" / "ListPage.tsx").read_text()
    assert "useTranslation" in content
    assert 't("loading")' in content
    assert 't("noDataFound")' in content
    assert 't("previous")' in content
    assert 't("next")' in content
