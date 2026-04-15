"""Generate command — create a project from a template."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer
import yaml

from apps_generator.core.generator import generate as run_generate
from apps_generator.templates.registry import resolve_template
from apps_generator.utils.console import console
from apps_generator.utils.naming import title_case, pascal_case


def generate(
    template: str = typer.Argument(help="Template name, local path, or repo/name[:version]."),
    output_dir: Path = typer.Option(
        None, "--output", "-o", help="Output directory. Defaults to ./<projectName>."
    ),
    parameters_file: Optional[Path] = typer.Option(
        None, "--parameters", "-p", help="YAML file with parameter values."
    ),
    set_values: Optional[list[str]] = typer.Option(
        None, "--set", "-s", help="Set parameter: key=value (repeatable)."
    ),
    shell: Optional[Path] = typer.Option(
        None, "--shell", help="Path to an existing platform-shell project. Automatically registers this frontend app in the shell's remotes.json.",
    ),
    uikit: Optional[Path] = typer.Option(
        None, "--uikit", help="Path to a ui-kit project. Adds it as a dependency and extends Tailwind config.",
    ),
    gateway: Optional[Path] = typer.Option(
        None, "--gateway", help="Path to an api-gateway project. Registers this backend's route in the gateway.",
    ),
    api_client: Optional[Path] = typer.Option(
        None, "--api-client", help="Path to an api-client project. Adds it as a dependency.",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing output directory."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be generated without writing."),
    no_interactive: bool = typer.Option(False, "--no-interactive", help="Disable interactive prompts."),
) -> None:
    """Generate a project from a template."""
    # Resolve template
    template_info = resolve_template(template)
    if not template_info:
        console.print(f"[red]Error:[/red] Template '{template}' not found.")
        console.print("  Run [bold]appgen templates list[/bold] to see available templates.")
        raise typer.Exit(1)

    # Validate --shell is only used with frontend-app
    if shell is not None and template_info.name != "frontend-app":
        console.print("[red]Error:[/red] --shell can only be used with the 'frontend-app' template.")
        raise typer.Exit(1)

    # Validate --uikit is only used with frontend-app or platform-shell
    if uikit is not None and template_info.name not in ("frontend-app", "platform-shell"):
        console.print("[red]Error:[/red] --uikit can only be used with 'frontend-app' or 'platform-shell' templates.")
        raise typer.Exit(1)

    # Validate --gateway is only used with api-domain
    if gateway is not None and template_info.name != "api-domain":
        console.print("[red]Error:[/red] --gateway can only be used with the 'api-domain' template.")
        raise typer.Exit(1)

    # Validate --api-client is only used with frontend-app or platform-shell
    if api_client is not None and template_info.name not in ("frontend-app", "platform-shell"):
        console.print("[red]Error:[/red] --api-client can only be used with 'frontend-app' or 'platform-shell' templates.")
        raise typer.Exit(1)

    if shell is not None:
        remotes_file = _find_remotes_json(shell)
        if remotes_file is None:
            console.print(f"[red]Error:[/red] Could not find remotes.json in shell at '{shell}'.")
            console.print("  Make sure --shell points to a generated platform-shell project directory.")
            raise typer.Exit(1)

    # Load file-based parameters
    file_values: dict = {}
    if parameters_file:
        if not parameters_file.exists():
            console.print(f"[red]Error:[/red] Parameters file not found: {parameters_file}")
            raise typer.Exit(1)
        with open(parameters_file) as f:
            file_values = yaml.safe_load(f) or {}

    # Parse CLI --set values
    cli_values: dict[str, str] = {}
    if set_values:
        for sv in set_values:
            if "=" not in sv:
                console.print(f"[red]Error:[/red] Invalid --set format: '{sv}'. Expected key=value.")
                raise typer.Exit(1)
            key, val = sv.split("=", 1)
            cli_values[key.strip()] = val.strip()

    # Determine output directory
    if output_dir is None:
        project_name = cli_values.get("projectName") or file_values.get("projectName") or template_info.defaults.get("projectName")
        if project_name:
            output_dir = Path.cwd() / project_name
        else:
            output_dir = Path.cwd() / template_info.name

    result = run_generate(
        template_dir=template_info.path,
        output_dir=output_dir,
        file_values=file_values,
        cli_values=cli_values,
        interactive=not no_interactive,
        dry_run=dry_run,
        force=force,
        source=template_info.source,
    )

    # Post-generation: create page components and update pages.ts if pages were specified
    if template_info.name == "frontend-app" and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        pages_str = cli_values.get("pages") or file_values.get("pages", "[]")
        pages = _parse_pages(pages_str)

        if pages:
            project_root = _find_project_root(result, project_name)
            if project_root:
                _generate_page_components(project_root, pages, project_name)

    # Register in shell if --shell was provided
    if shell is not None and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        dev_port = cli_values.get("devPort") or file_values.get("devPort", "5001")
        menu_label = cli_values.get("menuLabel") or file_values.get("menuLabel", "") or title_case(project_name)
        pages_str = cli_values.get("pages") or file_values.get("pages", "[]")
        pages = _parse_pages(pages_str)

        _register_in_shell(
            shell_path=shell,
            app_name=project_name,
            dev_port=str(dev_port),
            menu_label=menu_label,
            pages=pages,
        )

    # Register ui-kit if --uikit was provided
    if uikit is not None and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        project_root = _find_consumer_root(result, project_name)
        if project_root:
            _register_uikit(uikit_path=uikit, consumer_root=project_root)

    # Register in gateway if --gateway was provided
    if gateway is not None and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        _register_in_gateway(gateway_path=gateway, service_name=project_name)

    # Link api-client if --api-client was provided
    if api_client is not None and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        project_root = _find_consumer_root(result, project_name)
        if project_root:
            _register_api_client(api_client_path=api_client, consumer_root=project_root)


def _parse_pages(pages_str: str) -> list[dict]:
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


def _find_project_root(output_dir: Path, project_name: str) -> Path | None:
    """Find the generated project root directory."""
    # output_dir/projectName/src/pages.ts
    candidate = output_dir / project_name
    if (candidate / "src" / "pages.ts").exists():
        return candidate
    # output_dir/src/pages.ts
    if (output_dir / "src" / "pages.ts").exists():
        return output_dir
    return None


def _generate_page_components(project_root: Path, pages: list[dict], project_name: str) -> None:
    """Generate individual page component files and update pages.ts registry."""
    routes_dir = project_root / "src" / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)

    imports: list[str] = ['import type { ComponentType } from "react";']
    imports.append('import { HomePage } from "./routes/HomePage";')
    registry_entries: list[str] = ["  default: HomePage,"]

    for page in pages:
        path = page.get("path", "")
        label = page.get("label", title_case(path))
        component_name = pascal_case(path) + "Page"

        # Generate page component file
        page_file = routes_dir / f"{component_name}.tsx"
        if not page_file.exists():
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


def _find_remotes_json(shell_path: Path) -> Path | None:
    """Find remotes.json inside a shell project directory."""
    shell_path = shell_path.resolve()

    candidate = shell_path / "public" / "remotes.json"
    if candidate.exists():
        return candidate

    if shell_path.is_dir():
        for child in shell_path.iterdir():
            if child.is_dir():
                candidate = child / "public" / "remotes.json"
                if candidate.exists():
                    return candidate

    return None


def _register_in_shell(
    shell_path: Path,
    app_name: str,
    dev_port: str,
    menu_label: str,
    pages: list[dict] | None = None,
) -> None:
    """Add a frontend app entry to the shell's remotes.json."""
    remotes_file = _find_remotes_json(shell_path)
    if remotes_file is None:
        console.print("[yellow]Warning:[/yellow] Could not find shell's remotes.json — skipping registration.")
        return

    with open(remotes_file) as f:
        remotes: list[dict] = json.load(f)

    existing_names = {r.get("name") for r in remotes}
    if app_name in existing_names:
        console.print(f"[yellow]App '{app_name}' already registered in shell — skipping.[/yellow]")
        return

    new_entry: dict = {
        "name": app_name,
        "url": f"http://localhost:{dev_port}",
        "menuLabel": menu_label,
        "menuIcon": "",
    }

    if pages:
        new_entry["pages"] = [
            {"path": p["path"], "label": p.get("label", title_case(p["path"]))}
            for p in pages
        ]

    remotes.append(new_entry)

    with open(remotes_file, "w") as f:
        json.dump(remotes, f, indent=2)
        f.write("\n")

    # Add translation keys for nav labels to shell's locale files
    if pages:
        _add_nav_translations(remotes_file.parent.parent, app_name, menu_label, pages)

    pages_info = f" ({len(pages)} pages)" if pages else ""
    console.print(
        f"[green]Registered '{app_name}' in shell at {remotes_file}{pages_info}[/green]\n"
        f"  URL: http://localhost:{dev_port}\n"
        f"  Menu: {menu_label}"
    )
    if pages:
        for p in pages:
            console.print(f"    /{app_name}/{p['path']} — {p.get('label', p['path'])}")


