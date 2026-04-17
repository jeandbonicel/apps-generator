"""Page component generation — parse page configs and generate React components."""

from __future__ import annotations

import json
from pathlib import Path

from apps_generator.utils.console import console
from apps_generator.utils.naming import title_case, pascal_case, camel_case


def parse_pages(pages_str: str) -> list[dict]:
    """Parse pages JSON string into a list of page configs."""
    if not pages_str or pages_str == "[]":
        return []
    try:
        pages = json.loads(pages_str)
        if isinstance(pages, list):
            return pages
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def find_project_root(output_dir: Path, project_name: str) -> Path | None:
    """Find the generated project root directory."""
    # output_dir/projectName/src/pages.ts
    candidate = output_dir / project_name
    if (candidate / "src" / "pages.ts").exists():
        return candidate
    # output_dir/src/pages.ts
    if (output_dir / "src" / "pages.ts").exists():
        return output_dir
    return None


def _detect_lookup(field: dict, all_resources: list[str]) -> dict | None:
    """Auto-detect if a field should be a lookup to another resource.

    Matches patterns like 'dogName' -> resource 'dog', 'categoryId' -> resource 'category'.
    Returns lookup config dict or None.
    """
    fname = field["name"]
    for res in all_resources:
        res_lower = res.lower()
        fname_lower = fname.lower()
        # Match dogName, dogId, dog_name, dog_id patterns
        if fname_lower in (f"{res_lower}name", f"{res_lower}id", f"{res_lower}_name", f"{res_lower}_id"):
            value_field = "id" if fname_lower.endswith("id") else "name"
            return {"resource": res, "valueField": value_field, "labelField": "name"}
    return None


def generate_page_components(
    project_root: Path,
    pages: list[dict],
    project_name: str,
    uikit_name: str = "",
    api_client_name: str = "",
    all_resources: list[str] | None = None,
) -> None:
    """Generate individual page component files and update pages.ts registry.

    Pages with ``resource`` + ``type`` fields generate data-fetching components
    using useApiClient() and TanStack Query (list page with table, form page
    with inputs). Pages without these fields stay as simple placeholders.

    When ``uikit_name`` is provided, generated pages import shadcn components
    (Button, Input, Table, Card, etc.) from the ui-kit package.
    """
    routes_dir = project_root / "src" / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)

    imports: list[str] = ['import type { ComponentType } from "react";']
    imports.append('import { HomePage } from "./routes/HomePage";')
    registry_entries: list[str] = ["  default: HomePage,"]

    for page in pages:
        path = page.get("path", "")
        label = page.get("label", title_case(path))
        component_name = pascal_case(path.replace("/", "-")) + "Page"
        resource = page.get("resource")
        page_type = page.get("type")
        fields = page.get("fields", [])

        page_file = routes_dir / f"{component_name}.tsx"
        if not page_file.exists():
            if resource and page_type == "list":
                write_list_page(page_file, component_name, label, resource, fields, uikit_name, api_client_name)
            elif resource and page_type == "form":
                # Auto-detect lookups for form fields
                if all_resources:
                    other_resources = [r for r in all_resources if r != resource]
                    for f in fields:
                        if "lookup" not in f:
                            detected = _detect_lookup(f, other_resources)
                            if detected:
                                f["lookup"] = detected
                write_form_page(page_file, component_name, label, resource, fields, uikit_name, api_client_name)
            elif resource and page_type == "dashboard":
                write_dashboard_page(page_file, component_name, label, resource, fields, uikit_name, api_client_name)
            else:
                page_file.write_text(
                    f"export function {component_name}() {{\n"
                    f"  return (\n"
                    f'    <div className="p-6">\n'
                    f'      <h1 className="text-2xl font-bold mb-4">{label}</h1>\n'
                    f'      <p className="text-gray-600">This is the {label} page of {title_case(project_name)}.</p>\n'
                    f"    </div>\n"
                    f"  );\n"
                    f"}}\n"
                )
            console.print(f"  Created page: src/routes/{component_name}.tsx")

        imports.append(f'import {{ {component_name} }} from "./routes/{component_name}";')
        registry_entries.append(f'  "{path}": {component_name},')

    # Write updated pages.ts
    pages_ts = project_root / "src" / "pages.ts"
    content = "\n".join(imports)
    content += "\n\nexport const pages: Record<string, ComponentType> = {\n"
    content += "\n".join(registry_entries)
    content += "\n};\n"
    pages_ts.write_text(content)
    console.print(f"  Updated: src/pages.ts ({len(pages)} pages registered)")


