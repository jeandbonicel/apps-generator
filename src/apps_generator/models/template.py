"""Pydantic models for template manifests and metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Feature(BaseModel):
    """A toggleable feature in a template."""

    name: str
    description: str = ""
    default: bool = True


class DerivedParam(BaseModel):
    """Configuration for auto-derived parameter variants."""

    source: str
    variants: list[str] = Field(default_factory=lambda: ["camel", "pascal", "snake", "kebab"])


class HookConfig(BaseModel):
    """Post-generation hook configuration."""

    git_init: bool = Field(default=False, alias="git_init")
    message: str = ""


class Manifest(BaseModel):
    """Template manifest.yaml model."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    engine: str = "jinja2"
    required_params: list[str] = Field(default_factory=list, alias="required")
    derived: list[DerivedParam] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    hooks: HookConfig = Field(default_factory=HookConfig)
    exclude_patterns: list[str] = Field(default_factory=list, alias="exclude")

    model_config = {"populate_by_name": True}


class TemplateInfo(BaseModel):
    """Resolved template information."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    path: Path
    manifest: Manifest
    param_schema: dict[str, Any] = Field(default_factory=dict, alias="schema")
    defaults: dict[str, Any] = Field(default_factory=dict)
    source: str = "builtin"  # "builtin", "local", "remote"
