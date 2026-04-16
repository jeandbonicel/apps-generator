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


def generate_page_components(project_root: Path, pages: list[dict], project_name: str) -> None:
    """Generate individual page component files and update pages.ts registry.

    Pages with ``resource`` + ``type`` fields generate data-fetching components
    using useApiClient() and TanStack Query (list page with table, form page
    with inputs). Pages without these fields stay as simple placeholders.
    """
    routes_dir = project_root / "src" / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)

    imports: list[str] = ['import type { ComponentType } from "react";']
    imports.append('import { HomePage } from "./routes/HomePage";')
    registry_entries: list[str] = ["  default: HomePage,"]

    for page in pages:
        path = page.get("path", "")
        label = page.get("label", title_case(path))
        component_name = pascal_case(path) + "Page"
        resource = page.get("resource")
        page_type = page.get("type")
        fields = page.get("fields", [])

        page_file = routes_dir / f"{component_name}.tsx"
        if not page_file.exists():
            if resource and page_type == "list":
                write_list_page(page_file, component_name, label, resource, fields)
            elif resource and page_type == "form":
                write_form_page(page_file, component_name, label, resource, fields)
            else:
                page_file.write_text(
                    f'export function {component_name}() {{\n'
                    f'  return (\n'
                    f'    <div className="p-6">\n'
                    f'      <h1 className="text-2xl font-bold mb-4">{label}</h1>\n'
                    f'      <p className="text-gray-600">This is the {label} page of {title_case(project_name)}.</p>\n'
                    f'    </div>\n'
                    f'  );\n'
                    f'}}\n'
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
    dest: Path, component: str, label: str, resource: str, fields: list[dict],
) -> None:
    """Generate a list page with useApiClient + useQuery table."""
    from apps_generator.cli.generators.resources import TS_TYPES
    entity = pascal_case(resource)

    # Table columns
    cols = []
    for f in fields:
        fname = camel_case(f["name"])
        flabel = title_case(f["name"])
        ft = f.get("type", "string")
        if ft == "decimal":
            cols.append(f'              <td className="p-2">${{p.{fname}.toFixed(2)}}</td>')
        elif ft in ("integer", "long"):
            cols.append(f'              <td className="p-2">{{p.{fname}}}</td>')
        elif ft == "boolean":
            cols.append(f'              <td className="p-2">{{p.{fname} ? "Yes" : "No"}}</td>')
        else:
            cols.append(f'              <td className="p-2">{{p.{fname}}}</td>')

    headers = "\n".join(
        f'              <th className="p-2 text-left">{title_case(f["name"])}</th>'
        for f in fields
    )
    cells = "\n".join(cols)

    dest.write_text(
        f'import {{ useState }} from "react";\n'
        f'import {{ useQuery }} from "@tanstack/react-query";\n'
        f'import {{ useApiClient }} from "my-api-client/react";\n'
        f'import type {{ {entity}, PageResponse }} from "my-api-client";\n'
        f"\n"
        f"export function {component}() {{\n"
        f"  const api = useApiClient();\n"
        f"  const [page, setPage] = useState(0);\n"
        f"\n"
        f'  const {{ data, isLoading, error }} = useQuery<PageResponse<{entity}>>({{  \n'
        f'    queryKey: ["{resource}", page],\n'
        f'    queryFn: () => api.get<PageResponse<{entity}>>("/{resource}", {{ params: {{ page: String(page), size: "20" }} }}),\n'
        f"  }});\n"
        f"\n"
        f'  if (isLoading) return <p className="p-6 text-gray-500">Loading...</p>;\n'
        f'  if (error) return <p className="p-6 text-red-600">Failed to load: {{(error as Error).message}}</p>;\n'
        f"\n"
        f"  const items = data?.content ?? [];\n"
        f"  const totalPages = data?.totalPages ?? 0;\n"
        f"\n"
        f"  return (\n"
        f'    <div className="p-6">\n'
        f'      <div className="flex items-center justify-between mb-4">\n'
        f'        <h1 className="text-2xl font-bold">{label} ({{data?.totalElements ?? 0}})</h1>\n'
        f"      </div>\n"
        f'      <table className="w-full border-collapse">\n'
        f"        <thead>\n"
        f'          <tr className="border-b">\n'
        f"{headers}\n"
        f"          </tr>\n"
        f"        </thead>\n"
        f"        <tbody>\n"
        f"          {{items.map((p) => (\n"
        f'            <tr key={{p.id}} className="border-b">\n'
        f"{cells}\n"
        f"            </tr>\n"
        f"          ))}}\n"
        f"          {{items.length === 0 && (\n"
        f'            <tr><td colSpan={{{len(fields)}}} className="p-4 text-center text-gray-400">No data found</td></tr>\n'
        f"          )}}\n"
        f"        </tbody>\n"
        f"      </table>\n"
        f'      <div className="flex gap-2 mt-4">\n'
        f'        <button className="px-3 py-1 border rounded disabled:opacity-50" onClick={{() => setPage(p => p - 1)}} disabled={{page === 0}}>Previous</button>\n'
        f'        <span className="px-3 py-1 text-sm text-gray-500">Page {{page + 1}} of {{totalPages}}</span>\n'
        f'        <button className="px-3 py-1 border rounded disabled:opacity-50" onClick={{() => setPage(p => p + 1)}} disabled={{page >= totalPages - 1}}>Next</button>\n'
        f"      </div>\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


def write_form_page(
    dest: Path, component: str, label: str, resource: str, fields: list[dict],
) -> None:
    """Generate a form page with useApiClient + useMutation."""
    entity = pascal_case(resource)

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

    state_init = ", ".join(f'{k}: {v}' for k, v in defaults.items())

    # Build form inputs
    inputs = []
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        flabel = title_case(f["name"])
        required = f.get("required", False)
        req_star = " *" if required else ""

        if ft == "text":
            inputs.append(
                f'      <label className="block">\n'
                f'        <span className="text-sm font-medium">{flabel}{req_star}</span>\n'
                f'        <textarea className="mt-1 block w-full border rounded p-2" rows={{3}}\n'
                f'          value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{"required " if required else ""}/>\n'
                f"      </label>"
            )
        elif ft == "boolean":
            inputs.append(
                f'      <label className="flex items-center gap-2">\n'
                f'        <input type="checkbox" checked={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.checked}}))}}/>\n'
                f'        <span className="text-sm font-medium">{flabel}</span>\n'
                f"      </label>"
            )
        elif ft in ("integer", "long"):
            inputs.append(
                f'      <label className="block">\n'
                f'        <span className="text-sm font-medium">{flabel}{req_star}</span>\n'
                f'        <input type="number" className="mt-1 block w-full border rounded p-2"\n'
                f'          value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{"required " if required else ""}/>\n'
                f"      </label>"
            )
        elif ft == "decimal":
            inputs.append(
                f'      <label className="block">\n'
                f'        <span className="text-sm font-medium">{flabel}{req_star}</span>\n'
                f'        <input type="number" step="0.01" className="mt-1 block w-full border rounded p-2"\n'
                f'          value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{"required " if required else ""}/>\n'
                f"      </label>"
            )
        elif ft == "date":
            inputs.append(
                f'      <label className="block">\n'
                f'        <span className="text-sm font-medium">{flabel}{req_star}</span>\n'
                f'        <input type="date" className="mt-1 block w-full border rounded p-2"\n'
                f'          value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{"required " if required else ""}/>\n'
                f"      </label>"
            )
        else:
            inputs.append(
                f'      <label className="block">\n'
                f'        <span className="text-sm font-medium">{flabel}{req_star}</span>\n'
                f'        <input type="text" className="mt-1 block w-full border rounded p-2"\n'
                f'          value={{form.{fname}}} onChange={{e => setForm(f => ({{...f, {fname}: e.target.value}}))}}{"required " if required else ""}/>\n'
                f"      </label>"
            )

    inputs_str = "\n".join(inputs)

    # Build submission body (cast number fields)
    body_fields = []
    for f in fields:
        ft = f.get("type", "string")
        fname = camel_case(f["name"])
        if ft in ("integer", "long"):
            body_fields.append(f"        {fname}: form.{fname} ? Number(form.{fname}) : undefined,")
        elif ft == "decimal":
            body_fields.append(f"        {fname}: form.{fname} ? Number(form.{fname}) : undefined,")
        elif ft == "boolean":
            body_fields.append(f"        {fname}: form.{fname},")
        else:
            body_fields.append(f"        {fname}: form.{fname} || undefined,")
    body_str = "\n".join(body_fields)

    dest.write_text(
        f'import {{ useState }} from "react";\n'
        f'import {{ useMutation, useQueryClient }} from "@tanstack/react-query";\n'
        f'import {{ useApiClient }} from "my-api-client/react";\n'
        f'import type {{ Create{entity}Request, {entity} }} from "my-api-client";\n'
        f"\n"
        f"export function {component}() {{\n"
        f"  const api = useApiClient();\n"
        f"  const queryClient = useQueryClient();\n"
        f"  const [form, setForm] = useState({{ {state_init} }});\n"
        f"  const [success, setSuccess] = useState(false);\n"
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
        f'    <div className="p-6 max-w-lg">\n'
        f'      <h1 className="text-2xl font-bold mb-4">{label}</h1>\n'
        f'      {{success && <p className="mb-4 p-2 bg-green-100 text-green-800 rounded">Created successfully!</p>}}\n'
        f'      {{mutation.error && <p className="mb-4 p-2 bg-red-100 text-red-800 rounded">{{(mutation.error as Error).message}}</p>}}\n'
        f'      <form onSubmit={{handleSubmit}} className="space-y-4">\n'
        f"{inputs_str}\n"
        f'        <button type="submit" disabled={{mutation.isPending}}\n'
        f'          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">\n'
        f'          {{mutation.isPending ? "Creating..." : "Create"}}\n'
        f"        </button>\n"
        f"      </form>\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )
