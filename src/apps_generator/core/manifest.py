"""Manifest loader — reads and validates template manifest.yaml."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from apps_generator.models.template import Manifest, TemplateInfo


def load_manifest(template_dir: Path) -> Manifest:
    """Load manifest.yaml from a template directory."""
    manifest_path = template_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.yaml found in {template_dir}")

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    return Manifest.model_validate(data)


def load_schema(template_dir: Path) -> dict[str, Any]:
    """Load parameters-schema.json from a template directory."""
    schema_path = template_dir / "parameters-schema.json"
    if not schema_path.exists():
        return {}

    with open(schema_path) as f:
        return json.load(f)


def load_defaults(template_dir: Path) -> dict[str, Any]:
    """Load parameters-defaults.yaml from a template directory."""
    defaults_path = template_dir / "parameters-defaults.yaml"
    if not defaults_path.exists():
        return {}

    with open(defaults_path) as f:
        data = yaml.safe_load(f)

    return data if isinstance(data, dict) else {}


def load_template_info(template_dir: Path, source: str = "local") -> TemplateInfo:
    """Load complete template information from a directory."""
    manifest = load_manifest(template_dir)
    schema = load_schema(template_dir)
    defaults = load_defaults(template_dir)

    return TemplateInfo(
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        tags=manifest.tags,
        path=template_dir,
        manifest=manifest,
        schema=schema,
        defaults=defaults,
        source=source,
    )
