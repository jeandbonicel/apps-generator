"""``list`` page type — paginated table for a resource collection."""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case, title_case

from .base import page_target
from .registry import PageContext, PageTypeInfo, get_registry


def emit_list(page: dict, ctx: PageContext) -> None:
    """Generate a list page with useApiClient + useQuery table."""
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])
    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name

    # ui-kit imports
    if ui:
        ui_import = (
            f"import {{ Button, Card, CardContent, CardHeader, CardTitle, "
            f'Table, TableHeader, TableBody, TableHead, TableRow, TableCell }} from "{ui}";\n'
        )
    else:
        ui_import = ""

    # Table headers
    if ui:
        headers = "\n".join(f"              <TableHead>{title_case(f['name'])}</TableHead>" for f in fields)
    else:
        headers = "\n".join(f'              <th className="p-2 text-left">{title_case(f["name"])}</th>' for f in fields)

    # Table cells
    cols = []
    for f in fields:
        fname = camel_case(f["name"])
        ft = f.get("type", "string")
        tag = "TableCell" if ui else 'td className="p-2"'
        close_tag = "TableCell" if ui else "td"
        if ft == "decimal":
            cols.append(f'              <{tag}>{{p.{fname} != null ? `${{p.{fname}.toFixed(2)}}` : "—"}}</{close_tag}>')
        elif ft == "boolean":
            cols.append(f'              <{tag}>{{p.{fname} ? "Yes" : "No"}}</{close_tag}>')
        elif ft in ("date", "datetime"):
            cols.append(
                f'              <{tag}>{{p.{fname} ? new Date(p.{fname}).toLocaleDateString() : "—"}}</{close_tag}>'
            )
        else:
            cols.append(f'              <{tag}>{{p.{fname} ?? "—"}}</{close_tag}>')
    cells = "\n".join(cols)

    # Button element
    btn_prev = (
        '<Button variant="outline" size="sm" onClick={() => setPage(p => p - 1)} disabled={page === 0}>{t("previous")}</Button>'
        if ui
        else '<button className="px-3 py-1 border rounded text-sm disabled:opacity-50" onClick={() => setPage(p => p - 1)} disabled={page === 0}>{t("previous")}</button>'
    )
    btn_next = (
        '<Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}>{t("next")}</Button>'
        if ui
        else '<button className="px-3 py-1 border rounded text-sm disabled:opacity-50" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}>{t("next")}</button>'
    )

    # Table wrapper
    if ui:
        table_open = f"      <Card>\n        <CardHeader>\n          <CardTitle>{label} ({{data?.totalElements ?? 0}})</CardTitle>\n        </CardHeader>\n        <CardContent>\n          <Table>\n            <TableHeader>\n              <TableRow>"
        table_head_close = "              </TableRow>\n            </TableHeader>\n            <TableBody>"
        row_open = "              <TableRow key={p.id}>"
        row_close = "              </TableRow>"
        empty_row = f'              <TableRow><TableCell colSpan={{{len(fields)}}} className="text-center text-muted-foreground py-8">{{t("noDataFound")}}</TableCell></TableRow>'
        table_close = "            </TableBody>\n          </Table>\n        </CardContent>\n      </Card>"
    else:
        table_open = (
            '      <table className="w-full border-collapse">\n        <thead>\n          <tr className="border-b">'
        )
        table_head_close = "          </tr>\n        </thead>\n        <tbody>"
        row_open = '            <tr key={p.id} className="border-b">'
        row_close = "            </tr>"
        empty_row = f'            <tr><td colSpan={{{len(fields)}}} className="p-4 text-center text-muted-foreground">{{t("noDataFound")}}</td></tr>'
        table_close = "        </tbody>\n      </table>"

    dest.write_text(
        f'import {{ useState }} from "react";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ useQuery }} from "@tanstack/react-query";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ {entity}, PageResponse }} from "{_api_pkg}";\n'
        f"{ui_import}"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f"  const [page, setPage] = useState(0);\n"
        f"\n"
        f"  const {{ data, isLoading, error }} = useQuery<PageResponse<{entity}>>({{  \n"
        f'    queryKey: ["{resource}", page],\n'
        f'    queryFn: () => api.get<PageResponse<{entity}>>("/{resource}", {{ params: {{ page: String(page), size: "20" }} }}),\n'
        f"  }});\n"
        f"\n"
        f'  if (isLoading) return <p className="text-muted-foreground">{{t("loading")}}</p>;\n'
        f'  if (error) return <p className="text-destructive">{{t("failedToLoad")}}: {{(error as Error).message}}</p>;\n'
        f"\n"
        f"  const items = data?.content ?? [];\n"
        f"  const totalPages = data?.totalPages ?? 0;\n"
        f"\n"
        f"  return (\n"
        f'    <div className="space-y-4">\n'
        + (
            f"{table_open}\n"
            if ui
            else f'      <div className="flex items-center justify-between">\n'
            f'        <h1 className="text-2xl font-bold tracking-tight">{label} ({{data?.totalElements ?? 0}})</h1>\n'
            f"      </div>\n"
            f"{table_open}\n"
        )
        + f"{headers}\n"
        f"{table_head_close}\n"
        f"          {{items.map((p) => (\n"
        f"{row_open}\n"
        f"{cells}\n"
        f"{row_close}\n"
        f"          ))}}\n"
        f"          {{items.length === 0 && (\n"
        f"{empty_row}\n"
        f"          )}}\n"
        f"{table_close}\n"
        f'      <div className="flex items-center justify-center gap-2" style={{{{ paddingTop: "1.5rem" }}}}>\n'
        f"        {btn_prev}\n"
        f'        <span className="text-sm text-muted-foreground">Page {{page + 1}} of {{totalPages}}</span>\n'
        f"        {btn_next}\n"
        f"      </div>\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


PAGE_TYPE = PageTypeInfo(
    name="list",
    description="Paginated table for a resource collection.",
    emit=emit_list,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
