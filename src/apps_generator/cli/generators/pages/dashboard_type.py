"""``dashboard`` page type — stat cards + bar chart + recent items table."""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case, title_case

from .base import page_target
from .registry import PageContext, PageTypeInfo, get_registry


def emit_dashboard(page: dict, ctx: PageContext) -> None:
    """Generate a dashboard page with stat cards + bar chart + recent items table."""
    dest, component, _label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])
    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name

    # Pick a numeric field for the chart and a string field for grouping
    chart_field = None
    group_field = None
    for f in fields:
        ft = f.get("type", "string")
        if ft in ("decimal", "integer", "long") and not chart_field:
            chart_field = f
        elif ft == "string" and not group_field:
            group_field = f

    chart_fname = camel_case(chart_field["name"]) if chart_field else None
    chart_label = title_case(chart_field["name"]) if chart_field else None
    group_fname = camel_case(group_field["name"]) if group_field else "id"
    group_label = title_case(group_field["name"]) if group_field else "ID"

    # Imports
    ui_imports = ""
    if ui:
        ui_imports += f'import {{ Card, CardContent, CardHeader, CardTitle, Table, TableHeader, TableBody, TableHead, TableRow, TableCell }} from "{ui}";\n'
        if chart_field:
            ui_imports += (
                f'import {{ ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig }} from "{ui}";\n'
            )
            ui_imports += 'import { Bar, BarChart, XAxis, YAxis, CartesianGrid } from "recharts";\n'

    # Recent items table (first 3 fields)
    display_fields = fields[:3]
    th_tag = "TableHead" if ui else 'th className="px-4 py-2 text-left font-medium text-muted-foreground"'
    td_tag = "TableCell" if ui else 'td className="px-4 py-4"'
    th_close = "TableHead" if ui else "th"
    td_close = "TableCell" if ui else "td"
    headers = "\n".join(f"                <{th_tag}>{title_case(f['name'])}</{th_close}>" for f in display_fields)
    cells = "\n".join(
        f"                <{td_tag}>{{item.{camel_case(f['name'])}}}</{td_close}>" for f in display_fields
    )

    # Chart data code
    chart_data_code = ""
    if chart_field:
        chart_data_code = (
            f"  const chartData = React.useMemo(() => {{\n"
            f"    const groups: Record<string, number> = {{}};\n"
            f"    for (const item of allItems) {{\n"
            f'      const key = String(item.{group_fname} ?? "Other");\n'
            f"      groups[key] = (groups[key] ?? 0) + Number(item.{chart_fname} ?? 0);\n"
            f"    }}\n"
            f"    return Object.entries(groups).map(([label, value]) => ({{ label, value }}));\n"
            f"  }}, [allItems]);\n"
            f"\n"
            f"  const chartConfig: ChartConfig = {{\n"
            f'    value: {{ label: "{chart_label}", color: "hsl(var(--chart-1))" }},\n'
            f"  }};\n"
        )

    # Chart section
    chart_section = ""
    if chart_field and ui:
        chart_section = (
            f"      <Card>\n"
            f"        <CardHeader>\n"
            f"          <CardTitle>{chart_label} by {group_label}</CardTitle>\n"
            f"        </CardHeader>\n"
            f"        <CardContent>\n"
            f'          <ChartContainer config={{chartConfig}} className="h-[300px]">\n'
            f"            <BarChart data={{chartData}}>\n"
            f'              <CartesianGrid strokeDasharray="3 3" />\n'
            f'              <XAxis dataKey="label" />\n'
            f"              <YAxis />\n"
            f"              <ChartTooltip content={{<ChartTooltipContent />}} />\n"
            f'              <Bar dataKey="value" fill="var(--color-value)" radius={{[4, 4, 0, 0]}} />\n'
            f"            </BarChart>\n"
            f"          </ChartContainer>\n"
            f"        </CardContent>\n"
            f"      </Card>\n"
        )

    # Stat card helper
    def stat_card(stat_label: str, value_expr: str) -> str:
        if ui:
            return (
                f"        <Card>\n"
                f'          <CardHeader className="pb-2">\n'
                f'            <CardTitle className="text-sm font-medium text-muted-foreground">{stat_label}</CardTitle>\n'
                f"          </CardHeader>\n"
                f"          <CardContent>\n"
                f'            <p className="text-3xl font-bold">{{{value_expr}}}</p>\n'
                f"          </CardContent>\n"
                f"        </Card>"
            )
        else:
            return (
                f'        <div className="rounded-lg border bg-card p-6">\n'
                f'          <p className="text-sm text-muted-foreground">{stat_label}</p>\n'
                f'          <p className="text-3xl font-bold">{{{value_expr}}}</p>\n'
                f"        </div>"
            )

    # Recent items table wrapper
    if ui:
        table_block = (
            f"      <Card>\n"
            f"        <CardHeader>\n"
            f"          <CardTitle>Recent {title_case(resource)}s</CardTitle>\n"
            f"        </CardHeader>\n"
            f"        <CardContent>\n"
            f"          <Table>\n"
            f"            <TableHeader>\n"
            f"              <TableRow>\n{headers}\n              </TableRow>\n"
            f"            </TableHeader>\n"
            f"            <TableBody>\n"
            f"              {{recentItems.map((item) => (\n"
            f"                <TableRow key={{item.id}}>\n{cells}\n                </TableRow>\n"
            f"              ))}}\n"
            f"            </TableBody>\n"
            f"          </Table>\n"
            f"        </CardContent>\n"
            f"      </Card>"
        )
    else:
        table_block = (
            f'      <div className="rounded-lg border">\n'
            f'        <h3 className="p-4 font-semibold">Recent {title_case(resource)}s</h3>\n'
            f'        <table className="w-full">\n'
            f'          <thead><tr className="border-b">\n{headers}\n          </tr></thead>\n'
            f"          <tbody>{{recentItems.map((item) => (\n"
            f'            <tr key={{item.id}} className="border-b">\n{cells}\n            </tr>\n'
            f"          ))}}</tbody>\n"
            f"        </table>\n"
            f"      </div>"
        )

    dest.write_text(
        f'import React from "react";\n'
        f'import {{ useQuery }} from "@tanstack/react-query";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ {entity}, PageResponse }} from "{_api_pkg}";\n'
        f"{ui_imports}"
        f"\n"
        f"export function {component}() {{\n"
        f"  const api = useApiClient();\n"
        f"\n"
        f"  const {{ data, isLoading, error }} = useQuery<PageResponse<{entity}>>({{  \n"
        f'    queryKey: ["{resource}", "dashboard"],\n'
        f'    queryFn: () => api.get<PageResponse<{entity}>>("/{resource}", {{ params: {{ page: "0", size: "100" }} }}),\n'
        f"  }});\n"
        f"\n"
        f'  if (isLoading) return <p className="text-muted-foreground">Loading dashboard...</p>;\n'
        f'  if (error) return <p className="text-destructive">Failed to load: {{(error as Error).message}}</p>;\n'
        f"\n"
        f"  const allItems = data?.content ?? [];\n"
        f"  const totalCount = data?.totalElements ?? 0;\n"
        f"  const recentItems = allItems.slice(0, 5);\n"
        f"\n"
        f"{chart_data_code}"
        f"  return (\n"
        f'    <div className="space-y-6">\n'
        f'      <div style={{{{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}}}>\n'
        f"{stat_card(f'Total {title_case(resource)}s', 'totalCount')}\n"
        f"{stat_card('Showing', 'allItems.length')}\n"
        f"      </div>\n"
        f"\n"
        f"{chart_section}"
        f"\n"
        f"{table_block}\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


PAGE_TYPE = PageTypeInfo(
    name="dashboard",
    description="Stat cards + bar chart + recent items table for a resource.",
    emit=emit_dashboard,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
