"""``grid`` page type — card-grid view of a resource collection.

Same data shape as ``list`` (paginated, null-safe) but rendered as a
responsive grid of Cards instead of a Table. Picks the first string field
as the card title and the second as the description; remaining fields
become a compact label/value list inside the card body. Enum and boolean
fields render as Badges for visual scanning.
"""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case, title_case

from .base import normalize_row_link, page_target
from .registry import PageContext, PageTypeInfo, get_registry


def _pick_title_and_description(fields: list[dict]) -> tuple[dict | None, dict | None, list[dict]]:
    """Pick which fields become CardTitle / CardDescription / body rows.

    Heuristic: first ``string`` field is the title, second is the description.
    Everything else (plus non-string fields) goes into the card body.
    """
    string_fields = [f for f in fields if f.get("type", "string") == "string"]
    title = string_fields[0] if string_fields else None
    description = string_fields[1] if len(string_fields) >= 2 else None
    chosen = {id(title), id(description)} - {id(None)}
    body = [f for f in fields if id(f) not in chosen]
    return title, description, body


def _render_body_value(field: dict, ui: bool) -> str:
    """JSX expression for a single body field's value, type-aware and null-safe."""
    fname = camel_case(field["name"])
    ft = field.get("type", "string")

    if ft == "boolean":
        if ui:
            return (
                f"p.{fname} == null ? (\n"
                f'                    <span className="text-muted-foreground">—</span>\n'
                f"                  ) : p.{fname} ? (\n"
                f'                    <Badge variant="default">{{t("yes")}}</Badge>\n'
                f"                  ) : (\n"
                f'                    <Badge variant="outline">{{t("no")}}</Badge>\n'
                f"                  )"
            )
        return f'p.{fname} == null ? "—" : p.{fname} ? t("yes") : t("no")'

    if ft == "decimal":
        return f'p.{fname} != null ? `$${{p.{fname}.toFixed(2)}}` : "—"'

    if ft in ("date", "datetime"):
        return f'p.{fname} ? new Date(p.{fname}).toLocaleDateString() : "—"'

    if ft == "enum" and ui:
        return (
            f"p.{fname} == null ? (\n"
            f'                    <span className="text-muted-foreground">—</span>\n'
            f"                  ) : (\n"
            f'                    <Badge variant="secondary">{{String(p.{fname})}}</Badge>\n'
            f"                  )"
        )

    return f'p.{fname} ?? "—"'


