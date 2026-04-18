"""``detail`` page type — read-only view of a single record.

Renders a two-column "definition list" of the resource's field values inside
a Card. The record id is read from the ``?id=...`` query string, since the
generated frontend-app maps paths to components directly without URL params.
"""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case, title_case

from .base import page_target
from .registry import PageContext, PageTypeInfo, get_registry


def _render_value(field: dict, ui: bool) -> str:
    """Return the JSX expression for one field's value, type-aware and null-safe."""
    fname = camel_case(field["name"])
    ft = field.get("type", "string")

    if ft == "boolean":
        if ui:
            return (
                f"data.{fname} == null ? (\n"
                f'                <span className="text-muted-foreground">—</span>\n'
                f"              ) : data.{fname} ? (\n"
                f'                <Badge variant="default">{{t("yes")}}</Badge>\n'
                f"              ) : (\n"
                f'                <Badge variant="outline">{{t("no")}}</Badge>\n'
                f"              )"
            )
        return f'data.{fname} == null ? "—" : data.{fname} ? t("yes") : t("no")'

    if ft == "decimal":
        return f'data.{fname} != null ? `$${{data.{fname}.toFixed(2)}}` : "—"'

    if ft in ("date", "datetime"):
        return f'data.{fname} ? new Date(data.{fname}).toLocaleDateString() : "—"'

    if ft == "enum" and ui:
        # Render enum values as a Badge so statuses stand out visually.
        return (
            f"data.{fname} == null ? (\n"
            f'                <span className="text-muted-foreground">—</span>\n'
            f"              ) : (\n"
            f'                <Badge variant="secondary">{{String(data.{fname})}}</Badge>\n'
            f"              )"
        )

    if ft == "text":
        # Long text wraps and preserves whitespace.
        if ui:
            return (
                f"data.{fname} == null ? (\n"
                f'                <span className="text-muted-foreground">—</span>\n'
                f"              ) : (\n"
                f'                <span className="whitespace-pre-wrap">{{data.{fname}}}</span>\n'
                f"              )"
            )
        return f'data.{fname} ?? "—"'

    # string / integer / long (default)
    return f'data.{fname} ?? "—"'


def emit_detail(page: dict, ctx: PageContext) -> None:
    """Generate a detail page — single record view."""
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])
    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name

    # ui-kit imports
    if ui:
        ui_import = f'import {{ Card, CardContent, CardHeader, CardTitle, Badge, Skeleton }} from "{ui}";\n'
    else:
        ui_import = ""

    # Build one dt/dd pair per field. We put the label in <dt> and the value
    # (already a JSX expression returned by _render_value) in <dd>. Using a
    # definition list keeps the semantics right for screen readers.
    rows: list[str] = []
    for f in fields:
        flabel = title_case(f["name"])
        value_expr = _render_value(f, bool(ui))
        if ui:
            rows.append(
                f'            <div className="space-y-1">\n'
                f'              <dt className="text-sm font-medium text-muted-foreground">{flabel}</dt>\n'
                f"              <dd>\n"
                f"                {{{value_expr}}}\n"
                f"              </dd>\n"
                f"            </div>"
            )
        else:
            rows.append(
                f'            <div className="space-y-1">\n'
                f'              <dt className="text-sm font-medium text-muted-foreground">{flabel}</dt>\n'
                f'              <dd className="text-sm">{{{value_expr}}}</dd>\n'
                f"            </div>"
            )
    rows_str = "\n".join(rows)

    # Loading skeleton — use the ui-kit Skeleton when available, else a plain
    # pulsing placeholder. One skeleton per field keeps the layout stable so
    # the user doesn't see a jarring reflow when data arrives.
    if ui:
        loading_skeletons = "\n".join(
            '            <div className="space-y-1">\n'
            '              <Skeleton className="h-4 w-24" />\n'
            '              <Skeleton className="h-5 w-40" />\n'
            "            </div>"
            for _ in fields
        )
        loading_block = (
            f"      <Card>\n"
            f"        <CardHeader>\n"
            f"          <CardTitle>{label}</CardTitle>\n"
            f"        </CardHeader>\n"
            f"        <CardContent>\n"
            f'          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">\n'
            f"{loading_skeletons}\n"
            f"          </dl>\n"
            f"        </CardContent>\n"
            f"      </Card>"
        )
        content_block = (
            f"      <Card>\n"
            f"        <CardHeader>\n"
            f"          <CardTitle>{label}</CardTitle>\n"
            f"        </CardHeader>\n"
            f"        <CardContent>\n"
            f'          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">\n'
            f"{rows_str}\n"
            f"          </dl>\n"
            f"        </CardContent>\n"
            f"      </Card>"
        )
    else:
        loading_skeletons = "\n".join(
            '            <div className="space-y-1">\n'
            '              <div className="h-4 w-24 animate-pulse bg-muted rounded" />\n'
            '              <div className="h-5 w-40 animate-pulse bg-muted rounded" />\n'
            "            </div>"
            for _ in fields
        )
        loading_block = (
            f'      <h1 className="text-2xl font-bold tracking-tight mb-4">{label}</h1>\n'
            f'          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">\n'
            f"{loading_skeletons}\n"
            f"          </dl>"
        )
        content_block = (
            f'      <h1 className="text-2xl font-bold tracking-tight mb-4">{label}</h1>\n'
            f'          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">\n'
            f"{rows_str}\n"
            f"          </dl>"
        )

    dest.write_text(
        f'import {{ useQuery }} from "@tanstack/react-query";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ {entity} }} from "{_api_pkg}";\n'
        f"{ui_import}"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f'  const id = new URLSearchParams(window.location.search).get("id");\n'
        f"\n"
        f"  const {{ data, isLoading, error }} = useQuery<{entity}>({{  \n"
        f'    queryKey: ["{resource}", id],\n'
        f"    queryFn: () => api.get<{entity}>(`/{resource}/${{id}}`),\n"
        f"    enabled: !!id,\n"
        f"  }});\n"
        f"\n"
        f'  if (!id) return <p className="text-destructive">{{t("missingId")}}</p>;\n'
        f'  if (error) return <p className="text-destructive">{{t("failedToLoad")}}: {{(error as Error).message}}</p>;\n'
        f"\n"
        f"  if (isLoading || !data) {{\n"
        f"    return (\n"
        f'      <div className="space-y-4">\n'
        f"{loading_block}\n"
        f"      </div>\n"
        f"    );\n"
        f"  }}\n"
        f"\n"
        f"  return (\n"
        f'    <div className="space-y-4">\n'
        f"{content_block}\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


PAGE_TYPE = PageTypeInfo(
    name="detail",
    description="Read-only single-record view — field values in a definition list.",
    emit=emit_detail,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