def _find_consumer_root(output_dir: Path, project_name: str) -> Path | None:
    """Find the generated project root directory (for shell or frontend-app)."""
    candidate = output_dir / project_name
    if (candidate / "package.json").exists():
        return candidate
    if (output_dir / "package.json").exists():
        return output_dir
    return None


def _copy_lib_to_local_deps(lib_dir: Path, consumer_root: Path, lib_name: str) -> None:
    """Copy a shared library into consumer's local-deps/ for Docker builds."""
    import shutil
    local_deps = consumer_root / "local-deps" / lib_name
    local_deps.mkdir(parents=True, exist_ok=True)

    # Copy package.json
    shutil.copy2(lib_dir / "package.json", local_deps / "package.json")

    # Copy dist/ if it exists (built library)
    dist_dir = lib_dir / "dist"
    if dist_dir.exists():
        dest_dist = local_deps / "dist"
        if dest_dist.exists():
            shutil.rmtree(dest_dist)
        shutil.copytree(dist_dir, dest_dist)

    # Copy source files referenced in package.json exports (tailwind-preset, globals.css)
    for src_file in ["src/tailwind-preset.ts", "src/globals.css"]:
        src = lib_dir / src_file
        if src.exists():
            dest = local_deps / src_file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)


def _register_uikit(uikit_path: Path, consumer_root: Path) -> None:
    """Add ui-kit as a file: dependency and extend Tailwind config."""
    uikit_path = uikit_path.resolve()

    uikit_pkg_path = _find_uikit_package_json(uikit_path)
    if uikit_pkg_path is None:
        console.print("[yellow]Warning:[/yellow] Could not find ui-kit's package.json — skipping.")
        return

    with open(uikit_pkg_path) as f:
        uikit_pkg = json.load(f)

    uikit_name = uikit_pkg.get("name", "")
    if not uikit_name:
        console.print("[yellow]Warning:[/yellow] ui-kit package.json has no name — skipping.")
        return

    uikit_dir = uikit_pkg_path.parent.resolve()

    # Copy library into local-deps/ (for Docker builds)
    _copy_lib_to_local_deps(uikit_dir, consumer_root, uikit_name)

    # 1. Add file: dependency pointing to local-deps/ (works both locally and in Docker)
    consumer_pkg_path = consumer_root / "package.json"
    with open(consumer_pkg_path) as f:
        consumer_pkg = json.load(f)

    deps = consumer_pkg.get("dependencies", {})
    deps[uikit_name] = f"file:./local-deps/{uikit_name}"
    consumer_pkg["dependencies"] = deps

    with open(consumer_pkg_path, "w") as f:
        json.dump(consumer_pkg, f, indent=2)
        f.write("\n")

    # 2. Update tailwind.config.ts with shadcn theme + ui-kit content path
    tailwind_path = consumer_root / "tailwind.config.ts"
    if tailwind_path.exists():
        tailwind_content = f'''/** @type {{import('tailwindcss').Config}} */
export default {{
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{{ts,tsx}}",
    "./local-deps/{uikit_name}/src/**/*.{{ts,tsx}}",
  ],
  theme: {{
    extend: {{
      colors: {{
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {{
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        }},
        secondary: {{
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        }},
        destructive: {{
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        }},
        muted: {{
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        }},
        accent: {{
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        }},
        popover: {{
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        }},
        card: {{
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        }},
      }},
      borderRadius: {{
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      }},
    }},
  }},
  plugins: [],
}};
'''
        tailwind_path.write_text(tailwind_content)

    # 3. Replace consumer's index.css with ui-kit's globals.css (includes Tailwind + CSS variables)
    uikit_css = uikit_dir / "src" / "globals.css"
    index_css = consumer_root / "src" / "index.css"
    if index_css.exists() and uikit_css.exists():
        index_css.write_text(uikit_css.read_text())

    console.print(
        f"[green]Linked ui-kit '{uikit_name}' to {consumer_root.name}[/green]\n"
        f"  Dependency: {uikit_name} -> file:./local-deps/{uikit_name}\n"
        f"  Tailwind: shadcn theme applied"
    )


