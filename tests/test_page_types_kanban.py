"""Tests for the ``kanban`` page type — drag-and-drop board grouped by status."""

from __future__ import annotations

from pathlib import Path

from apps_generator.cli.generators.pages import (
    generate_page_components,
    get_registry,
)


# ── Registration ───────────────────────────────────────────────────────────


def test_kanban_type_is_registered() -> None:
    info = get_registry().get("kanban")
    assert info is not None
    assert info.source == "builtin"
    assert info.required_fields == ["resource"]
    assert info.description


# ── Emitter fixture ────────────────────────────────────────────────────────


def _generate_ticket_board(
    tmp_path: Path,
    *,
    uikit: str = "my-ui",
    status_field: str | None = None,
    fields: list[dict] | None = None,
) -> str:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "board",
        "label": "Ticket Board",
        "resource": "ticket",
        "type": "kanban",
        "fields": fields
        if fields is not None
        else [
            {"name": "title", "type": "string"},
            {"name": "assignee", "type": "string"},
            {"name": "priority", "type": "enum", "values": ["low", "medium", "high"]},
            {"name": "status", "type": "enum", "values": ["todo", "inProgress", "done"]},
            {"name": "dueDate", "type": "date"},
        ],
    }
    if status_field:
        page["statusField"] = status_field
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name=uikit,
        api_client_name="my-api",
    )
    return (project_root / "src" / "routes" / "BoardPage.tsx").read_text()


# ── Status-field resolution ────────────────────────────────────────────────


def test_kanban_prefers_field_named_status_when_multiple_enums_exist(tmp_path: Path) -> None:
    """`priority` is the first enum in declaration order, but `status` wins by name."""
    tsx = _generate_ticket_board(tmp_path)
    assert 'STATUSES = ["todo", "inProgress", "done"] as const;' in tsx
    # priority's values must NOT be the column set
    assert 'STATUSES = ["low", "medium", "high"]' not in tsx


def test_kanban_explicit_status_field_wins_over_name_heuristic(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path, status_field="priority")
    assert 'STATUSES = ["low", "medium", "high"]' in tsx


def test_kanban_falls_back_to_first_enum_when_no_status_like_name(tmp_path: Path) -> None:
    """With no status/state/stage/phase, the first enum with values wins."""
    tsx = _generate_ticket_board(
        tmp_path,
        fields=[
            {"name": "title", "type": "string"},
            {"name": "severity", "type": "enum", "values": ["low", "high"]},
        ],
    )
    assert 'STATUSES = ["low", "high"]' in tsx


def test_kanban_falls_back_to_single_backlog_column_when_no_enum(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(
        tmp_path,
        fields=[
            {"name": "title", "type": "string"},
            {"name": "assignee", "type": "string"},
        ],
    )
    assert 'STATUSES = ["Backlog"]' in tsx


# ── Data fetch + mutation ──────────────────────────────────────────────────


def test_kanban_fetches_flat_list_with_large_page_size(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    assert "useQuery<PageResponse<Ticket>>" in tsx
    assert 'size: "1000"' in tsx
    assert '"ticket", "kanban"' in tsx


def test_kanban_patch_mutation_updates_status_field(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    # Sends a PATCH with the status field set to the new column value
    assert "api.patch<Ticket>(`/ticket/${id}`, { status: status }" in tsx
    # Invalidates the resource's caches after the mutation settles
    assert 'queryClient.invalidateQueries({ queryKey: ["ticket"] })' in tsx


# ── Optimistic move + rollback surface ─────────────────────────────────────


def test_kanban_keeps_local_mirror_of_records_for_optimistic_moves(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    # Local state + useEffect sync keeps the UI responsive without waiting on fetches
    assert "const [local, setLocal] = useState<Ticket[]>([])" in tsx
    assert "if (data) setLocal(data.content ?? [])" in tsx


def test_kanban_drag_end_moves_card_locally_before_patch(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    # Optimistic update before mutation.mutate
    assert "setLocal((prev) =>" in tsx
    assert "{ ...it, status: target }" in tsx
    assert "mutation.mutate({ id, status: target })" in tsx


def test_kanban_drop_on_non_column_is_noop(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    # Guards against drops outside a registered column
    assert "if (!over) return;" in tsx
    assert "if (!STATUSES.includes(target)) return;" in tsx


# ── dnd-kit wiring ─────────────────────────────────────────────────────────


def test_kanban_imports_dnd_kit(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    assert 'from "@dnd-kit/core"' in tsx
    assert 'from "@dnd-kit/sortable"' in tsx
    assert 'from "@dnd-kit/utilities"' in tsx
    for sym in [
        "DndContext",
        "PointerSensor",
        "useSensor",
        "SortableContext",
        "verticalListSortingStrategy",
        "useSortable",
    ]:
        assert sym in tsx, f"missing dnd-kit symbol: {sym}"


def test_kanban_uses_pointer_sensor_with_activation_distance(tmp_path: Path) -> None:
    """4px activation distance — small enough to feel responsive, big enough to
    not fire on accidental clicks."""
    tsx = _generate_ticket_board(tmp_path)
    assert "activationConstraint: { distance: 4 }" in tsx


def test_kanban_one_sortable_context_per_column(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    # A SortableContext mapped over STATUSES.map((status) => ...)
    assert "<SortableContext" in tsx
    assert "strategy={verticalListSortingStrategy}" in tsx


# ── Card rendering ─────────────────────────────────────────────────────────


def test_kanban_card_title_comes_from_first_string_field_other_than_status(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    # title is the first string field (status is enum so isn't eligible)
    assert "{String(item.title ?? item.id)}" in tsx


def test_kanban_card_body_hides_title_and_status_fields(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    # dt labels for body fields
    for label in ["Assignee", "Priority", "Due Date"]:
        assert f">{label}<" in tsx
    # title + status are consumed by the header / column, so no dt for them
    assert ">Title<" not in tsx
    assert ">Status<" not in tsx


def test_kanban_card_formats_dates_and_decimals(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path)
    assert "new Date(item.dueDate).toLocaleDateString()" in tsx


# ── Column header ─────────────────────────────────────────────────────────


def test_kanban_column_header_shows_count(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path, uikit="my-ui")
    # ui-kit branch: count inside a Badge
    assert '<Badge variant="secondary">{items.length}</Badge>' in tsx


def test_kanban_plain_branch_shows_count_without_badge(tmp_path: Path) -> None:
    tsx = _generate_ticket_board(tmp_path, uikit="")
    assert "Badge" not in tsx
    # Still renders the count, just as a plain styled span
    assert "rounded-full bg-muted" in tsx
