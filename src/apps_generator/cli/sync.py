"""Sync command — regenerate TypeScript types from a live backend's OpenAPI spec."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import typer

from apps_generator.utils.console import console
from apps_generator.utils.naming import camel_case


sync_app = typer.Typer(name="sync", help="Sync API types between backend and frontend.", no_args_is_help=True)


@sync_app.command("types")
def sync_types(
    from_url: str = typer.Option(
        ..., "--from", help="OpenAPI spec URL (e.g., http://localhost:8082/v3/api-docs)."
    ),
    to: Path = typer.Option(
        ..., "--to", help="Path to the api-client project."
    ),
) -> None:
    """Regenerate TypeScript types from a live backend's OpenAPI specification.

    Fetches the OpenAPI JSON from a running Spring Boot service (SpringDoc)
    and generates TypeScript interfaces in the api-client package.
    """
    console.print(f"\n[bold]Syncing types from:[/bold] {from_url}")

    # Fetch OpenAPI spec
    try:
        resp = httpx.get(from_url, timeout=10)
        resp.raise_for_status()
        spec = resp.json()
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] Failed to fetch OpenAPI spec: {e}")
        raise typer.Exit(1)
    except json.JSONDecodeError:
        console.print("[red]Error:[/red] Response is not valid JSON.")
        raise typer.Exit(1)

    # Find api-client src dir
    to = to.resolve()
    src_dir: Path | None = None
    for child in [to] + list(to.iterdir()):
        if child.is_dir() and (child / "src").is_dir():
            src_dir = child / "src"
            break
    if not src_dir:
        console.print(f"[red]Error:[/red] Could not find src/ in {to}")
        raise typer.Exit(1)

    # Parse schemas from OpenAPI spec
    schemas = spec.get("components", {}).get("schemas", {})
    if not schemas:
        console.print("[yellow]Warning:[/yellow] No schemas found in OpenAPI spec.")
        raise typer.Exit(0)

    # Group schemas by resource (heuristic: XxxResponse, CreateXxxRequest, UpdateXxxRequest)
    resources = _group_schemas(schemas)

    if not resources:
        console.print("[yellow]Warning:[/yellow] No resource schemas detected.")
        raise typer.Exit(0)

    # Generate TypeScript types
    resources_dir = src_dir / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)

    exports = []
    for resource_name, type_schemas in resources.items():
        filename = f"{resource_name}.ts"
        exports.append(resource_name)

        lines = ["// Types synced from OpenAPI spec — DO NOT EDIT", ""]

        for schema_name, schema in type_schemas.items():
            ts_interface = _schema_to_typescript(schema_name, schema, schemas)
            lines.append(ts_interface)

        # Always include PageResponse
        lines.append(
            "export interface PageResponse<T> {\n"
            "  content: T[];\n"
            "  totalElements: number;\n"
            "  totalPages: number;\n"
            "  number: number;\n"
            "  size: number;\n"
            "}\n"
        )

        (resources_dir / filename).write_text("\n".join(lines))
        console.print(f"  Generated: src/resources/{filename} ({len(type_schemas)} types)")

    # Barrel export
    barrel = "\n".join(f'export * from "./{name}";' for name in exports)
    (resources_dir / "index.ts").write_text(barrel + "\n")

    # Update main index.ts
    main_index = src_dir / "index.ts"
    if main_index.exists():
        content = main_index.read_text()
        export_line = 'export * from "./resources";'
        if export_line not in content:
            with open(main_index, "a") as f:
                f.write(f"\n{export_line}\n")

    # Bump patch version
    _bump_patch_version(to)

    console.print(f"\n[green]Synced {len(exports)} resource type(s) from OpenAPI spec[/green]")


def _group_schemas(schemas: dict) -> dict[str, dict]:
    """Group OpenAPI schemas by resource name.

    Heuristic: looks for patterns like ProductResponse, CreateProductRequest, etc.
    The resource name is extracted by removing the suffix.
    """
    resources: dict[str, dict] = {}
    suffixes = ["Response", "Request"]

    for name, schema in schemas.items():
        # Skip Spring/Java internal types
        if name.startswith("Page") or name.startswith("Pageable") or name.startswith("Sort"):
            continue

        resource_name = None
        for suffix in suffixes:
            if name.endswith(suffix):
                # Remove prefix (Create/Update) and suffix
                base = name.removesuffix(suffix)
                for prefix in ["Create", "Update"]:
                    if base.startswith(prefix):
                        base = base.removeprefix(prefix)
                        break
                resource_name = camel_case(base)
                break

        if not resource_name:
            # Try as a direct entity name
            resource_name = camel_case(name)

        if resource_name not in resources:
            resources[resource_name] = {}
        resources[resource_name][name] = schema

    return resources


def _schema_to_typescript(name: str, schema: dict, all_schemas: dict) -> str:
    """Convert an OpenAPI schema to a TypeScript interface."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    fields = []
    for prop_name, prop in properties.items():
        ts_type = _openapi_type_to_ts(prop, all_schemas)
        optional = prop_name not in required
        nullable = prop.get("nullable", False)

        if nullable:
            ts_type = f"{ts_type} | null"
        suffix = "?" if optional and not nullable else ""
        fields.append(f"  {prop_name}{suffix}: {ts_type};")

    return f"export interface {name} {{\n" + "\n".join(fields) + "\n}\n"


def _openapi_type_to_ts(prop: dict, all_schemas: dict) -> str:
    """Map an OpenAPI property type to TypeScript."""
    if "$ref" in prop:
        ref = prop["$ref"].split("/")[-1]
        return ref

    prop_type = prop.get("type", "string")
    prop.get("format", "")

    if prop_type == "string":
        return "string"
    elif prop_type == "integer" or prop_type == "number":
        return "number"
    elif prop_type == "boolean":
        return "boolean"
    elif prop_type == "array":
        items = prop.get("items", {})
        item_type = _openapi_type_to_ts(items, all_schemas)
        return f"{item_type}[]"
    elif prop_type == "object":
        return "Record<string, unknown>"
    else:
        return "unknown"


def _bump_patch_version(api_client_path: Path) -> None:
    """Bump the patch version in package.json."""
    for child in [api_client_path] + list(api_client_path.iterdir()):
        pkg_path = child / "package.json" if child.is_dir() else child
        if pkg_path.name == "package.json" and pkg_path.exists():
            try:
                with open(pkg_path) as f:
                    pkg = json.load(f)
                version = pkg.get("version", "0.1.0")
                parts = version.split(".")
                if len(parts) == 3:
                    parts[2] = str(int(parts[2]) + 1)
                    new_version = ".".join(parts)
                    pkg["version"] = new_version
                    with open(pkg_path, "w") as f:
                        json.dump(pkg, f, indent=2)
                        f.write("\n")
                    console.print(f"  Bumped version: {version} → {new_version}")
                return
            except (json.JSONDecodeError, ValueError, OSError):
                pass