def _register_in_gateway(gateway_path: Path, service_name: str) -> None:
    """Add a backend service route to the gateway's routes.yaml."""
    gateway_path = gateway_path.resolve()

    # Find routes.yaml
    routes_file = _find_gateway_routes(gateway_path)
    if routes_file is None:
        console.print("[yellow]Warning:[/yellow] Could not find gateway's routes.yaml — skipping.")
        return

    with open(routes_file) as f:
        routes_config = yaml.safe_load(f) or {}

    routes = routes_config.get("spring", {}).get("cloud", {}).get("gateway", {}).get("routes", [])
    if not isinstance(routes, list):
        routes = []

    # Check if already registered
    existing_ids = {r.get("id") for r in routes}
    if service_name in existing_ids:
        console.print(f"[yellow]Service '{service_name}' already registered in gateway — skipping.[/yellow]")
        return

    # Derive API path from service name: "order-service" → "order", "user-service" → "user"
    api_prefix = service_name.replace("-service", "").replace("_service", "")

    # Auto-assign port (8081, 8082, ...) based on existing routes
    base_port = 8081
    existing_ports = set()
    for r in routes:
        uri = r.get("uri", "")
        if ":" in uri:
            try:
                existing_ports.add(int(uri.rsplit(":", 1)[1]))
            except (ValueError, IndexError):
                pass
    port = base_port
    while port in existing_ports:
        port += 1

    new_route = {
        "id": service_name,
        "uri": f"http://localhost:{port}",
        "predicates": [f"Path=/api/{api_prefix}/**"],
        "filters": ["StripPrefix=2"],
    }
    routes.append(new_route)

    # Write back
    routes_config.setdefault("spring", {}).setdefault("cloud", {}).setdefault("gateway", {})["routes"] = routes
    with open(routes_file, "w") as f:
        yaml.dump(routes_config, f, default_flow_style=False, sort_keys=False)

    console.print(
        f"[green]Registered '{service_name}' in gateway[/green]\n"
        f"  Route: /api/{api_prefix}/** → http://localhost:{port}\n"
        f"  Config: {routes_file}"
    )


