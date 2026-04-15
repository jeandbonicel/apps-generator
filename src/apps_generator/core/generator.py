"""Generator — orchestrates template rendering from manifest + params to output files."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from apps_generator.core.engine import (
    create_jinja_env,
    is_binary_file,
    render_file_content,
    render_filename,
)
from apps_generator.core.manifest import load_template_info
from apps_generator.core.parameters import build_context
from apps_generator.models.context import GenerationContext
from apps_generator.models.template import TemplateInfo
from apps_generator.utils.console import console


def generate(
    template_dir: Path,
    output_dir: Path,
    file_values: dict[str, Any] | None = None,
    cli_values: dict[str, str] | None = None,
    interactive: bool = True,
    dry_run: bool = False,
    force: bool = False,
    source: str = "local",
) -> Path:
    """Generate a project from a template directory.

    Returns the path to the generated project root.
    """
    template_info = load_template_info(template_dir, source=source)
    manifest = template_info.manifest

    console.print(f"\n[bold]Generating from template:[/bold] {manifest.name} v{manifest.version}")
    console.print(f"  {manifest.description}\n")

    # Build context
    context = build_context(
        defaults=template_info.defaults,
        file_values=file_values or {},
        cli_values=cli_values or {},
        schema=template_info.param_schema,
        derived_configs=[d.model_dump() for d in manifest.derived],
        features=[f.model_dump() for f in manifest.features],
        interactive=interactive,
    )

    template_vars = context.as_template_vars()
    env = create_jinja_env()

    files_dir = template_dir / "files"
    if not files_dir.exists():
        console.print("[red]Error:[/red] Template has no 'files/' directory.")
        raise SystemExit(1)

    # Resolve output directory
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir

    if output_dir.exists() and not force:
        console.print(f"[red]Error:[/red] Output directory already exists: {output_dir}")
        console.print("  Use --force to overwrite.")
        raise SystemExit(1)

    if dry_run:
        console.print("[yellow]Dry run — listing files that would be generated:[/yellow]\n")

    generated_files = _render_tree(
        src=files_dir,
        dst=output_dir,
        env=env,
        context=template_vars,
        template_info=template_info,
        dry_run=dry_run,
    )

    if dry_run:
        for f in generated_files:
            console.print(f"  {f}")
        console.print(f"\n[yellow]Would generate {len(generated_files)} files.[/yellow]")
        return output_dir

    console.print(f"\n[green]Generated {len(generated_files)} files in {output_dir}[/green]")

    # Post-generation hooks
    _run_hooks(manifest, output_dir, template_vars)

    return output_dir


def _render_tree(
    src: Path,
    dst: Path,
    env: Any,
    context: dict[str, Any],
    template_info: TemplateInfo,
    dry_run: bool = False,
) -> list[str]:
    """Walk the template file tree, rendering names and contents."""
    generated: list[str] = []
    conditions = _load_conditions(src)

    for item in sorted(src.iterdir()):
        if item.name == ".conditions.yaml":
            continue

        # Render the name
        rendered_name = render_filename(item.name, env, context)

        # Check conditions
        if not _check_condition(item.name, conditions, env, context):
            continue

        target = dst / rendered_name

        if item.is_dir():
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
            sub_files = _render_tree(item, target, env, context, template_info, dry_run)
            generated.extend(sub_files)
        else:
            rel_path = str(target)
            if dry_run:
                generated.append(rel_path)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            if is_binary_file(item):
                shutil.copy2(item, target)
            else:
                try:
                    content = item.read_text(encoding="utf-8")
                    rendered = render_file_content(content, env, context)
                    target.write_text(rendered, encoding="utf-8")
                except UnicodeDecodeError:
                    shutil.copy2(item, target)

            # Preserve executable permission
            if os.access(item, os.X_OK):
                target.chmod(target.stat().st_mode | 0o111)

            generated.append(rel_path)

    return generated


def _load_conditions(directory: Path) -> dict[str, str]:
    """Load .conditions.yaml from a directory if it exists."""
    conditions_file = directory / ".conditions.yaml"
    if not conditions_file.exists():
        return {}

    with open(conditions_file) as f:
        data = yaml.safe_load(f)

    return data if isinstance(data, dict) else {}


def _check_condition(
    name: str,
    conditions: dict[str, str],
    env: Any,
    context: dict[str, Any],
) -> bool:
    """Check if a file/directory should be included based on conditions."""
    if name not in conditions:
        return True

    expr = conditions[name]
    try:
        template = env.from_string(f"{{% if {expr} %}}yes{{% endif %}}")
        result = template.render(context)
        return result.strip() == "yes"
    except Exception:
        return True


def _run_hooks(manifest: Any, output_dir: Path, context: dict[str, Any]) -> None:
    """Run post-generation hooks."""
    hooks = manifest.hooks

    if hooks.git_init:
        try:
            subprocess.run(
                ["git", "init"],
                cwd=output_dir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "add", "."],
                cwd=output_dir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial project scaffold"],
                cwd=output_dir,
                capture_output=True,
                check=True,
            )
            console.print("[dim]Initialized git repository with initial commit.[/dim]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[dim]Git init skipped (git not available or failed).[/dim]")

    if hooks.message:
        env = create_jinja_env()
        msg = render_file_content(hooks.message, env, context)
        console.print(f"\n[bold cyan]{msg}[/bold cyan]")
