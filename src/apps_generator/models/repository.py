"""Pydantic models for template repositories."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IndexEntry(BaseModel):
    """A single template entry in a repository index."""

    name: str
    version: str
    description: str = ""
    archive: str = ""
    checksum: str = ""
    tags: list[str] = Field(default_factory=list)


class RepositoryIndex(BaseModel):
    """Repository index.yaml model."""

    api_version: str = Field(default="v1", alias="apiVersion")
    templates: list[IndexEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class Repository(BaseModel):
    """A configured template repository."""

    name: str
    url: str = ""
    path: str = ""
    type: str = "remote"  # "remote" or "local"