def _register_api_client(api_client_path: Path, consumer_root: Path) -> None:
    """Add api-client as a file: dependency to a consumer project."""
    api_client_path = api_client_path.resolve()

    pkg_path = _find_uikit_package_json(api_client_path)
    if pkg_path is None:
        console.print("[yellow]Warning:[/yellow] Could not find api-client's package.json — skipping.")
        return

    with open(pkg_path) as f:
        pkg = json.load(f)

    client_name = pkg.get("name", "")
    if not client_name:
        console.print("[yellow]Warning:[/yellow] api-client package.json has no name — skipping.")
        return

    client_dir = pkg_path.parent.resolve()

    # Copy library into local-deps/ (for Docker builds)
    _copy_lib_to_local_deps(client_dir, consumer_root, client_name)

    # Add file: dependency pointing to local-deps/
    consumer_pkg_path = consumer_root / "package.json"
    with open(consumer_pkg_path) as f:
        consumer_pkg = json.load(f)

    deps = consumer_pkg.get("dependencies", {})
    deps[client_name] = f"file:./local-deps/{client_name}"
    consumer_pkg["dependencies"] = deps

    with open(consumer_pkg_path, "w") as f:
        json.dump(consumer_pkg, f, indent=2)
        f.write("\n")

    console.print(
        f"[green]Linked api-client '{client_name}' to {consumer_root.name}[/green]\n"
        f"  Dependency: {client_name} -> file:./local-deps/{client_name}"
    )


def _find_gateway_routes(gateway_path: Path) -> Path | None:
    """Find routes.yaml in a gateway project."""
    # Direct: gateway_path/src/main/resources/routes.yaml
    candidate = gateway_path / "src" / "main" / "resources" / "routes.yaml"
    if candidate.exists():
        return candidate

    # One level down
    if gateway_path.is_dir():
        for child in gateway_path.iterdir():
            if child.is_dir():
                candidate = child / "src" / "main" / "resources" / "routes.yaml"
                if candidate.exists():
                    return candidate

    return None


def _add_nav_translations(
    shell_project_root: Path,
    app_name: str,
    menu_label: str,
    pages: list[dict],
) -> None:
    """Add navigation translation keys to the shell's locale files."""
    locales_dir = shell_project_root / "src" / "i18n" / "locales"
    if not locales_dir.exists():
        return

    nav_keys = {}
    for p in pages:
        nav_keys[p["path"]] = p.get("label", title_case(p["path"]))

    for locale_file in locales_dir.glob("*.json"):
        try:
            with open(locale_file) as f:
                translations = json.load(f)

            if "nav" not in translations:
                translations["nav"] = {}
            if app_name not in translations["nav"]:
                translations["nav"][app_name] = {}

            for path, label in nav_keys.items():
                if path not in translations["nav"][app_name]:
                    translations["nav"][app_name][path] = label

            with open(locale_file, "w") as f:
                json.dump(translations, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except (json.JSONDecodeError, OSError):
            pass


def _find_uikit_package_json(uikit_path: Path) -> Path | None:
    """Find package.json inside a ui-kit project directory."""
    candidate = uikit_path / "package.json"
    if candidate.exists():
        return candidate

    if uikit_path.is_dir():
        for child in uikit_path.iterdir():
            if child.is_dir():
                candidate = child / "package.json"
                if candidate.exists():
                    return candidate

    return None