def write_list_page(
    dest: Path,
    component: str,
    label: str,
    resource: str,
    fields: list[dict],
    uikit_name: str = "",
    api_client_name: str = "",
) -> None:
    """Generate a list page with useApiClient + useQuery table."""
    entity = pascal_case(resource)
    _api_pkg = api_client_name or "my-api-client"
    ui = uikit_name  # shorthand

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


def write_form_page(
    dest: Path,
    component: str,
    label: str,
    resource: str,
    fields: list[dict],
    uikit_name: str = "",
    api_client_name: str = "",
) -> None:
    """Generate a form page with useApiClient + useMutation."""
    entity = pascal_case(resource)
    _api_pkg = api_client_name or "my-api-client"
    ui = uikit_name

    # ui-kit imports
    if ui:
        ui_import = f'import {{ Button, Input, Label, Textarea, Checkbox, Card, CardContent, CardHeader, CardTitle, Alert, AlertDescription }} from "{ui}";\n'
    else:
        ui_import = ""

    # Build form state defaults
    defaults = {}
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        if ft in ("integer", "long", "decimal"):
            defaults[fname] = '""'
        elif ft == "boolean":
            defaults[fname] = "false"
        else:
            defaults[fname] = '""'

    state_init = ", ".join(f"{k}: {v}" for k, v in defaults.items())

    # Collect lookup resources (need separate useQuery for each)
    lookups: list[dict] = []
    for f in fields:
        if "lookup" in f:
            lk = f["lookup"]
            if lk not in lookups:
                lookups.append(lk)

    # Build form inputs
    inputs = []
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        flabel = title_case(f["name"])
        required = f.get("required", False)
        req_star = " *" if required else ""
        lookup = f.get("lookup")

        if ui:
            # Lookup field -> Select dropdown
            if lookup:
                lk_res = lookup["resource"]
                lk_var = camel_case(lk_res) + "Options"
                lk_val = lookup.get("valueField", "name")
                lk_label = lookup.get("labelField", "name")
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f"          {{{lk_var}.length === 0 ? (\n"
                    f'            <p className="text-sm text-muted-foreground">No {title_case(lk_res)}s found. <a href="../{lk_res}s/new" className="underline text-primary">Create one first</a>.</p>\n'
                    f"          ) : (\n"
                    f'            <select id="{fname}" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"\n'
                    f"              value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}>\n"
                    f'              <option value="">Select {flabel}...</option>\n'
                    f"              {{{lk_var}.map((opt: any) => <option key={{opt.{lk_val}}} value={{opt.{lk_val}}}>{{opt.{lk_label}}}</option>)}}\n"
                    f"            </select>\n"
                    f"          )}}\n"
                    f"        </div>"
                )
                continue

            # shadcn-style with Label + Input/Textarea/Checkbox
            if ft == "text":
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f'          <Textarea id="{fname}" rows={{3}}\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                    f"        </div>"
                )
            elif ft == "boolean":
                inputs.append(
                    f'        <div className="flex items-center space-x-2">\n'
                    f'          <Checkbox id="{fname}" checked={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: (e.target as HTMLInputElement).checked}}))}}/>\n'
                    f'          <Label htmlFor="{fname}">{flabel}</Label>\n'
                    f"        </div>"
                )
            elif ft == "date":
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f'          <Input id="{fname}" type="date"\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                    f"        </div>"
                )
            elif ft == "datetime":
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f'          <Input id="{fname}" type="datetime-local"\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                    f"        </div>"
                )
            elif ft in ("integer", "long"):
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f'          <Input id="{fname}" type="number"\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                    f"        </div>"
                )
            elif ft == "decimal":
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f'          <Input id="{fname}" type="number" step="0.01"\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                    f"        </div>"
                )
            else:
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f'          <Input id="{fname}" type="text"\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                    f"        </div>"
                )
        else:
            # Plain HTML fallback — lookup
            if lookup:
                lk_res = lookup["resource"]
                lk_var = camel_case(lk_res) + "Options"
                lk_val = lookup.get("valueField", "name")
                lk_label = lookup.get("labelField", "name")
                inputs.append(
                    f"        <div>\n"
                    f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}{req_star}</label>\n'
                    f"          {{{lk_var}.length === 0 ? (\n"
                    f'            <p className="mt-1 text-sm text-muted-foreground">No {title_case(lk_res)}s found. <a href="../{lk_res}s/new" className="underline">Create one first</a>.</p>\n'
                    f"          ) : (\n"
                    f'            <select id="{fname}" className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"\n'
                    f"              value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}>\n"
                    f'              <option value="">Select {flabel}...</option>\n'
                    f"              {{{lk_var}.map((opt: any) => <option key={{opt.{lk_val}}} value={{opt.{lk_val}}}>{{opt.{lk_label}}}</option>)}}\n"
                    f"            </select>\n"
                    f"          )}}\n"
                    f"        </div>"
                )
                continue
            if ft == "text":
                inputs.append(
                    f"        <div>\n"
                    f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}{req_star}</label>\n'
                    f'          <textarea id="{fname}" className="mt-1 flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm" rows={{3}}\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                    f"        </div>"
                )
            elif ft == "boolean":
                inputs.append(
                    f'        <div className="flex items-center space-x-2">\n'
                    f'          <input id="{fname}" type="checkbox" className="h-4 w-4 rounded border-primary" checked={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.checked}}))}}/>\n'
                    f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}</label>\n'
                    f"        </div>"
                )
            else:
                input_type = (
                    "number"
                    if ft in ("integer", "long", "decimal")
                    else "date"
                    if ft == "date"
                    else "datetime-local"
                    if ft == "datetime"
                    else "text"
                )
                step = ' step="0.01"' if ft == "decimal" else ""
                inputs.append(
                    f"        <div>\n"
                    f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}{req_star}</label>\n'
                    f'          <input id="{fname}" type="{input_type}"{step} className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                    f"        </div>"
                )

    inputs_str = "\n".join(inputs)

    # Build submission body (cast number fields)
    body_fields = []
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        if ft in ("integer", "long", "decimal"):
            body_fields.append(f"        {fname}: form.{fname} ? Number(form.{fname}) : undefined,")
        elif ft == "boolean":
            body_fields.append(f"        {fname}: form.{fname},")
        else:
            body_fields.append(f"        {fname}: form.{fname} || undefined,")
    body_str = "\n".join(body_fields)

    # Submit button — use inline style for margin since Tailwind classes may not
    # be generated when MFE is loaded via Module Federation in the shell
    if ui:
        submit_btn = '          <div style={{ paddingTop: "1.5rem" }}>\n            <Button type="submit" disabled={mutation.isPending}>\n              {mutation.isPending ? t("creating") : t("create")}\n            </Button>\n          </div>'
    else:
        submit_btn = '          <div style={{ paddingTop: "1.5rem" }}>\n            <button type="submit" disabled={mutation.isPending}\n              className="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground h-10 px-4 py-2 hover:bg-primary/90 disabled:opacity-50">\n              {mutation.isPending ? t("creating") : t("create")}\n            </button>\n          </div>'

    # Success/error messages
    if ui:
        success_msg = '          {success && <Alert className="mb-2"><AlertDescription>{t("createdSuccessfully")}</AlertDescription></Alert>}'
        error_msg = '          {mutation.error && <Alert variant="destructive" className="mb-2"><AlertDescription>{(mutation.error as Error).message}</AlertDescription></Alert>}'
    else:
        success_msg = '          {success && <div className="mb-2 p-3 rounded-md border bg-green-50 text-green-800 text-sm">{t("createdSuccessfully")}</div>}'
        error_msg = '          {mutation.error && <div className="mb-2 p-3 rounded-md border border-destructive/50 bg-destructive/5 text-destructive text-sm">{(mutation.error as Error).message}</div>}'

    # Card wrapper — clean indentation
    if ui:
        form_open = (
            f'      <Card className="max-w-xl">\n'
            f"        <CardHeader>\n"
            f"          <CardTitle>{label}</CardTitle>\n"
            f"        </CardHeader>\n"
            f"        <CardContent>\n"
            f"{success_msg}\n"
            f"{error_msg}\n"
            f'          <form onSubmit={{handleSubmit}} className="space-y-4">'
        )
        form_close = f"{submit_btn}\n          </form>\n        </CardContent>\n      </Card>"
    else:
        form_open = (
            f'      <h1 className="text-2xl font-bold tracking-tight mb-4">{label}</h1>\n'
            f"{success_msg}\n"
            f"{error_msg}\n"
            f'      <form onSubmit={{handleSubmit}} className="max-w-xl space-y-6">'
        )
        form_close = f"{submit_btn}\n      </form>"

    # Build lookup query hooks
    lookup_hooks = ""
    rq_imports = "useMutation, useQueryClient"
    if lookups:
        rq_imports = "useQuery, useMutation, useQueryClient"
        for lk in lookups:
            lk_res = lk["resource"]
            lk_entity = pascal_case(lk_res)
            lk_var = camel_case(lk_res) + "Options"
            lookup_hooks += (
                f"\n"
                f"  const {{ data: {lk_var}Data }} = useQuery<{{ content: {lk_entity}[] }}>({{  \n"
                f'    queryKey: ["{lk_res}", "all"],\n'
                f'    queryFn: () => api.get("/{lk_res}", {{ params: {{ size: "100" }} }}),\n'
                f"  }});\n"
                f"  const {lk_var} = {lk_var}Data?.content ?? [];\n"
            )

    # Build lookup type imports
    lookup_type_imports = ""
    if lookups:
        for lk in lookups:
            lk_entity = pascal_case(lk["resource"])
            lookup_type_imports += f", {lk_entity}"

    dest.write_text(
        f'import {{ useState }} from "react";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ {rq_imports} }} from "@tanstack/react-query";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ Create{entity}Request, {entity}{lookup_type_imports} }} from "{_api_pkg}";\n'
        f"{ui_import}"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f"  const queryClient = useQueryClient();\n"
        f"  const [form, setForm] = useState({{ {state_init} }});\n"
        f"  const [success, setSuccess] = useState(false);\n"
        f"{lookup_hooks}"
        f"\n"
        f"  const mutation = useMutation({{\n"
        f"    mutationFn: (data: Create{entity}Request) =>\n"
        f'      api.post<{entity}>("/{resource}", data),\n'
        f"    onSuccess: () => {{\n"
        f'      queryClient.invalidateQueries({{ queryKey: ["{resource}"] }});\n'
        f"      setForm({{ {state_init} }});\n"
        f"      setSuccess(true);\n"
        f"      setTimeout(() => setSuccess(false), 3000);\n"
        f"    }},\n"
        f"  }});\n"
        f"\n"
        f"  const handleSubmit = (e: React.FormEvent) => {{\n"
        f"    e.preventDefault();\n"
        f"    mutation.mutate({{\n"
        f"{body_str}\n"
        f"    }} as Create{entity}Request);\n"
        f"  }};\n"
        f"\n"
        f"  return (\n"
        f'    <div className="space-y-4">\n'
        f"{form_open}\n"
        f"{inputs_str}\n"
        f"{form_close}\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


def write_dashboard_page(
    dest: Path,
    component: str,
    label: str,
    resource: str,
    fields: list[dict],
    uikit_name: str = "",
    api_client_name: str = "",
) -> None:
    """Generate a dashboard page with stat cards + bar chart + recent items table."""
    entity = pascal_case(resource)
    _api_pkg = api_client_name or "my-api-client"
    ui = uikit_name

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
