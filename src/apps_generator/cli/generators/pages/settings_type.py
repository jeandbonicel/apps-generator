"""``settings`` page type — configuration form for a singleton resource.

Unlike ``form`` / ``edit`` which operate on a collection (``/resource`` for
listing, ``/resource/{id}`` for one record), ``settings`` treats the
resource as a single record: ``GET /{resource}`` returns the one record,
``PUT /{resource}`` replaces it. No ``id`` is needed in the URL.

Fields can be grouped via an optional ``group`` key on each field. Groups
render as shadcn ``Accordion`` items (all expanded by default), giving a
familiar multi-section settings UX. Ungrouped fields drop into a
"General" section.

Example page config::

    {
      "path": "settings",
      "label": "Organization Settings",
      "resource": "orgSettings",
      "type": "settings",
      "fields": [
        {"name": "companyName",  "type": "string",  "group": "Company"},
        {"name": "billingEmail", "type": "string",  "group": "Billing"},
        {"name": "autoRenew",    "type": "boolean", "group": "Billing"},
        {"name": "maintenance",  "type": "boolean"}
      ]
    }
"""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case, title_case

from .base import page_target
from .registry import PageContext, PageTypeInfo, get_registry


_DEFAULT_GROUP = "General"


def _group_fields(fields: list[dict]) -> list[tuple[str, list[dict]]]:
    """Bucket fields by their optional ``group`` key, preserving insertion order.

    Returns a list of ``(group_label, fields)`` tuples. Ungrouped fields are
    collected under :data:`_DEFAULT_GROUP`. Groups appear in the order they
    first show up in the page config.
    """
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for f in fields:
        g = f.get("group") or _DEFAULT_GROUP
        if g not in groups:
            groups[g] = []
            order.append(g)
        groups[g].append(f)
    return [(g, groups[g]) for g in order]


def _render_input(field: dict, ui: bool) -> str:
    """Return one labelled input block for a field.

    Mirrors the rendering in ``form_type`` / ``edit_type`` for the supported
    types (string, text, integer/long, decimal, date, datetime, boolean,
    enum). ``settings`` doesn't participate in resource-lookup auto-detection
    because it's a singleton record.
    """
    fname = camel_case(field["name"])
    flabel = title_case(field["name"])
    ft = field.get("type", "string")
    required = field.get("required", False)
    req_star = " *" if required else ""

    if ui:
        if ft == "text":
            return (
                f'        <div className="space-y-2">\n'
                f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                f'          <Textarea id="{fname}" rows={{3}}\n'
                f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                f"        </div>"
            )
        if ft == "boolean":
            return (
                f'        <div className="flex items-center space-x-2">\n'
                f'          <Checkbox id="{fname}" checked={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: (e.target as HTMLInputElement).checked}}))}}/>\n'
                f'          <Label htmlFor="{fname}">{flabel}</Label>\n'
                f"        </div>"
            )
        if ft == "date":
            # Calendar-popover picker from ui-kit (Phase 0)
            return (
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
        if ft == "datetime":
            return (
                f'        <div className="space-y-2">\n'
                f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                f'          <Input id="{fname}" type="datetime-local"\n'
                f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                f"        </div>"
            )
        if ft in ("integer", "long"):
            return (
                f'        <div className="space-y-2">\n'
                f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                f'          <Input id="{fname}" type="number"\n'
                f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                f"        </div>"
            )
        if ft == "decimal":
            return (
                f'        <div className="space-y-2">\n'
                f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                f'          <Input id="{fname}" type="number" step="0.01"\n'
                f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
                f"        </div>"
            )
        if ft == "enum" and field.get("values"):
            options = "".join(f'\n              <option value="{v}">{title_case(v)}</option>' for v in field["values"])
            return (
                f'        <div className="space-y-2">\n'
                f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
                f'          <select id="{fname}" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"\n'
                f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}>\n"
                f'              <option value="">Select {flabel}...</option>{options}\n'
                f"            </select>\n"
                f"        </div>"
            )
        # string / fallback
        return (
            f'        <div className="space-y-2">\n'
            f'          <Label htmlFor="{fname}">{flabel}{req_star}</Label>\n'
            f'          <Input id="{fname}" type="text"\n'
            f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
            f"        </div>"
        )

    # Plain-HTML fallback
    if ft == "text":
        return (
            f"        <div>\n"
            f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}{req_star}</label>\n'
            f'          <textarea id="{fname}" className="mt-1 flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm" rows={{3}}\n'
            f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
            f"        </div>"
        )
    if ft == "boolean":
        return (
            f'        <div className="flex items-center space-x-2">\n'
            f'          <input id="{fname}" type="checkbox" className="h-4 w-4 rounded border-primary" checked={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.checked}}))}}/>\n'
            f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}</label>\n'
            f"        </div>"
        )
    if ft == "enum" and field.get("values"):
        options = "".join(f'\n              <option value="{v}">{title_case(v)}</option>' for v in field["values"])
        return (
            f"        <div>\n"
            f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}{req_star}</label>\n'
            f'          <select id="{fname}" className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"\n'
            f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}>\n"
            f'              <option value="">Select {flabel}...</option>{options}\n'
            f"            </select>\n"
            f"        </div>"
        )
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
    return (
        f"        <div>\n"
        f'          <label className="text-sm font-medium" htmlFor="{fname}">{flabel}{req_star}</label>\n'
        f'          <input id="{fname}" type="{input_type}"{step} className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"\n'
        f"            value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{'required ' if required else ''}/>\n"
        f"        </div>"
    )


