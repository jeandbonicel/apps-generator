"""``edit`` page type — update form + delete confirmation for a single record.

Mirrors ``form_type`` (same auto-detected lookups, same type-aware inputs)
but adds three things:

1. A :func:`useQuery` fetch of the existing record (id from ``?id=`` query
   string, like ``detail_type``) and a :func:`useEffect` that seeds the
   form state once the data lands.
2. A PUT mutation that replaces the existing record, with
   ``t("updatedSuccessfully")`` feedback.
3. A destructive Delete button wrapped in an :component:`AlertDialog` —
   confirmation step, then DELETE, then ``history.back()`` to return to
   whatever referred the user here.

The field-input rendering is duplicated from ``form_type`` for now. A
follow-up could extract it into :mod:`.base` so both emitters share a
single source of truth — deferred to keep this PR focused.
"""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case, title_case

from .base import detect_lookup, page_target
from .registry import PageContext, PageTypeInfo, get_registry


def emit_edit(page: dict, ctx: PageContext) -> None:
    """Generate an edit page — hydrated form + PUT + delete with confirm."""
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])

    # Auto-detect lookups (same convention as form_type, mutating fields in
    # place to preserve the existing contract).
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

    # ui-kit imports — edit needs Form primitives + AlertDialog for the
    # destructive confirm flow. AlertDialog is a Phase 0 addition.
    if ui:
        ui_import = (
            f"import {{ Button, Input, Label, Textarea, Checkbox, "
            f"Card, CardContent, CardHeader, CardTitle, Alert, AlertDescription, "
            f"AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, "
            f"AlertDialogFooter, AlertDialogTitle, AlertDialogDescription, "
            f'AlertDialogAction, AlertDialogCancel }} from "{ui}";\n'
        )
    else:
        ui_import = ""

    # Initial empty state — filled in by useEffect once the fetch resolves.
    defaults: dict[str, str] = {}
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        if ft == "boolean":
            defaults[fname] = "false"
        else:
            defaults[fname] = '""'
    state_init = ", ".join(f"{k}: {v}" for k, v in defaults.items())

    # State hydration — map each fetched field into the form. Numbers come
    # back as numbers from the API but the form state expects strings.
    hydrate_lines: list[str] = []
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        if ft == "boolean":
            hydrate_lines.append(f"          {fname}: data.{fname} ?? false,")
        elif ft in ("integer", "long", "decimal"):
            hydrate_lines.append(f'          {fname}: data.{fname} != null ? String(data.{fname}) : "",')
        elif ft == "datetime":
            # HTML datetime-local wants YYYY-MM-DDTHH:mm (no TZ) — trim any zone.
            hydrate_lines.append(f'          {fname}: data.{fname} ? String(data.{fname}).slice(0, 16) : "",')
        else:
            hydrate_lines.append(f'          {fname}: data.{fname} ?? "",')
    hydrate_str = "\n".join(hydrate_lines)

    # Collect lookups for the extra useQuery hooks (same as form_type).
    lookups: list[dict] = []
    for f in fields:
        if "lookup" in f:
            lk = f["lookup"]
            if lk not in lookups:
                lookups.append(lk)

    # Build the form inputs — duplicated from form_type for now.
    inputs: list[str] = []
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        flabel = title_case(f["name"])
        required = f.get("required", False)
        req_star = " *" if required else ""
        lookup = f.get("lookup")

        if ui:
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
            # Plain-HTML fallback
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

    # Body of the PUT — cast numeric fields back to numbers.
    body_fields: list[str] = []
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

    # Action buttons — Save + destructive Delete with AlertDialog.
    if ui:
        save_btn = (
            '            <Button type="submit" disabled={update.isPending}>\n'
            '              {update.isPending ? t("saving") : t("save")}\n'
            "            </Button>"
        )
        delete_trigger_wrap = (
            "            <AlertDialog>\n"
            "              <AlertDialogTrigger asChild>\n"
            '                <Button type="button" variant="destructive" disabled={del_.isPending}>\n'
            '                  {del_.isPending ? t("deleting") : t("delete")}\n'
            "                </Button>\n"
            "              </AlertDialogTrigger>\n"
            "              <AlertDialogContent>\n"
            "                <AlertDialogHeader>\n"
            '                  <AlertDialogTitle>{t("confirmDelete")}</AlertDialogTitle>\n'
            '                  <AlertDialogDescription>{t("confirmDeleteDesc")}</AlertDialogDescription>\n'
            "                </AlertDialogHeader>\n"
            "                <AlertDialogFooter>\n"
            '                  <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>\n'
            '                  <AlertDialogAction onClick={() => del_.mutate()}>{t("confirm")}</AlertDialogAction>\n'
            "                </AlertDialogFooter>\n"
            "              </AlertDialogContent>\n"
            "            </AlertDialog>"
        )
        action_row = (
            '          <div className="flex gap-2" style={{ paddingTop: "1.5rem" }}>\n'
            f"{save_btn}\n"
            f"{delete_trigger_wrap}\n"
            "          </div>"
        )
        # Note: ``{{{{`` in an f-string becomes ``{{`` in the emitted .tsx —
        # that's the JSX style-prop double-brace. The emitted file is not
        # Jinja-rendered so the literal ``{{`` is safe.
        success_msg = (
            '          {success && <Alert className="mb-2">'
            '<AlertDescription>{t("updatedSuccessfully")}</AlertDescription></Alert>}'
        )
        error_msg = (
            "          {(update.error || del_.error) && "
            '<Alert variant="destructive" className="mb-2"><AlertDescription>'
            "{((update.error || del_.error) as Error).message}</AlertDescription></Alert>}"
        )
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
        form_close = f"{action_row}\n          </form>\n        </CardContent>\n      </Card>"
    else:
        save_btn = (
            '            <button type="submit" disabled={update.isPending}\n'
            '              className="inline-flex items-center justify-center rounded-md '
            "text-sm font-medium bg-primary text-primary-foreground h-10 px-4 py-2 "
            'hover:bg-primary/90 disabled:opacity-50">\n'
            '              {update.isPending ? t("saving") : t("save")}\n'
            "            </button>"
        )
        delete_trigger_wrap = (
            '            <button type="button" disabled={del_.isPending}\n'
            '              onClick={() => { if (confirm(t("confirmDelete"))) del_.mutate(); }}\n'
            '              className="inline-flex items-center justify-center rounded-md '
            "text-sm font-medium bg-destructive text-destructive-foreground h-10 px-4 py-2 "
            'hover:bg-destructive/90 disabled:opacity-50">\n'
            '              {del_.isPending ? t("deleting") : t("delete")}\n'
            "            </button>"
        )
        action_row = (
            '          <div className="flex gap-2" style={{ paddingTop: "1.5rem" }}>\n'
            f"{save_btn}\n"
            f"{delete_trigger_wrap}\n"
            "          </div>"
        )
        success_msg = (
            '          {success && <div className="mb-2 p-3 rounded-md border bg-green-50 text-green-800 text-sm">'
            '{t("updatedSuccessfully")}</div>}'
        )
        error_msg = (
            "          {(update.error || del_.error) && "
            '<div className="mb-2 p-3 rounded-md border border-destructive/50 '
            'bg-destructive/5 text-destructive text-sm">'
            "{((update.error || del_.error) as Error).message}</div>}"
        )
        form_open = (
            f'      <h1 className="text-2xl font-bold tracking-tight mb-4">{label}</h1>\n'
            f"{success_msg}\n"
            f"{error_msg}\n"
            f'      <form onSubmit={{handleSubmit}} className="max-w-xl space-y-6">'
        )
        form_close = f"{action_row}\n      </form>"

    # Lookup query hooks (same as form_type)
    lookup_hooks = ""
    rq_imports = "useQuery, useMutation, useQueryClient"
    if lookups:
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

    lookup_type_imports = ""
    for lk in lookups:
        lk_entity = pascal_case(lk["resource"])
        lookup_type_imports += f", {lk_entity}"

    dest.write_text(
        f'import {{ useState, useEffect }} from "react";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ {rq_imports} }} from "@tanstack/react-query";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ Update{entity}Request, {entity}{lookup_type_imports} }} from "{_api_pkg}";\n'
        f"{ui_import}"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f"  const queryClient = useQueryClient();\n"
        f'  const id = new URLSearchParams(window.location.search).get("id");\n'
        f"  const [form, setForm] = useState({{ {state_init} }});\n"
        f"  const [success, setSuccess] = useState(false);\n"
        f"\n"
        f"  const {{ data: existing, isLoading, error: fetchError }} = useQuery<{entity}>({{  \n"
        f'    queryKey: ["{resource}", id],\n'
        f"    queryFn: () => api.get<{entity}>(`/{resource}/${{id}}`),\n"
        f"    enabled: !!id,\n"
        f"  }});\n"
        f"\n"
        f"  useEffect(() => {{\n"
        f"    if (existing) {{\n"
        f"      setForm({{\n"
        f"{hydrate_str}\n"
        f"      }});\n"
        f"    }}\n"
        f"  }}, [existing]);\n"
        f"{lookup_hooks}"
        f"\n"
        f"  const update = useMutation({{\n"
        f"    mutationFn: (data: Update{entity}Request) =>\n"
        f"      api.put<{entity}>(`/{resource}/${{id}}`, data),\n"
        f"    onSuccess: () => {{\n"
        f'      queryClient.invalidateQueries({{ queryKey: ["{resource}"] }});\n'
        f"      setSuccess(true);\n"
        f"      setTimeout(() => setSuccess(false), 3000);\n"
        f"    }},\n"
        f"  }});\n"
        f"\n"
        f"  const del_ = useMutation({{\n"
        f"    mutationFn: () => api.delete<void>(`/{resource}/${{id}}`),\n"
        f"    onSuccess: () => {{\n"
        f'      queryClient.invalidateQueries({{ queryKey: ["{resource}"] }});\n'
        f"      window.history.back();\n"
        f"    }},\n"
        f"  }});\n"
        f"\n"
        f"  const handleSubmit = (e: React.FormEvent) => {{\n"
        f"    e.preventDefault();\n"
        f"    update.mutate({{\n"
        f"{body_str}\n"
        f"    }} as Update{entity}Request);\n"
        f"  }};\n"
        f"\n"
        f'  if (!id) return <p className="text-destructive">{{t("missingId")}}</p>;\n'
        f'  if (isLoading) return <p className="text-muted-foreground">{{t("loading")}}</p>;\n'
        f"  if (fetchError)\n"
        f'    return <p className="text-destructive">{{t("failedToLoad")}}: {{(fetchError as Error).message}}</p>;\n'
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
    name="edit",
    description="Edit form for an existing record — hydrated from GET, saves via PUT, with a destructive delete confirmation.",
    emit=emit_edit,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
