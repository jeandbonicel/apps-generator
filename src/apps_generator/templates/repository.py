"""Repository management — fetch remote template indexes and archives."""

from __future__ import annotations

from pathlib import Path

from apps_generator.config.settings import CACHE_DIR


def get_cache_path(repo_name: str) -> Path:
    """Get the cache directory for a repository."""
    path = CACHE_DIR / repo_name
    path.mkdir(parents=True, exist_ok=True)
    return path
