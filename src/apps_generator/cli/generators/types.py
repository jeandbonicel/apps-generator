"""TypeScript type generation — generates TS interfaces in an api-client package."""

from __future__ import annotations

from pathlib import Path

from apps_generator.utils.console import console
from apps_generator.utils.naming import pascal_case, camel_case

from apps_generator.cli.generators.resources import TS_TYPES


def generate_resource_types(api_client_src: Path, resources: list[dict]) -> None:
    """Generate TypeScript interfaces in the api-client package."""
    resources_dir = api_client_src / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)

    exports = []

    for resource in resources:
        name = resource.get("name", "")
        fields = resource.get("fields", [])
        if not name:
            continue

        entity = pascal_case(name)
        filename = f"{name}.ts"
        exports.append(name)

        # Build interface fields
        response_fields = ["  id: number;", "  tenantId: string;"]
        create_fields = []
        for f in fields:
            ts_type = TS_TYPES.get(f.get("type", "string"), "string")
            fname = camel_case(f["name"])
            required = f.get("required", False)
            if required:
                response_fields.append(f"  {fname}: {ts_type};")
                create_fields.append(f"  {fname}: {ts_type};")
            else:
                response_fields.append(f"  {fname}: {ts_type} | null;")
                create_fields.append(f"  {fname}?: {ts_type};")
        response_fields.extend(["  createdAt: string;", "  updatedAt: string;"])

        ts_content = (
            f"// Types generated from resource schema — DO NOT EDIT\n"
            f"\n"
            f"export interface {entity} {{\n"
            f"{''.join(chr(10) + rf for rf in response_fields)}\n"
            f"}}\n"
            f"\n"
            f"export interface Create{entity}Request {{\n"
            f"{''.join(chr(10) + cf for cf in create_fields)}\n"
            f"}}\n"
            f"\n"
            f"export interface Update{entity}Request {{\n"
            f"{''.join(chr(10) + cf for cf in create_fields)}\n"
            f"}}\n"
            f"\n"
            f"export interface PageResponse<T> {{\n"
            f"  content: T[];\n"
            f"  totalElements: number;\n"
            f"  totalPages: number;\n"
            f"  number: number;\n"
            f"  size: number;\n"
            f"}}\n"
        )

        (resources_dir / filename).write_text(ts_content)
        console.print(f"    Created: src/resources/{filename}")

    # Barrel export
    barrel = "\n".join(f'export * from "./{name}";' for name in exports)
    (resources_dir / "index.ts").write_text(barrel + "\n")

    # Update main index.ts to re-export resources
    main_index = api_client_src / "index.ts"
    if main_index.exists():
        content = main_index.read_text()
        export_line = 'export * from "./resources";'
        if export_line not in content:
            with open(main_index, "a") as f:
                f.write(f"\n{export_line}\n")
            console.print("    Updated: src/index.ts (added resources export)")

    console.print(f"[green]Generated TypeScript types for {len(exports)} resource(s)[/green]")
