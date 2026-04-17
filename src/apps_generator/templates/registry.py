"""Template registry — discover templates from built-in and configured repositories."""

from __future__ import annotations

from pathlib import Path

from apps_generator.core.manifest import load_template_info
from apps_generator.models.template import TemplateInfo

BUILTIN_DIR = Path(__file__).parent / "builtin"


def get_builtin_templates() -> list[TemplateInfo]:
    """Discover all built-in templates."""
    templates: list[TemplateInfo] = []

    if not BUILTIN_DIR.exists():
        return templates

    for child in sorted(BUILTIN_DIR.iterdir()):
        if child.is_dir() and (child / "manifest.yaml").exists():
            try:
                info = load_template_info(child, source="builtin")
                templates.append(info)
            except Exception:
                pass

    return templates


def resolve_template(name: str) -> TemplateInfo | None:
    """Resolve a template by name.

    Checks built-in templates first, then configured repositories.
    Name can be:
      - Simple name: 'api-domain' (searches built-in)
      - Local path: '/path/to/template' or './my-template'
      - Repo reference: 'repo-name/template-name[:version]'
    """
    # Check if it's a local path
    local_path = Path(name)
    if local_path.exists() and (local_path / "manifest.yaml").exists():
        return load_template_info(local_path, source="local")

    # Check built-in templates
    for template in get_builtin_templates():
        if template.name == name:
            return template

    # TODO: Check configured repositories
    return None


def list_templates() -> list[TemplateInfo]:
    """List all available templates from all sources."""
    templates = get_builtin_templates()
    # TODO: Add templates from configured repositories
    return templates
