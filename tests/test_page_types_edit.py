"""Tests for the ``edit`` page type — update form + delete confirmation."""

from __future__ import annotations

from pathlib import Path

from apps_generator.cli.generators.pages import (
    generate_page_components,
    get_registry,
)


# ── Registration ───────────────────────────────────────────────────────────


def test_edit_type_is_registered() -> None:
    info = get_registry().get("edit")
    assert info is not None
    assert info.source == "builtin"
    assert info.required_fields == ["resource"]
    assert info.description


# ── Emitter fixture ────────────────────────────────────────────────────────


def _generate_employee_edit(tmp_path: Path, *, uikit: str = "my-ui") -> str:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "edit",
        "label": "Edit Employee",
        "resource": "employee",
        "type": "edit",
        "fields": [
            {"name": "firstName", "type": "string", "required": True},
            {"name": "email", "type": "string"},
            {"name": "hireDate", "type": "date"},
            {"name": "startTime", "type": "datetime"},
            {"name": "salary", "type": "decimal"},
            {"name": "yearsExperience", "type": "integer"},
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
    return (project_root / "src" / "routes" / "EditPage.tsx").read_text()


# ── Fetch + hydrate ────────────────────────────────────────────────────────


def test_edit_reads_id_from_query_string(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    assert 'new URLSearchParams(window.location.search).get("id")' in tsx
    assert 't("missingId")' in tsx


def test_edit_fetches_existing_via_use_query(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    assert "useQuery<Employee>" in tsx
    assert "`/employee/${id}`" in tsx
    assert "enabled: !!id" in tsx


def test_edit_hydrates_form_state_from_fetched_record(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    # Numbers are stringified for the Input[type=number] controls
    assert 'salary: data.salary != null ? String(data.salary) : "",' in tsx
    assert 'yearsExperience: data.yearsExperience != null ? String(data.yearsExperience) : "",' in tsx
    # Booleans fall back to false
    assert "active: data.active ?? false," in tsx
    # datetime is trimmed to the 16 chars the <input type=datetime-local> expects
    assert 'startTime: data.startTime ? String(data.startTime).slice(0, 16) : "",' in tsx
    # Strings fall back to ""
    assert 'firstName: data.firstName ?? "",' in tsx
    # And hydration fires in a useEffect so it waits for the fetch
    assert "useEffect(() => {" in tsx


# ── Mutations ──────────────────────────────────────────────────────────────


def test_edit_uses_put_for_update(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    assert "api.put<Employee>(`/employee/${id}`, data)" in tsx
    assert "UpdateEmployeeRequest" in tsx


def test_edit_uses_delete_for_destructive_action(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    assert "api.delete<void>(`/employee/${id}`)" in tsx
    # After delete we return to wherever the user came from
    assert "window.history.back()" in tsx


def test_edit_invalidates_resource_queries(tmp_path: Path) -> None:
    """Both save and delete should invalidate the resource's cached queries."""
    tsx = _generate_employee_edit(tmp_path)
    assert tsx.count('queryClient.invalidateQueries({ queryKey: ["employee"] })') == 2


def test_edit_shows_updated_success_and_merged_errors(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    assert 't("updatedSuccessfully")' in tsx
    # A single error banner covers both mutations
    assert "(update.error || del_.error)" in tsx


# ── AlertDialog destructive confirm ────────────────────────────────────────


def test_edit_uses_alert_dialog_for_delete_confirm(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path, uikit="my-ui")
    for sym in [
        "AlertDialog",
        "AlertDialogTrigger",
        "AlertDialogContent",
        "AlertDialogHeader",
        "AlertDialogFooter",
        "AlertDialogTitle",
        "AlertDialogDescription",
        "AlertDialogAction",
        "AlertDialogCancel",
    ]:
        assert sym in tsx, f"missing AlertDialog symbol: {sym}"
    # Confirmation copy is i18n-keyed
    assert 't("confirmDelete")' in tsx
    assert 't("confirmDeleteDesc")' in tsx
    # Cancel + Confirm buttons
    assert 't("cancel")' in tsx
    assert 't("confirm")' in tsx
    # Confirm button actually triggers the mutation
    assert "onClick={() => del_.mutate()}" in tsx


def test_edit_plain_fallback_uses_confirm_prompt(tmp_path: Path) -> None:
    """Without --uikit we can't use AlertDialog; fall back to window.confirm."""
    tsx = _generate_employee_edit(tmp_path, uikit="")
    assert "AlertDialog" not in tsx
    assert 'confirm(t("confirmDelete"))' in tsx


# ── Form inputs match form_type behaviour ──────────────────────────────────


def test_edit_renders_type_aware_inputs(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    # Enum → <select> with the provided options
    assert '<option value="active">Active</option>' in tsx
    assert '<option value="inactive">Inactive</option>' in tsx
    # Checkbox for boolean
    assert '<Checkbox id="active"' in tsx
    # Textarea for text
    assert '<Textarea id="notes"' in tsx
    # Date fields now use the ui-kit DatePicker (Phase 0). Datetime stays
    # as a native <Input type="datetime-local"> — DatePicker has no time picker.
    assert "<DatePicker" in tsx
    assert 'id="hireDate"' in tsx
    assert '<Input id="startTime" type="datetime-local"' in tsx
    # Number inputs for integer/decimal
    assert '<Input id="yearsExperience" type="number"' in tsx
    assert '<Input id="salary" type="number" step="0.01"' in tsx


def test_edit_required_fields_show_star(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    assert "First Name *" in tsx
    # Non-required fields don't get the star
    assert ">Email<" in tsx or "Email</Label>" in tsx


# ── Plain-HTML fallback ────────────────────────────────────────────────────


def test_edit_plain_branch_has_no_shadcn_imports(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path, uikit="")
    assert "Card" not in tsx
    assert "AlertDialog" not in tsx


# ── Loading / error states ─────────────────────────────────────────────────


def test_edit_handles_fetch_loading_and_error(tmp_path: Path) -> None:
    tsx = _generate_employee_edit(tmp_path)
    assert 't("loading")' in tsx
    assert 't("failedToLoad")' in tsx


def test_edit_uses_datepicker_for_date_fields(tmp_path: Path) -> None:
    """Date fields swap to ui-kit DatePicker — converts ISO string <-> Date.

    The form state stays a YYYY-MM-DD string so the BE contract is
    unchanged; only the input widget swaps.
    """
    tsx = _generate_employee_edit(tmp_path, uikit="my-ui")
    assert "<DatePicker" in tsx
    # ISO string -> Date on read
    assert "form.hireDate ? new Date(form.hireDate) : undefined" in tsx
    # Date -> ISO string on write
    assert 'd ? d.toISOString().slice(0, 10) : ""' in tsx
    # No stale native date input
    assert '<Input id="hireDate" type="date"' not in tsx


def test_edit_uses_combobox_for_lookup_fields(tmp_path: Path) -> None:
    """Resource-lookup dropdowns swap to Combobox so they stay usable
    when the option list gets long."""
    # Second resource needed so `employeeName` auto-detects as a lookup
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "edit-leave",
        "label": "Edit Leave",
        "resource": "leave",
        "type": "edit",
        "fields": [
            {"name": "employeeName", "type": "string"},
            {"name": "startDate", "type": "date"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name="my-ui",
        api_client_name="my-api",
        all_resources=["leave", "employee"],
    )
    tsx = (project_root / "src" / "routes" / "EditLeavePage.tsx").read_text()
    assert "<Combobox" in tsx
    # Options built inline from the lookup query result
    assert "employeeOptions.map((opt: any) => ({ value:" in tsx
    # No stale native <select> for lookups
    assert 'id="employeeName"' in tsx
    # The surrounding <div> + Label wiring is intact
    assert 'htmlFor="employeeName"' in tsx


def test_edit_emits_valid_jsx_style_prop(tmp_path: Path) -> None:
    """Regression: the inline style prop is one double-brace (object literal), not four.

    An earlier version of the emitter over-escaped and wrote
    ``style={{{{ paddingTop: ... }}}}`` which is invalid JSX and breaks
    ``vite build``.
    """
    tsx = _generate_employee_edit(tmp_path)
    assert "{{{{" not in tsx
    assert "}}}}" not in tsx
    assert 'style={{ paddingTop: "1.5rem" }}' in tsx
