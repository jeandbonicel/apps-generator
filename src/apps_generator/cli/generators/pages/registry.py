"""Registry mapping page-type names to emitter metadata.

Built-in page types (``list``, ``form``, ``dashboard``) self-register at import
time. Plugins can register additional types via the ``appgen.page_types`` entry
point group (added in Phase 3 of the refactor).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class PageContext:
    """Runtime context passed to every page-type emitter.

    Values here are shared across all pages in a single generation run.
    Per-page data comes from the page config dict passed alongside.
    """

    project_root: Path
    project_name: str
    uikit_name: str = ""
    api_client_name: str = ""
    all_resources: list[str] = field(default_factory=list)


EmitterFn = Callable[[dict, PageContext], None]
"""Emitter signature: ``(page_config, context) -> None``.

The emitter reads ``path``, ``label``, ``resource``, ``fields`` etc. from the
page config and writes a single ``.tsx`` file under
``ctx.project_root / "src" / "routes"``.
"""


@dataclass
class PageTypeInfo:
    """Metadata + emitter for a registered page type."""

    name: str
    description: str
    emit: EmitterFn
    required_fields: list[str] = field(default_factory=list)
    source: str = "builtin"


class PageTypeRegistry:
    """Maps type name -> :class:`PageTypeInfo`."""

    def __init__(self) -> None:
        self._types: dict[str, PageTypeInfo] = {}

    def register(self, info: PageTypeInfo) -> None:
        if info.name in self._types:
            raise ValueError(f"Page type already registered: {info.name!r}")
        self._types[info.name] = info

    def get(self, name: str | None) -> PageTypeInfo | None:
        if not name:
            return None
        return self._types.get(name)

    def list_all(self) -> list[PageTypeInfo]:
        return sorted(self._types.values(), key=lambda i: i.name)


_registry = PageTypeRegistry()


def get_registry() -> PageTypeRegistry:
    """Return the process-wide page type registry."""
    return _registry