def emit_settings(page: dict, ctx: PageContext) -> None:
    """Generate a settings page — singleton record with grouped sections."""
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])
    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name

    grouped = _group_fields(fields)

    # ui-kit imports — Accordion is a Phase 0 addition.
    if ui:
        ui_import = (
            f"import {{ Button, Input, Label, Textarea, Checkbox, "
            f"Card, CardContent, CardHeader, CardTitle, Alert, AlertDescription, "
            f"Accordion, AccordionItem, AccordionTrigger, AccordionContent, "
            f'DatePicker }} from "{ui}";\n'
        )
    else:
        ui_import = ""

    # Form state defaults (empty strings / false) — seeded by useEffect once
    # the singleton fetch resolves.
    defaults: dict[str, str] = {}
    for f in fields:
        fname = camel_case(f["name"])
        defaults[fname] = "false" if f.get("type") == "boolean" else '""'
    state_init = ", ".join(f"{k}: {v}" for k, v in defaults.items())

    # Hydration — same rules as edit_type: stringify numbers, slice datetime.
    hydrate_lines: list[str] = []
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        if ft == "boolean":
            hydrate_lines.append(f"          {fname}: data.{fname} ?? false,")
        elif ft in ("integer", "long", "decimal"):
            hydrate_lines.append(f'          {fname}: data.{fname} != null ? String(data.{fname}) : "",')
        elif ft == "datetime":
            hydrate_lines.append(f'          {fname}: data.{fname} ? String(data.{fname}).slice(0, 16) : "",')
        else:
            hydrate_lines.append(f'          {fname}: data.{fname} ?? "",')
    hydrate_str = "\n".join(hydrate_lines)

    # Body of the PUT — cast numeric fields.
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

    # Build grouped content — Accordion in ui branch, plain sections in fallback.
    if ui:
        # All groups open by default so users don't have to click through.
        default_values = "[" + ", ".join(f'"{g}"' for g, _ in grouped) + "]"
        group_items = []
        for group_label, group_fields in grouped:
            inputs_jsx = "\n".join(_render_input(f, True) for f in group_fields)
            group_items.append(
                f'              <AccordionItem value="{group_label}">\n'
                f"                <AccordionTrigger>{group_label}</AccordionTrigger>\n"
                f"                <AccordionContent>\n"
                f'                  <div className="space-y-4 pt-2">\n'
                f"{inputs_jsx}\n"
                f"                  </div>\n"
                f"                </AccordionContent>\n"
                f"              </AccordionItem>"
            )
        groups_block = (
            f'            <Accordion type="multiple" defaultValue={{{default_values}}} className="w-full">\n'
            + "\n".join(group_items)
            + "\n            </Accordion>"
        )
        submit_btn = (
            '            <div style={{ paddingTop: "1.5rem" }}>\n'
            '              <Button type="submit" disabled={mutation.isPending}>\n'
            '                {mutation.isPending ? t("saving") : t("save")}\n'
            "              </Button>\n"
            "            </div>"
        )
        success_msg = (
            '            {success && <Alert className="mb-2">'
            '<AlertDescription>{t("updatedSuccessfully")}</AlertDescription></Alert>}'
        )
        error_msg = (
            "            {mutation.error && "
            '<Alert variant="destructive" className="mb-2"><AlertDescription>'
            "{(mutation.error as Error).message}</AlertDescription></Alert>}"
        )
        wrapper_open = (
            f"      <Card>\n"
            f"        <CardHeader>\n"
            f"          <CardTitle>{label}</CardTitle>\n"
            f"        </CardHeader>\n"
            f"        <CardContent>\n"
            f"{success_msg}\n"
            f"{error_msg}\n"
            f'          <form onSubmit={{handleSubmit}} className="space-y-4">'
        )
        wrapper_close = "          </form>\n        </CardContent>\n      </Card>"
    else:
        # No Accordion without --uikit; render groups as plain bordered sections
        # so the visual hierarchy still reads.
        group_items = []
        for group_label, group_fields in grouped:
            inputs_jsx = "\n".join(_render_input(f, False) for f in group_fields)
            group_items.append(
                f'            <section className="rounded-lg border p-4 space-y-4">\n'
                f'              <h2 className="font-semibold">{group_label}</h2>\n'
                f"{inputs_jsx}\n"
                f"            </section>"
            )
        groups_block = "\n".join(group_items)
        submit_btn = (
            '            <div style={{ paddingTop: "1.5rem" }}>\n'
            '              <button type="submit" disabled={mutation.isPending}\n'
            '                className="inline-flex items-center justify-center rounded-md '
            "text-sm font-medium bg-primary text-primary-foreground h-10 px-4 py-2 "
            'hover:bg-primary/90 disabled:opacity-50">\n'
            '                {mutation.isPending ? t("saving") : t("save")}\n'
            "              </button>\n"
            "            </div>"
        )
        success_msg = (
            '            {success && <div className="mb-2 p-3 rounded-md border bg-green-50 text-green-800 text-sm">'
            '{t("updatedSuccessfully")}</div>}'
        )
        error_msg = (
            "            {mutation.error && "
            '<div className="mb-2 p-3 rounded-md border border-destructive/50 '
            'bg-destructive/5 text-destructive text-sm">'
            "{(mutation.error as Error).message}</div>}"
        )
        wrapper_open = (
            f'      <h1 className="text-2xl font-bold tracking-tight mb-4">{label}</h1>\n'
            f"{success_msg}\n"
            f"{error_msg}\n"
            f'      <form onSubmit={{handleSubmit}} className="space-y-6">'
        )
        wrapper_close = "      </form>"

    dest.write_text(
        f'import {{ useState, useEffect }} from "react";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ useQuery, useMutation, useQueryClient }} from "@tanstack/react-query";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ Update{entity}Request, {entity} }} from "{_api_pkg}";\n'
        f"{ui_import}"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f"  const queryClient = useQueryClient();\n"
        f"  const [form, setForm] = useState({{ {state_init} }});\n"
        f"  const [success, setSuccess] = useState(false);\n"
        f"\n"
        f"  const {{ data, isLoading, error: fetchError }} = useQuery<{entity}>({{  \n"
        f'    queryKey: ["{resource}"],\n'
        f'    queryFn: () => api.get<{entity}>("/{resource}"),\n'
        f"  }});\n"
        f"\n"
        f"  useEffect(() => {{\n"
        f"    if (data) {{\n"
        f"      setForm({{\n"
        f"{hydrate_str}\n"
        f"      }});\n"
        f"    }}\n"
        f"  }}, [data]);\n"
        f"\n"
        f"  const mutation = useMutation({{\n"
        f"    mutationFn: (payload: Update{entity}Request) =>\n"
        f'      api.put<{entity}>("/{resource}", payload),\n'
        f"    onSuccess: () => {{\n"
        f'      queryClient.invalidateQueries({{ queryKey: ["{resource}"] }});\n'
        f"      setSuccess(true);\n"
        f"      setTimeout(() => setSuccess(false), 3000);\n"
        f"    }},\n"
        f"  }});\n"
        f"\n"
        f"  const handleSubmit = (e: React.FormEvent) => {{\n"
        f"    e.preventDefault();\n"
        f"    mutation.mutate({{\n"
        f"{body_str}\n"
        f"    }} as Update{entity}Request);\n"
        f"  }};\n"
        f"\n"
        f'  if (isLoading) return <p className="text-muted-foreground">{{t("loading")}}</p>;\n'
        f"  if (fetchError)\n"
        f'    return <p className="text-destructive">{{t("failedToLoad")}}: {{(fetchError as Error).message}}</p>;\n'
        f"\n"
        f"  return (\n"
        f'    <div className="space-y-4">\n'
        f"{wrapper_open}\n"
        f"{groups_block}\n"
        f"{submit_btn}\n"
        f"{wrapper_close}\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


PAGE_TYPE = PageTypeInfo(
    name="settings",
    description="Configuration form for a singleton resource — grouped fields in an Accordion, fetched via GET and saved via PUT.",
    emit=emit_settings,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
