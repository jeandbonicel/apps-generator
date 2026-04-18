"""``calendar`` page type — month/week/day calendar view via schedule-x.

Transforms records into `schedule-x`_ event objects and renders them in
a multi-view calendar (month grid, week, day). Suited for attendance,
leave requests, bookings, deadlines — anything with a primary date and
an optional end date.

Field picking
-------------
1. **Date field** (required) — the event start. Resolution order:

   a. Explicit ``dateField`` in the page config
   b. First field named ``date``/``startDate``/``start``/``when`` with
      a ``date`` or ``datetime`` type
   c. First ``date``/``datetime`` field

   The emitter refuses to generate a meaningful calendar if no date or
   datetime field is available — the page falls back to a read-only
   "No date field configured" notice.

2. **End field** (optional) — event end. Defaults to explicit
   ``endField`` or the next ``date``/``datetime`` field after the start.

3. **Title field** — first ``string`` field (what shows in the event
   pill). Falls back to the record id.

.. _schedule-x: https://schedule-x.dev/
"""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case

from .base import page_target
from .registry import PageContext, PageTypeInfo, get_registry


_DATE_NAME_HINTS = ("date", "startdate", "start", "when")


def _is_temporal(f: dict) -> bool:
    return f.get("type") in ("date", "datetime")


def _pick_date_field(page: dict, fields: list[dict]) -> dict | None:
    explicit = page.get("dateField")
    if explicit:
        for f in fields:
            if f.get("name") == explicit:
                return f
    for f in fields:
        if _is_temporal(f) and f["name"].lower() in _DATE_NAME_HINTS:
            return f
    for f in fields:
        if _is_temporal(f):
            return f
    return None


def _pick_end_field(page: dict, fields: list[dict], start: dict | None) -> dict | None:
    explicit = page.get("endField")
    if explicit:
        for f in fields:
            if f.get("name") == explicit:
                return f
    for f in fields:
        if f is start:
            continue
        if _is_temporal(f):
            return f
    return None


def _pick_title_field(fields: list[dict]) -> dict | None:
    for f in fields:
        if f.get("type", "string") == "string":
            return f
    return None


def _date_js_expr(field: dict, record_var: str) -> str:
    """JS expression that converts a record's value into schedule-x's date format.

    schedule-x expects ``YYYY-MM-DD`` (all-day) or ``YYYY-MM-DD HH:mm``
    (timed). Date strings coming from the API are ISO-ish (``YYYY-MM-DD``
    for dates, ``YYYY-MM-DDTHH:mm:ss[.sss][Z]`` for datetimes).
    """
    fname = camel_case(field["name"])
    if field.get("type") == "datetime":
        # datetime → slice first 16 chars, swap 'T' for a space
        return f'String({record_var}.{fname}).slice(0, 16).replace("T", " ")'
    # date → slice first 10 chars (already YYYY-MM-DD)
    return f"String({record_var}.{fname}).slice(0, 10)"


def emit_calendar(page: dict, ctx: PageContext) -> None:
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])
    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name

    start_field = _pick_date_field(page, fields)
    end_field = _pick_end_field(page, fields, start_field)
    title_field = _pick_title_field(fields)

    # No temporal field at all — emit a graceful placeholder. Better than a
    # broken calendar that crashes at runtime.
    if start_field is None:
        dest.write_text(
            f'import {{ useTranslation }} from "react-i18next";\n'
            f"\n"
            f"export function {component}() {{\n"
            f"  const {{ t }} = useTranslation();\n"
            f"  return (\n"
            f'    <div className="space-y-4">\n'
            f'      <h1 className="text-2xl font-bold tracking-tight">{label}</h1>\n'
            f'      <p className="text-destructive">\n'
            f'        {{t("calendarNeedsDateField")}}\n'
            f"      </p>\n"
            f"    </div>\n"
            f"  );\n"
            f"}}\n"
        )
        return

    start_expr = _date_js_expr(start_field, "item")
    end_expr = _date_js_expr(end_field, "item") if end_field else start_expr
    title_expr = f"String(item.{camel_case(title_field['name'])} ?? item.id)" if title_field else "String(item.id)"

    # ui-kit imports — calendar leans on Card for outer chrome; the grid
    # itself is schedule-x regardless of --uikit.
    if ui:
        ui_import = f'import {{ Card, CardContent, CardHeader, CardTitle }} from "{ui}";\n'
        wrapper_open = (
            f"      <Card>\n"
            f"        <CardHeader>\n"
            f"          <CardTitle>{label} ({{items.length}})</CardTitle>\n"
            f"        </CardHeader>\n"
            f"        <CardContent>"
        )
        wrapper_close = "        </CardContent>\n      </Card>"
    else:
        ui_import = ""
        wrapper_open = (
            f'      <h1 className="text-2xl font-bold tracking-tight mb-4">{label} ({{items.length}})</h1>\n'
            f'      <div className="rounded-lg border p-4">'
        )
        wrapper_close = "      </div>"

    dest.write_text(
        f'import {{ useMemo }} from "react";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ useQuery }} from "@tanstack/react-query";\n'
        f'import {{ ScheduleXCalendar, useCalendarApp }} from "@schedule-x/react";\n'
        f'import {{ createViewMonthGrid, createViewWeek, createViewDay }} from "@schedule-x/calendar";\n'
        f'import "@schedule-x/theme-default/dist/index.css";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ {entity}, PageResponse }} from "{_api_pkg}";\n'
        f"{ui_import}"
        f"\n"
        f"interface CalendarEvent {{\n"
        f"  id: string;\n"
        f"  title: string;\n"
        f"  start: string;\n"
        f"  end: string;\n"
        f"}}\n"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f"\n"
        f"  const {{ data, isLoading, error }} = useQuery<PageResponse<{entity}>>({{  \n"
        f'    queryKey: ["{resource}", "calendar"],\n'
        f'    queryFn: () => api.get<PageResponse<{entity}>>("/{resource}", '
        f'{{ params: {{ page: "0", size: "1000" }} }}),\n'
        f"  }});\n"
        f"\n"
        f"  const items = data?.content ?? [];\n"
        f"\n"
        f"  const events = useMemo<CalendarEvent[]>(() => {{\n"
        f"    const out: CalendarEvent[] = [];\n"
        f"    for (const item of items) {{\n"
        f"      const start = item.{camel_case(start_field['name'])};\n"
        f"      if (start == null) continue;\n"
        f"      out.push({{\n"
        f"        id: String(item.id),\n"
        f"        title: {title_expr},\n"
        f"        start: {start_expr},\n"
        f"        end: {end_expr},\n"
        f"      }});\n"
        f"    }}\n"
        f"    return out;\n"
        f"  }}, [items]);\n"
        f"\n"
        f"  const calendar = useCalendarApp({{\n"
        f"    views: [createViewMonthGrid(), createViewWeek(), createViewDay()],\n"
        f"    events,\n"
        f"  }});\n"
        f"\n"
        f'  if (isLoading) return <p className="text-muted-foreground">{{t("loading")}}</p>;\n'
        f'  if (error) return <p className="text-destructive">'
        f'{{t("failedToLoad")}}: {{(error as Error).message}}</p>;\n'
        f"\n"
        f"  return (\n"
        f'    <div className="space-y-4">\n'
        f"{wrapper_open}\n"
        f"          <ScheduleXCalendar calendarApp={{calendar}} />\n"
        f"{wrapper_close}\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


PAGE_TYPE = PageTypeInfo(
    name="calendar",
    description="Month / week / day calendar view via schedule-x — records transformed to events by a date field.",
    emit=emit_calendar,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
