"""Templates subcommands — list, describe, validate, package."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from apps_generator.templates.registry import list_templates, resolve_template
from apps_generator.templates.packaging import package_template
from apps_generator.utils.console import console

templates_app = typer.Typer(no_args_is_help=True)


@templates_app.command("list")
def list_cmd(
    repo: Optional[str] = typer.Option(None, "--repo", help="Filter by repository name."),
) -> None:
    """List all available templates."""
    templates = list_templates()

    if repo:
        templates = [t for t in templates if t.source == repo]

    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return

    table = Table(title="Available Templates")
    table.add_column("Name", style="bold cyan")
    table.add_column("Version")
    table.add_column("Description")
    table.add_column("Source", style="dim")
    table.add_column("Tags", style="dim")

    for t in templates:
        table.add_row(
            t.name,
            t.version,
            t.description,
            t.source,
            ", ".join(t.tags),
        )

    console.print(table)


@templates_app.command("describe")
def describe(
    template: str = typer.Argument(help="Template name or path."),
) -> None:
    """Show detailed information about a template."""
    info = resolve_template(template)
    if not info:
        console.print(f"[red]Error:[/red] Template '{template}' not found.")
        raise typer.Exit(1)

    console.print(f"\n[bold]{info.name}[/bold] v{info.version}")
    console.print(f"  {info.description}")
    console.print(f"  Source: {info.source}")
    if info.tags:
        console.print(f"  Tags: {', '.join(info.tags)}")

    # Show parameters
    schema = info.param_schema
    if schema:
        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        console.print("\n[bold]Parameters:[/bold]")
        table = Table(show_header=True)
        table.add_column("Name", style="bold")
        table.add_column("Type")
        table.add_column("Default")
        table.add_column("Required", justify="center")
        table.add_column("Description")

        for name, prop in props.items():
            ptype = prop.get("type", "string")
            default = prop.get("default", "")
            desc = prop.get("description", "")
            is_required = "yes" if name in required else ""

            table.add_row(name, ptype, str(default) if default else "", is_required, desc)

        console.print(table)

    # Show features
    if info.manifest.features:
        console.print("\n[bold]Features:[/bold]")
        for f in info.manifest.features:
            status = "[green]on[/green]" if f.default else "[dim]off[/dim]"
            console.print(f"  {status}  {f.name} — {f.description}")

    console.print()


@templates_app.command("validate")
def validate(
    path: Path = typer.Argument(help="Path to template directory."),
) -> None:
    """Validate a template directory structure."""
    errors = []

    if not path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {path}")
        raise typer.Exit(1)

    if not (path / "manifest.yaml").exists():
        errors.append("Missing manifest.yaml")
    if not (path / "parameters-schema.json").exists():
        errors.append("Missing parameters-schema.json")
    if not (path / "parameters-defaults.yaml").exists():
        errors.append("Missing parameters-defaults.yaml")
    if not (path / "files").exists() or not (path / "files").is_dir():
        errors.append("Missing files/ directory")

    if errors:
        console.print("[red]Validation failed:[/red]")
        for e in errors:
            console.print(f"  - {e}")
        raise typer.Exit(1)

    # Try loading the template
    try:
        from apps_generator.core.manifest import load_template_info
        load_template_info(path)
        console.print(f"[green]Template at {path} is valid.[/green]")
    except Exception as e:
        console.print(f"[red]Validation failed:[/red] {e}")
        raise typer.Exit(1)


@templates_app.command("package")
def package(
    path: Path = typer.Argument(help="Path to template directory."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output archive path."),
) -> None:
    """Package a template into a tar.gz archive."""
    if not path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {path}")
        raise typer.Exit(1)

    if output is None:
        output = Path.cwd() / f"{path.name}.tar.gz"

    result = package_template(path, output)
    console.print(f"[green]Packaged template to {result}[/green]")