def emit_grid(page: dict, ctx: PageContext) -> None:
    """Generate a grid page — responsive card-grid for a resource collection."""
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])
    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name
    row_link = normalize_row_link(page.get("rowLink"))

    # Same ``rowLink`` semantics as ``list_type``: opt-in click-through to
    # ``{rowLink}?id={card.id}`` via the MFE router. Cards get a hover state
    # and a pointer cursor so they read as affordances.
    click_attrs = f" onClick={{() => navigateTo(`{row_link}?id=${{p.id}}`)}}" if row_link else ""
    click_class = " cursor-pointer hover:shadow-md transition-shadow" if row_link else ""

    title_field, description_field, body_fields = _pick_title_and_description(fields)

    # ui-kit imports
    if ui:
        ui_import = (
            f'import {{ Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Badge }} from "{ui}";\n'
        )
    else:
        ui_import = ""

    # Build the card JSX
    if title_field:
        title_fname = camel_case(title_field["name"])
        title_expr = f"{{p.{title_fname} ?? p.id}}"
    else:
        title_expr = "{p.id}"

    if description_field:
        desc_fname = camel_case(description_field["name"])
        description_jsx = (
            "              <CardDescription>\n"
            f"                {{p.{desc_fname} ?? null}}\n"
            "              </CardDescription>\n"
            if ui
            else f'              <p className="text-sm text-muted-foreground">{{p.{desc_fname} ?? null}}</p>\n'
        )
    else:
        description_jsx = ""

    # Body rows — one entry per remaining field
    body_rows: list[str] = []
    for f in body_fields:
        flabel = title_case(f["name"])
        value_expr = _render_body_value(f, bool(ui))
        body_rows.append(
            f'                <div className="flex items-start justify-between gap-2 text-sm">\n'
            f'                  <dt className="text-muted-foreground">{flabel}</dt>\n'
            f"                  <dd>\n"
            f"                    {{{value_expr}}}\n"
            f"                  </dd>\n"
            f"                </div>"
        )
    body_rows_str = "\n".join(body_rows)

    if ui:
        card_class_attr = f' className="{click_class.strip()}"' if click_class else ""
        card_block = (
            f"            <Card key={{p.id}}{card_class_attr}{click_attrs}>\n"
            f"              <CardHeader>\n"
            f"                <CardTitle>{title_expr}</CardTitle>\n"
            f"{description_jsx}"
            f"              </CardHeader>\n"
            + (
                f"              <CardContent>\n"
                f'                <dl className="space-y-2">\n'
                f"{body_rows_str}\n"
                f"                </dl>\n"
                f"              </CardContent>\n"
                if body_rows
                else ""
            )
            + "            </Card>"
        )
        empty_state = (
            '          <p className="col-span-full text-center text-muted-foreground py-8">{t("noDataFound")}</p>'
        )
        btn_prev = (
            '<Button variant="outline" size="sm" onClick={() => setPage(p => p - 1)} '
            'disabled={page === 0}>{t("previous")}</Button>'
        )
        btn_next = (
            '<Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} '
            'disabled={page >= totalPages - 1}>{t("next")}</Button>'
        )
    else:
        # Plain fallback — click attrs merge into the existing div's class list.
        div_classes = "rounded-lg border bg-card p-4 space-y-2" + click_class
        card_block = (
            f'            <div key={{p.id}} className="{div_classes}"{click_attrs}>\n'
            f'              <h3 className="text-lg font-semibold">{title_expr}</h3>\n'
            f"{description_jsx}"
            + (
                f'              <dl className="space-y-1 pt-2 border-t">\n{body_rows_str}\n              </dl>\n'
                if body_rows
                else ""
            )
            + "            </div>"
        )
        empty_state = (
            '          <p className="col-span-full text-center text-muted-foreground py-8">{t("noDataFound")}</p>'
        )
        btn_prev = (
            '<button className="px-3 py-1 border rounded text-sm disabled:opacity-50" '
            'onClick={() => setPage(p => p - 1)} disabled={page === 0}>{t("previous")}</button>'
        )
        btn_next = (
            '<button className="px-3 py-1 border rounded text-sm disabled:opacity-50" '
            'onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}>{t("next")}</button>'
        )

    # navigateTo comes from the MFE router; only pull it in when rowLink is set
    # so grids without navigation keep their existing import list unchanged.
    nav_import = 'import { navigateTo } from "../router";\n' if row_link else ""

    dest.write_text(
        f'import {{ useState }} from "react";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ useQuery }} from "@tanstack/react-query";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ {entity}, PageResponse }} from "{_api_pkg}";\n'
        f"{nav_import}"
        f"{ui_import}"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f"  const [page, setPage] = useState(0);\n"
        f"\n"
        f"  const {{ data, isLoading, error }} = useQuery<PageResponse<{entity}>>({{  \n"
        f'    queryKey: ["{resource}", "grid", page],\n'
        f'    queryFn: () => api.get<PageResponse<{entity}>>("/{resource}", '
        f'{{ params: {{ page: String(page), size: "20" }} }}),\n'
        f"  }});\n"
        f"\n"
        f'  if (isLoading) return <p className="text-muted-foreground">{{t("loading")}}</p>;\n'
        f'  if (error) return <p className="text-destructive">'
        f'{{t("failedToLoad")}}: {{(error as Error).message}}</p>;\n'
        f"\n"
        f"  const items = data?.content ?? [];\n"
        f"  const totalPages = data?.totalPages ?? 0;\n"
        f"\n"
        f"  return (\n"
        f'    <div className="space-y-4">\n'
        f'      <div className="flex items-center justify-between">\n'
        f'        <h1 className="text-2xl font-bold tracking-tight">'
        f"{label} ({{data?.totalElements ?? 0}})</h1>\n"
        f"      </div>\n"
        f'      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">\n'
        f"          {{items.map((p) => (\n"
        f"{card_block}\n"
        f"          ))}}\n"
        f"          {{items.length === 0 && (\n"
        f"{empty_state}\n"
        f"          )}}\n"
        f"      </div>\n"
        f'      <div className="flex items-center justify-center gap-2" '
        f'style={{{{ paddingTop: "1.5rem" }}}}>\n'
        f"        {btn_prev}\n"
        f'        <span className="text-sm text-muted-foreground">'
        f"Page {{page + 1}} of {{totalPages}}</span>\n"
        f"        {btn_next}\n"
        f"      </div>\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


PAGE_TYPE = PageTypeInfo(
    name="grid",
    description="Responsive card-grid view for a resource collection.",
    emit=emit_grid,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
