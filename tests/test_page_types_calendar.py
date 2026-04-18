"""Tests for the ``calendar`` page type — schedule-x month/week/day view."""

from __future__ import annotations

from pathlib import Path

from apps_generator.cli.generators.pages import (
    generate_page_components,
    get_registry,
)


# ── Registration ───────────────────────────────────────────────────────────


def test_calendar_type_is_registered() -> None:
    info = get_registry().get("calendar")
    assert info is not None
    assert info.source == "builtin"
    assert info.required_fields == ["resource"]
    assert info.description


# ── Emitter fixture ────────────────────────────────────────────────────────


def _generate_attendance_calendar(
    tmp_path: Path,
    *,
    uikit: str = "my-ui",
    fields: list[dict] | None = None,
    date_field: str | None = None,
    end_field: str | None = None,
) -> str:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "cal",
        "label": "Attendance Calendar",
        "resource": "attendance",
        "type": "calendar",
        "fields": fields
        if fields is not None
        else [
            {"name": "employeeName", "type": "string"},
            {"name": "date", "type": "date"},
            {"name": "endDate", "type": "date"},
            {"name": "type", "type": "enum", "values": ["vacation", "sick", "remote"]},
        ],
    }
    if date_field:
        page["dateField"] = date_field
    if end_field:
        page["endField"] = end_field
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name=uikit,
        api_client_name="my-api",
    )
    return (project_root / "src" / "routes" / "CalPage.tsx").read_text()


# ── Date-field resolution ──────────────────────────────────────────────────


def test_calendar_prefers_field_named_date_when_multiple_temporals_exist(tmp_path: Path) -> None:
    """`date` wins over `endDate` (both are `date`) because of the name hint."""
    tsx = _generate_attendance_calendar(tmp_path)
    # Start uses `date`, end uses `endDate`
    assert "const start = item.date;" in tsx
    assert "start: String(item.date).slice(0, 10)" in tsx
    assert "end: String(item.endDate).slice(0, 10)" in tsx


def test_calendar_explicit_date_field_wins(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(
        tmp_path,
        fields=[
            {"name": "employeeName", "type": "string"},
            {"name": "checkIn", "type": "datetime"},
            {"name": "checkOut", "type": "datetime"},
        ],
        date_field="checkIn",
    )
    assert "const start = item.checkIn;" in tsx
    # datetime → 16-char slice + T→space
    assert 'start: String(item.checkIn).slice(0, 16).replace("T", " ")' in tsx


def test_calendar_explicit_end_field_wins(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(
        tmp_path,
        fields=[
            {"name": "employeeName", "type": "string"},
            {"name": "from", "type": "date"},
            {"name": "until", "type": "date"},
            {"name": "auditDate", "type": "date"},
        ],
        date_field="from",
        end_field="until",
    )
    assert "end: String(item.until).slice(0, 10)" in tsx


def test_calendar_end_defaults_to_start_when_only_one_temporal(tmp_path: Path) -> None:
    """Single-date events — end == start so schedule-x renders a 1-cell event."""
    tsx = _generate_attendance_calendar(
        tmp_path,
        fields=[
            {"name": "title", "type": "string"},
            {"name": "date", "type": "date"},
        ],
    )
    # end should mirror start
    assert "start: String(item.date).slice(0, 10)" in tsx
    assert "end: String(item.date).slice(0, 10)" in tsx


def test_calendar_falls_back_to_first_temporal_when_no_name_hint(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(
        tmp_path,
        fields=[
            {"name": "title", "type": "string"},
            {"name": "notifyAt", "type": "datetime"},
        ],
    )
    assert "const start = item.notifyAt;" in tsx


# ── Graceful fallback when no temporal field ───────────────────────────────


def test_calendar_with_no_date_field_emits_placeholder(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(
        tmp_path,
        fields=[
            {"name": "title", "type": "string"},
            {"name": "description", "type": "text"},
        ],
    )
    # No schedule-x wiring — just the "needs a date field" notice
    assert "@schedule-x/react" not in tsx
    assert "ScheduleXCalendar" not in tsx
    assert 't("calendarNeedsDateField")' in tsx


# ── Data fetch + transform ─────────────────────────────────────────────────


def test_calendar_fetches_flat_list_with_large_page_size(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(tmp_path)
    assert "useQuery<PageResponse<Attendance>>" in tsx
    assert 'size: "1000"' in tsx
    assert '"attendance", "calendar"' in tsx


def test_calendar_skips_records_with_null_start(tmp_path: Path) -> None:
    """Schedule-x chokes if an event's start is null — drop the record."""
    tsx = _generate_attendance_calendar(tmp_path)
    assert "if (start == null) continue;" in tsx


def test_calendar_event_title_uses_first_string_field(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(tmp_path)
    assert "title: String(item.employeeName ?? item.id)" in tsx


def test_calendar_event_title_falls_back_to_id_when_no_string(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(
        tmp_path,
        fields=[
            {"name": "date", "type": "date"},
            {"name": "endDate", "type": "date"},
        ],
    )
    assert "title: String(item.id)" in tsx


def test_calendar_events_memoized_so_useCalendarApp_is_stable(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(tmp_path)
    assert "useMemo<CalendarEvent[]>(() => {" in tsx
    assert "}, [items]);" in tsx


# ── schedule-x wiring ──────────────────────────────────────────────────────


def test_calendar_imports_schedule_x(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(tmp_path)
    assert 'from "@schedule-x/react"' in tsx
    assert 'from "@schedule-x/calendar"' in tsx
    assert 'import "@schedule-x/theme-default/dist/index.css"' in tsx
    assert "ScheduleXCalendar" in tsx
    assert "useCalendarApp" in tsx


def test_calendar_registers_month_week_day_views(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(tmp_path)
    assert "createViewMonthGrid()" in tsx
    assert "createViewWeek()" in tsx
    assert "createViewDay()" in tsx


# ── Datetime formatting ────────────────────────────────────────────────────


def test_calendar_datetime_field_slices_and_replaces_T(tmp_path: Path) -> None:
    """schedule-x wants ``YYYY-MM-DD HH:mm`` — ISO's ``T`` separator must go."""
    tsx = _generate_attendance_calendar(
        tmp_path,
        fields=[
            {"name": "title", "type": "string"},
            {"name": "startsAt", "type": "datetime"},
        ],
    )
    assert 'String(item.startsAt).slice(0, 16).replace("T", " ")' in tsx


# ── Wrappers ───────────────────────────────────────────────────────────────


def test_calendar_uikit_branch_uses_card_wrapper(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(tmp_path, uikit="my-ui")
    assert 'from "my-ui"' in tsx
    for sym in ["Card", "CardContent", "CardHeader", "CardTitle"]:
        assert sym in tsx


def test_calendar_plain_branch_uses_bordered_div(tmp_path: Path) -> None:
    tsx = _generate_attendance_calendar(tmp_path, uikit="")
    assert "Card" not in tsx
    assert '<div className="rounded-lg border p-4">' in tsx
    assert "Attendance Calendar ({items.length})" in tsx
