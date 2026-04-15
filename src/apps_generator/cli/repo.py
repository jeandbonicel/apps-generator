"""Repository subcommands — add, remove, list, update."""

from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from apps_generator.config.settings import add_repository, get_repositories, remove_repository
from apps_generator.utils.console import console

repo_app = typer.Typer(no_args_is_help=True)


@repo_app.command("add")
def add(
    name: str = typer.Argument(help="Repository name."),
    url: str = typer.Argument(help="Repository URL or local path."),
    repo_type: str = typer.Option("remote", "--type", help="Repository type: remote or local."),
) -> None:
    """Add a template repository."""
    add_repository(name, url, repo_type)
    console.print(f"[green]Added repository '{name}' -> {url}[/green]")


@repo_app.command("remove")
def remove(
    name: str = typer.Argument(help="Repository name to remove."),
) -> None:
    """Remove a template repository."""
    if remove_repository(name):
        console.print(f"[green]Removed repository '{name}'.[/green]")
    else:
        console.print(f"[yellow]Repository '{name}' not found.[/yellow]")


@repo_app.command("list")
def list_cmd() -> None:
    """List configured repositories."""
    repos = get_repositories()

    if not repos:
        console.print("[yellow]No repositories configured.[/yellow]")
        console.print("  Add one with: [bold]appgen repo add <name> <url>[/bold]")
        return

    table = Table(title="Configured Repositories")
    table.add_column("Name", style="bold cyan")
    table.add_column("URL")
    table.add_column("Type", style="dim")

    for r in repos:
        table.add_row(r.name, r.url or r.path, r.type)

    console.print(table)


@repo_app.command("update")
def update(
    name: Optional[str] = typer.Argument(None, help="Repository name to update. Updates all if omitted."),
) -> None:
    """Update repository index from remote."""
    console.print("[yellow]Repository update not yet implemented for remote repos.[/yellow]")
