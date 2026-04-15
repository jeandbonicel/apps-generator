"""Template packaging — create and extract tar.gz archives."""

from __future__ import annotations

import tarfile
from pathlib import Path


def package_template(template_dir: Path, output_path: Path) -> Path:
    """Package a template directory into a tar.gz archive."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(template_dir, arcname=template_dir.name)

    return output_path


def extract_template(archive_path: Path, output_dir: Path) -> Path:
    """Extract a template archive to a directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(output_dir, filter="data")

    return output_dir
