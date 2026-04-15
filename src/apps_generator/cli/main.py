"""Root CLI application."""

from __future__ import annotations

import typer

from apps_generator import __version__
from apps_generator.cli.generate import generate
from apps_generator.cli.docker_compose import docker_compose
from apps_generator.cli.repo import repo_app
from apps_generator.cli.templates_cmd import templates_app

app = typer.Typer(
    name="appgen",
    help="Generate full-stack projects from configurable templates.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.command()(generate)
app.command("docker-compose")(docker_compose)
app.add_typer(templates_app, name="templates", help="Manage and inspect templates.")
app.add_typer(repo_app, name="repo", help="Manage template repositories.")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"apps-generator {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit.", callback=version_callback, is_eager=True
    ),
) -> None:
    """Apps Generator — scaffold full-stack projects from templates."""


def run() -> None:
    app()
