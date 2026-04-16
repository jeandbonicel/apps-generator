"""Generate command — create a project from a template."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml

from apps_generator.core.generator import generate as run_generate
from apps_generator.templates.registry import resolve_template
from apps_generator.utils.console import console
from apps_generator.utils.naming import title_case

from apps_generator.cli.generators.pages import parse_pages, find_project_root, generate_page_components
from apps_generator.cli.generators.shell import find_remotes_json, register_in_shell
from apps_generator.cli.generators.gateway import register_in_gateway
from apps_generator.cli.generators.linking import (
    find_consumer_root,
    register_uikit,
    register_api_client,
    find_java_root,
    find_resources_root,
    find_api_client_src,
)
from apps_generator.cli.generators.resources import parse_resources, generate_resource_scaffolding
from apps_generator.cli.generators.types import generate_resource_types
from apps_generator.cli.generators.toast import generate_toast_provider


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
        console.print(
            "[red]Error:[/red] --gateway can only be used with the 'api-domain' template.\n"
            "  Hint: Use --gateway when generating your backend service, not the frontend."
        )
        raise typer.Exit(1)

    # Validate --api-client is only used with frontend-app, platform-shell, or api-domain
    if api_client is not None and template_info.name not in ("frontend-app", "platform-shell", "api-domain"):
        console.print("[red]Error:[/red] --api-client can only be used with 'frontend-app', 'platform-shell', or 'api-domain' templates.")
        raise typer.Exit(1)

    if shell is not None:
        remotes_file = find_remotes_json(shell)
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

    # Resolve uikit name early (needed by page generator)
    _uikit_pkg_name = ""
    if uikit is not None:
        from apps_generator.cli.generators.linking import find_uikit_package_json
        import json as _json
        _uikit_pkg_path = find_uikit_package_json(uikit)
        if _uikit_pkg_path:
            _uikit_pkg_name = _json.load(open(_uikit_pkg_path)).get("name", "")

    # Post-generation: create page components and update pages.ts if pages were specified
    if template_info.name == "frontend-app" and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        pages_str = cli_values.get("pages") or file_values.get("pages", "[]")
        pages = parse_pages(pages_str)

        if pages:
            project_root = find_project_root(result, project_name)
            if project_root:
                generate_page_components(project_root, pages, project_name, uikit_name=_uikit_pkg_name)

    # Post-generation: create CRUD resources for api-domain
    if template_info.name == "api-domain" and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        base_package = cli_values.get("basePackage") or file_values.get("basePackage", "com.example")
        resources_str = cli_values.get("resources") or file_values.get("resources", "[]")
        resources = parse_resources(resources_str)

        if resources:
            java_root = find_java_root(result, project_name, base_package)
            res_root = find_resources_root(result, project_name)
            if java_root and res_root:
                generate_resource_scaffolding(java_root, res_root, resources, base_package, project_name)

            # Generate TypeScript types in api-client if linked
            if api_client is not None:
                api_client_src = find_api_client_src(api_client)
                if api_client_src:
                    generate_resource_types(api_client_src, resources)

    # Register in shell if --shell was provided
    if shell is not None and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        dev_port = cli_values.get("devPort") or file_values.get("devPort", "5001")
        menu_label = cli_values.get("menuLabel") or file_values.get("menuLabel", "") or title_case(project_name)
        pages_str = cli_values.get("pages") or file_values.get("pages", "[]")
        pages = parse_pages(pages_str)

        register_in_shell(
            shell_path=shell,
            app_name=project_name,
            dev_port=str(dev_port),
            menu_label=menu_label,
            pages=pages,
        )

    # Register ui-kit if --uikit was provided
    uikit_name = ""
    if uikit is not None and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        project_root = find_consumer_root(result, project_name)
        if project_root:
            uikit_name = register_uikit(uikit_path=uikit, consumer_root=project_root)

    # Generate ToastProvider for platform-shell (after uikit linking so we know the name)
    if template_info.name == "platform-shell" and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        project_root = find_consumer_root(result, project_name)
        if project_root:
            generate_toast_provider(project_root, has_uikit=bool(uikit_name), uikit_name=uikit_name)

    # Register in gateway if --gateway was provided
    if gateway is not None and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        register_in_gateway(gateway_path=gateway, service_name=project_name)

    # Link api-client if --api-client was provided
    if api_client is not None and not dry_run:
        project_name = cli_values.get("projectName") or file_values.get("projectName", "")
        project_root = find_consumer_root(result, project_name)
        if project_root:
            register_api_client(api_client_path=api_client, consumer_root=project_root)
