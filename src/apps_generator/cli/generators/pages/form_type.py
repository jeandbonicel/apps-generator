"""``form`` page type — create form with useApiClient + useMutation."""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case, title_case

from .base import detect_lookup, page_target
from .registry import PageContext, PageTypeInfo, get_registry


def emit_form(page: dict, ctx: PageContext) -> None:
    """Generate a form page with useApiClient + useMutation."""
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])

    # Auto-detect lookups (mutates page["fields"] in-place to preserve prior
    # behaviour — the old dispatcher did this before calling the emitter).
    if ctx.all_resources:
        other_resources = [r for r in ctx.all_resources if r != resource]
        for f in fields:
            if "lookup" not in f:
                detected = detect_lookup(f, other_resources)
                if detected:
                    f["lookup"] = detected

    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name

    # ui-kit imports
    if ui:
        ui_import = (
            f"import {{ Button, Input, Label, Textarea, Checkbox, "
            f"Card, CardContent, CardHeader, CardTitle, Alert, AlertDescription, "
            f'DatePicker, Combobox }} from "{ui}";\n'
        )
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
            # Lookup field -> typeahead Combobox (ui-kit Phase 0).
            # Native <select> gets unusable once the option list grows; Combobox
            # has a built-in search input so it scales.
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
                    f"            <Combobox\n"
                    f'              id="{fname}"\n'
                    f"              options={{{lk_var}.map((opt: any) => ({{ value: String(opt.{lk_val}), label: String(opt.{lk_label}) }}))}}\n"
                    f"              value={{form.{fname}}}\n"
                    f'              onChange={{(v) => setForm(f => ({{...f, {fname}: v ?? ""}}))}}\n'
                    f'              placeholder="Select {flabel}..."\n'
                    f"            />\n"
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
                # Calendar-popover picker from ui-kit (Phase 0) — form state stays
                # a plain YYYY-MM-DD string so the backend DTO contract doesn't
                # change; we just swap the UI.
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f"          <DatePicker\n"
                    f'            id="{fname}"\n'
                    f"            value={{form.{fname} ? new Date(form.{fname}) : undefined}}\n"
                    f'            onChange={{(d) => setForm(f => ({{...f, {fname}: d ? d.toISOString().slice(0, 10) : ""}}))}}\n'
                    f'            placeholder="Select {flabel}..."\n'
                    f"          />\n"
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
            elif ft == "enum" and f.get("values"):
                options = "".join(f'\n              <option value="{v}">{title_case(v)}</option>' for v in f["values"])
                inputs.append(
                    f'        <div className="space-y-2">\n'
                    f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                    f'          <select id="{fname}" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}>\n"
                    f'              <option value="">Select {flabel}...</option>{options}\n'
                    f"            </select>\n"
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
            elif ft == "enum" and f.get("values"):
                options = "".join(f'\n              <option value="{v}">{title_case(v)}</option>' for v in f["values"])
                inputs.append(
                    f"        <div>\n"
                    f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}{req_star}</label>\n'
                    f'          <select id="{fname}" className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"\n'
                    f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}>\n"
                    f'              <option value="">Select {flabel}...</option>{options}\n'
                    f"            </select>\n"
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


PAGE_TYPE = PageTypeInfo(
    name="form",
    description="Create form for a resource, with smart type-aware inputs and auto lookups.",
    emit=emit_form,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
