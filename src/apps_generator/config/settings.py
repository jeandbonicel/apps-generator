"""Configuration management — global config file and defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from apps_generator.models.repository import Repository

CONFIG_DIR = Path.home() / ".config" / "apps-generator"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
CACHE_DIR = Path.home() / ".cache" / "apps-generator"


def ensure_config_dir() -> None:
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Load global configuration from config.yaml."""
    if not CONFIG_FILE.exists():
        return {"defaults": {}, "repositories": [], "preferences": {}}

    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f)

    return data if isinstance(data, dict) else {"defaults": {}, "repositories": [], "preferences": {}}


def save_config(config: dict[str, Any]) -> None:
    """Save global configuration to config.yaml."""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_repositories() -> list[Repository]:
    """Get configured repositories."""
    config = load_config()
    repos_data = config.get("repositories", [])
    return [Repository.model_validate(r) for r in repos_data]


def add_repository(name: str, url: str, repo_type: str = "remote") -> None:
    """Add a repository to the configuration."""
    config = load_config()
    repos = config.get("repositories", [])

    # Remove existing with same name
    repos = [r for r in repos if r.get("name") != name]
    repos.append({"name": name, "url": url, "type": repo_type})

    config["repositories"] = repos
    save_config(config)


def remove_repository(name: str) -> bool:
    """Remove a repository. Returns True if found and removed."""
    config = load_config()
    repos = config.get("repositories", [])
    new_repos = [r for r in repos if r.get("name") != name]

    if len(new_repos) == len(repos):
        return False

    config["repositories"] = new_repos
    save_config(config)
    return True


def get_defaults() -> dict[str, Any]:
    """Get global default parameter values."""
    config = load_config()
    return config.get("defaults", {})
