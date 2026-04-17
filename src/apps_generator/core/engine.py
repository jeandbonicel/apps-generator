"""Jinja2 template engine — renders file contents and filenames."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined

from apps_generator.utils import naming

# File extensions that should never be processed by Jinja2
BINARY_EXTENSIONS = frozenset(
    {
        ".jar",
        ".class",
        ".war",
        ".ear",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".svg",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".pyc",
        ".pyo",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wav",
        ".db",
        ".sqlite",
    }
)

# Pattern for filename variables: __variableName__ or __variable|filter__
FILENAME_VAR_PATTERN = re.compile(r"__([a-zA-Z_][a-zA-Z0-9_]*(?:\|[a-zA-Z_]+)?)__")


def create_jinja_env() -> Environment:
    """Create a Jinja2 environment with custom filters and settings."""
    env = Environment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
    )

    env.filters["camel_case"] = naming.camel_case
    env.filters["pascal_case"] = naming.pascal_case
    env.filters["snake_case"] = naming.snake_case
    env.filters["kebab_case"] = naming.kebab_case
    env.filters["upper_snake_case"] = naming.upper_snake_case
    env.filters["package_to_path"] = naming.package_to_path
    env.filters["capitalize_first"] = naming.capitalize_first
    env.filters["title_case"] = naming.title_case

    return env


def is_binary_file(path: Path) -> bool:
    """Check if a file is binary based on extension or content."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except OSError:
        return True


def render_filename(name: str, env: Environment, context: dict[str, Any]) -> str:
    """Render a filename by replacing __var__ and __var|filter__ patterns.

    Examples:
        __projectName__ -> order-service
        __basePackage|package_to_path__ -> com/example/app
    """

    def replace_match(m: re.Match) -> str:
        expr = m.group(1)
        # Convert pipe to Jinja2 filter syntax
        if "|" in expr:
            var, filt = expr.split("|", 1)
            template_str = f"{{{{ {var} | {filt} }}}}"
        else:
            template_str = f"{{{{ {expr} }}}}"
        return env.from_string(template_str).render(context)

    return FILENAME_VAR_PATTERN.sub(replace_match, name)


def render_file_content(content: str, env: Environment, context: dict[str, Any]) -> str:
    """Render file content through Jinja2."""
    template = env.from_string(content)
    return template.render(context)
