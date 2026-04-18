"""``kanban`` page type — drag-and-drop board grouped by a status enum.

Renders records in columns keyed by an enum field's values. Cards are
draggable between columns via `@dnd-kit/core`_ and `@dnd-kit/sortable`_;
dropping a card into a different column PATCHes the underlying record
with the new status value and optimistically moves the card so the UI
never feels sluggish while the mutation is in flight.

Picking the status field:

1. If the page config sets ``statusField`` explicitly, use that.
2. Otherwise, use the first ``enum`` field with a ``values`` array.
3. If neither is available, the emitter still generates a page but the
   board has a single "Backlog" column containing every record — a
   graceful fallback rather than a hard error.

.. _@dnd-kit/core: https://dndkit.com/
.. _@dnd-kit/sortable: https://github.com/clauderic/dnd-kit
"""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case, title_case

from .base import page_target
from .registry import PageContext, PageTypeInfo, get_registry


_STATUS_NAME_HINTS = ("status", "state", "stage", "phase")


def _pick_status_field(page: dict, fields: list[dict]) -> dict | None:
    """Return the field whose enum values define the board's columns.

    Resolution order:

    1. Explicit ``statusField`` in the page config wins.
    2. Otherwise prefer an enum field whose name matches a status-y hint
       (``status`` / ``state`` / ``stage`` / ``phase``) — that's the convention
       behind nearly every kanban board.
    3. Fall back to the first enum field with a ``values`` array.
    """
    explicit = page.get("statusField")
    if explicit:
        for f in fields:
            if f.get("name") == explicit:
                return f
    enum_fields = [f for f in fields if f.get("type") == "enum" and f.get("values")]
    for f in enum_fields:
        if f["name"].lower() in _STATUS_NAME_HINTS:
            return f
    return enum_fields[0] if enum_fields else None


def _pick_title_field(fields: list[dict], exclude: dict | None) -> dict | None:
    """First string field, skipping the one chosen as the status field."""
    for f in fields:
        if f is exclude:
            continue
        if f.get("type", "string") == "string":
            return f
    return None


