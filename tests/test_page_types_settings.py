"""Tests for the ``settings`` page type — grouped configuration form for a singleton."""

from __future__ import annotations

from pathlib import Path

from apps_generator.cli.generators.pages import (
    generate_page_components,
    get_registry,
)


# ── Registration ───────────────────────────────────────────────────────────


def test_settings_type_is_registered() -> None:
    info = get_registry().get("settings")
    assert info is not None
    assert info.source == "builtin"
    assert info.required_fields == ["resource"]
    assert info.description


# ── Emitter fixture ────────────────────────────────────────────────────────


def _generate_org_settings(tmp_path: Path, *, uikit: str = "my-ui") -> str:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "settings",
        "label": "Organization Settings",
        "resource": "orgSettings",
        "type": "settings",
        "fields": [
            {"name": "companyName", "type": "string", "group": "Company", "required": True},
            {"name": "billingEmail", "type": "string", "group": "Billing"},
            {"name": "autoRenew", "type": "boolean", "group": "Billing"},
            {"name": "maintenance", "type": "boolean"},  # ungrouped -> "General"
            {"name": "supportHours", "type": "integer", "group": "Support"},
            {"name": "notes", "type": "text", "group": "Support"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name=uikit,
        api_client_name="my-api",
    )
    return (project_root / "src" / "routes" / "SettingsPage.tsx").read_text()


# ── Singleton fetch + PUT ──────────────────────────────────────────────────


def test_settings_fetches_singleton_resource(tmp_path: Path) -> None:
    """GET /{resource} without an id — that's what makes it a settings page."""
    tsx = _generate_org_settings(tmp_path)
    assert "useQuery<OrgSettings>" in tsx
    assert 'api.get<OrgSettings>("/orgSettings")' in tsx
    # No id plumbing at all
    assert "URLSearchParams" not in tsx
    assert "${id}" not in tsx


def test_settings_saves_via_put_on_singleton(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path)
    assert 'api.put<OrgSettings>("/orgSettings", payload)' in tsx
    assert "UpdateOrgSettingsRequest" in tsx
    # No DELETE — settings are persistent config, not CRUD records
    assert "api.delete" not in tsx


def test_settings_hydrates_form_on_fetch(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path)
    assert "useEffect(() => {" in tsx
    # Numbers stringified for Input[type=number]
    assert 'supportHours: data.supportHours != null ? String(data.supportHours) : "",' in tsx
    # Booleans default to false
    assert "autoRenew: data.autoRenew ?? false," in tsx
    # Strings default to ""
    assert 'companyName: data.companyName ?? "",' in tsx


def test_settings_invalidates_its_own_query_on_save(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path)
    assert 'queryClient.invalidateQueries({ queryKey: ["orgSettings"] })' in tsx
    assert 't("updatedSuccessfully")' in tsx


# ── Grouping ───────────────────────────────────────────────────────────────


def test_settings_renders_accordion_with_all_groups_expanded(tmp_path: Path) -> None:
    """All groups open by default; users shouldn't have to click to see settings."""
    tsx = _generate_org_settings(tmp_path, uikit="my-ui")
    assert '<Accordion type="multiple"' in tsx
    # defaultValue lists every group in declaration order
    assert 'defaultValue={["Company", "Billing", "General", "Support"]}' in tsx


def test_settings_groups_fields_by_group_key(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path, uikit="my-ui")
    for g in ["Company", "Billing", "General", "Support"]:
        assert f'value="{g}">' in tsx
        assert f"<AccordionTrigger>{g}</AccordionTrigger>" in tsx


def test_settings_ungrouped_fields_go_into_general_section(tmp_path: Path) -> None:
    """Fields without a ``group`` key collect under "General" in declaration order."""
    tsx = _generate_org_settings(tmp_path, uikit="my-ui")
    # maintenance has no group, so it's inside the General accordion item.
    # Find the "General" AccordionItem and confirm the maintenance input is in it.
    general_start = tsx.index('value="General"')
    general_end = tsx.index("</AccordionItem>", general_start)
    general_body = tsx[general_start:general_end]
    assert 'id="maintenance"' in general_body


# ── Type-aware inputs ──────────────────────────────────────────────────────


def test_settings_renders_expected_inputs(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path, uikit="my-ui")
    assert '<Input id="companyName" type="text"' in tsx
    assert '<Input id="supportHours" type="number"' in tsx
    assert '<Checkbox id="autoRenew"' in tsx
    assert '<Checkbox id="maintenance"' in tsx
    assert '<Textarea id="notes"' in tsx


def test_settings_required_field_shows_star(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path)
    assert "Company Name *" in tsx


# ── Plain-HTML fallback ────────────────────────────────────────────────────


def test_settings_plain_fallback_uses_bordered_sections_no_accordion(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path, uikit="")
    # No Accordion in the plain branch
    assert "Accordion" not in tsx
    # Groups render as <section> with a heading instead
    assert '<section className="rounded-lg border p-4 space-y-4">' in tsx
    assert '<h2 className="font-semibold">Company</h2>' in tsx
    assert '<h2 className="font-semibold">Billing</h2>' in tsx
    assert '<h2 className="font-semibold">General</h2>' in tsx
    assert '<h2 className="font-semibold">Support</h2>' in tsx


def test_settings_plain_fallback_has_no_shadcn_imports(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path, uikit="")
    assert "Card" not in tsx
    assert "Checkbox" not in tsx


# ── Loading / error states ─────────────────────────────────────────────────


def test_settings_shows_loading_and_fetch_error(tmp_path: Path) -> None:
    tsx = _generate_org_settings(tmp_path)
    assert 't("loading")' in tsx
    assert 't("failedToLoad")' in tsx


# ── Edge case: all fields ungrouped ────────────────────────────────────────


def test_settings_with_no_group_keys_collects_everything_under_general(tmp_path: Path) -> None:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "settings",
        "label": "Simple Settings",
        "resource": "userPrefs",
        "type": "settings",
        "fields": [
            {"name": "theme", "type": "string"},
            {"name": "emailAlerts", "type": "boolean"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
    )
    tsx = (project_root / "src" / "routes" / "SettingsPage.tsx").read_text()
    # Exactly one AccordionItem — the "General" bucket
    assert tsx.count("<AccordionItem") == 1
    assert 'value="General"' in tsx