def emit_kanban(page: dict, ctx: PageContext) -> None:
    """Generate a kanban page — DndContext + SortableContext per status column."""
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])
    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name

    status_field = _pick_status_field(page, fields)
    title_field = _pick_title_field(fields, status_field)

    # Column source-of-truth: the enum's values, or a single "Backlog" fallback.
    if status_field and status_field.get("values"):
        status_fname = camel_case(status_field["name"])
        column_keys = status_field["values"]
    else:
        status_fname = ""
        column_keys = ["Backlog"]
    columns_ts = "[" + ", ".join(f'"{v}"' for v in column_keys) + "]"

    title_fname = camel_case(title_field["name"]) if title_field else "id"

    # Descriptor fields shown under the card title — all fields except title +
    # status, rendered compactly. Keeps cards scannable.
    used_names: set[str] = set()
    if title_field:
        used_names.add(title_field["name"])
    if status_field:
        used_names.add(status_field["name"])
    body_fields = [f for f in fields if f["name"] not in used_names]

    body_rows: list[str] = []
    for f in body_fields:
        flabel = title_case(f["name"])
        fname = camel_case(f["name"])
        ft = f.get("type", "string")
        if ft == "decimal":
            expr = f'item.{fname} != null ? `$${{item.{fname}.toFixed(2)}}` : "—"'
        elif ft in ("date", "datetime"):
            expr = f'item.{fname} ? new Date(item.{fname}).toLocaleDateString() : "—"'
        elif ft == "boolean":
            expr = f'item.{fname} == null ? "—" : item.{fname} ? t("yes") : t("no")'
        else:
            expr = f'item.{fname} ?? "—"'
        body_rows.append(
            f'          <div className="flex items-center justify-between gap-2 text-xs">\n'
            f'            <span className="text-muted-foreground">{flabel}</span>\n'
            f"            <span>{{{expr}}}</span>\n"
            f"          </div>"
        )
    body_rows_str = "\n".join(body_rows)

    # ui-kit imports — kanban leans on Card + Badge for column headers and cards.
    if ui:
        ui_import = f'import {{ Card, CardContent, CardHeader, CardTitle, Badge }} from "{ui}";\n'
    else:
        ui_import = ""

    # Column header — with ui-kit it's a CardHeader + count badge; plain
    # fallback uses a styled <h3>. Either way, the column label is the enum
    # value title-cased.
    if ui:
        column_header = (
            '          <div className="flex items-center justify-between mb-3">\n'
            '            <h3 className="font-semibold text-sm">{statusLabel(status)}</h3>\n'
            '            <Badge variant="secondary">{items.length}</Badge>\n'
            "          </div>"
        )
        card_wrapper_open = "<Card>"
        card_wrapper_close = "</Card>"
    else:
        column_header = (
            '          <div className="flex items-center justify-between mb-3">\n'
            '            <h3 className="font-semibold text-sm">{statusLabel(status)}</h3>\n'
            '            <span className="text-xs text-muted-foreground rounded-full bg-muted px-2 py-0.5">{items.length}</span>\n'
            "          </div>"
        )
        card_wrapper_open = '<div className="rounded-lg border bg-card p-4">'
        card_wrapper_close = "</div>"

    dest.write_text(
        f'import {{ useMemo, useState, useEffect }} from "react";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ useQuery, useMutation, useQueryClient }} from "@tanstack/react-query";\n'
        f"import {{\n"
        f"  DndContext,\n"
        f"  type DragEndEvent,\n"
        f"  PointerSensor,\n"
        f"  useSensor,\n"
        f"  useSensors,\n"
        f'}} from "@dnd-kit/core";\n'
        f"import {{\n"
        f"  SortableContext,\n"
        f"  verticalListSortingStrategy,\n"
        f"  useSortable,\n"
        f'}} from "@dnd-kit/sortable";\n'
        f'import {{ CSS }} from "@dnd-kit/utilities";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ {entity}, PageResponse, Update{entity}Request }} from "{_api_pkg}";\n'
        f"{ui_import}"
        f"\n"
        f"const STATUSES = {columns_ts} as const;\n"
        f"type Status = (typeof STATUSES)[number];\n"
        f"\n"
        f"/** Turn an enum value into a human-readable column header. */\n"
        f"function statusLabel(s: Status): string {{\n"
        f"  return String(s)\n"
        f'    .replace(/([A-Z])/g, " $1")\n'
        f"    .replace(/^./, (c) => c.toUpperCase())\n"
        f"    .trim();\n"
        f"}}\n"
        f"\n"
        f"interface CardProps {{ item: {entity}; t: (key: string) => string; }}\n"
        f"\n"
        f"/** Sortable card — what the user actually drags. */\n"
        f"function DraggableCard({{ item, t }}: CardProps) {{\n"
        f"  const {{ attributes, listeners, setNodeRef, transform, transition, isDragging }} =\n"
        f"    useSortable({{ id: String(item.id) }});\n"
        f"  const style = {{\n"
        f"    transform: CSS.Transform.toString(transform),\n"
        f"    transition,\n"
        f"    opacity: isDragging ? 0.5 : 1,\n"
        f"  }};\n"
        f"  return (\n"
        f"    <div ref={{setNodeRef}} style={{style}} {{...attributes}} {{...listeners}}>\n"
        f"      {card_wrapper_open}\n"
        f'        <div className="p-3 space-y-2 cursor-grab active:cursor-grabbing">\n'
        f'          <div className="font-medium text-sm">{{String(item.{title_fname} ?? item.id)}}</div>\n'
        + (f"{body_rows_str}\n" if body_rows_str else "")
        + f"        </div>\n"
        f"      {card_wrapper_close}\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f"  const queryClient = useQueryClient();\n"
        f"\n"
        f"  const {{ data, isLoading, error }} = useQuery<PageResponse<{entity}>>({{  \n"
        f'    queryKey: ["{resource}", "kanban"],\n'
        f'    queryFn: () => api.get<PageResponse<{entity}>>("/{resource}", '
        f'{{ params: {{ page: "0", size: "1000" }} }}),\n'
        f"  }});\n"
        f"\n"
        f"  // Local mirror of the server list so we can move cards optimistically\n"
        f"  // and roll back on failure. Kept in sync with fetches via useEffect.\n"
        f"  const [local, setLocal] = useState<{entity}[]>([]);\n"
        f"  useEffect(() => {{\n"
        f"    if (data) setLocal(data.content ?? []);\n"
        f"  }}, [data]);\n"
        f"\n"
        f"  const grouped = useMemo(() => {{\n"
        f"    const by: Record<string, {entity}[]> = {{}};\n"
        f"    for (const s of STATUSES) by[s] = [];\n"
        f"    for (const item of local) {{\n"
        + (
            f"      const s = String((item as any).{status_fname} ?? STATUSES[0]) as Status;\n"
            if status_fname
            else "      const s = STATUSES[0];\n"
        )
        + "      (by[s] ?? (by[STATUSES[0]])).push(item);\n"
        "    }\n"
        "    return by;\n"
        "  }, [local]);\n"
        "\n"
        "  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));\n"
        "\n"
        "  const mutation = useMutation({\n"
        "    mutationFn: ({ id, status }: { id: string; status: Status }) =>\n"
        + (
            f"      api.patch<{entity}>(`/{resource}/${{id}}`, {{ {status_fname}: status }} as Update{entity}Request),\n"
            if status_fname
            else f"      api.patch<{entity}>(`/{resource}/${{id}}`, {{}} as Update{entity}Request),\n"
        )
        + f'    onSettled: () => queryClient.invalidateQueries({{ queryKey: ["{resource}"] }}),\n'
        f"  }});\n"
        f"\n"
        f"  const handleDragEnd = (e: DragEndEvent) => {{\n"
        f"    const {{ active, over }} = e;\n"
        f"    if (!over) return;\n"
        f"    const target = String(over.id) as Status;\n"
        f"    if (!STATUSES.includes(target)) return;\n"
        f"    const id = String(active.id);\n"
        f"    setLocal((prev) =>\n"
        + (
            f"      prev.map((it) => (String(it.id) === id ? {{ ...it, {status_fname}: target }} : it))\n"
            if status_fname
            else "      prev.map((it) => (String(it.id) === id ? it : it))\n"
        )
        + f"    );\n"
        f"    mutation.mutate({{ id, status: target }});\n"
        f"  }};\n"
        f"\n"
        f'  if (isLoading) return <p className="text-muted-foreground">{{t("loading")}}</p>;\n'
        f'  if (error) return <p className="text-destructive">'
        f'{{t("failedToLoad")}}: {{(error as Error).message}}</p>;\n'
        f"\n"
        f"  return (\n"
        f'    <div className="space-y-4">\n'
        f'      <h1 className="text-2xl font-bold tracking-tight">{label}</h1>\n'
        f"      <DndContext sensors={{sensors}} onDragEnd={{handleDragEnd}}>\n"
        f'        <div className="grid gap-4" style={{{{ gridTemplateColumns: `repeat(${{STATUSES.length}}, minmax(240px, 1fr))` }}}}>\n'
        f"          {{STATUSES.map((status) => {{\n"
        f"            const items = grouped[status] ?? [];\n"
        f"            return (\n"
        f'              <div key={{status}} id={{status}} data-status={{status}} className="rounded-lg bg-muted/40 p-3">\n'
        f"{column_header}\n"
        f"                <SortableContext\n"
        f"                  id={{status}}\n"
        f"                  items={{items.map((i) => String(i.id))}}\n"
        f"                  strategy={{verticalListSortingStrategy}}\n"
        f"                >\n"
        f'                  <div className="space-y-2 min-h-[4rem]">\n'
        f"                    {{items.map((item) => (\n"
        f"                      <DraggableCard key={{String(item.id)}} item={{item}} t={{t}} />\n"
        f"                    ))}}\n"
        f"                  </div>\n"
        f"                </SortableContext>\n"
        f"              </div>\n"
        f"            );\n"
        f"          }})}}\n"
        f"        </div>\n"
        f"      </DndContext>\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


PAGE_TYPE = PageTypeInfo(
    name="kanban",
    description="Drag-and-drop board grouped by a status enum — columns = enum values, drop PATCHes the record's status field.",
    emit=emit_kanban,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
