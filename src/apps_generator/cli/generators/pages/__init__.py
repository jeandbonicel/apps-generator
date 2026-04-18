"""Page generation package.

Public API is kept identical to the pre-refactor ``pages.py`` module so that
existing callers (``cli/generate.py``, tests) work unchanged:

* :func:`parse_pages`
* :func:`find_project_root`
* :func:`generate_page_components`

The generation itself is dispatched through a :class:`PageTypeRegistry`
populated by the built-in type modules imported below. Plugins can register
additional types via the ``appgen.page_types`` entry point group (Phase 3).
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

from apps_generator.utils.console import console
from apps_generator.utils.naming import pascal_case, title_case

from .registry import PageContext, PageTypeInfo, PageTypeRegistry, get_registry

# Import every built-in page-type module so each self-registers its PAGE_TYPE.
# Modules are named ``*_type`` to avoid shadowing Python builtins (notably
# ``list``) via the package-attribute binding that submodule imports trigger.
# Adding a new built-in is as simple as dropping a ``<name>_type.py`` module
# in this package.
_BUILTIN_TYPES = ("list_type", "form_type", "dashboard_type", "detail_type", "grid_type")
for _name in _BUILTIN_TYPES:
    import_module(f"{__name__}.{_name}")


__all__ = [
    "parse_pages",
    "find_project_root",
    "generate_page_components",
    "PageContext",
    "PageTypeInfo",
    "PageTypeRegistry",
    "get_registry",
]


def parse_pages(pages_str: str) -> list[dict]:
    """Parse pages JSON string into a list of page configs."""
    if not pages_str or pages_str == "[]":
        return []
    try:
        pages = json.loads(pages_str)
        if isinstance(pages, list):
            return pages
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def find_project_root(output_dir: Path, project_name: str) -> Path | None:
    """Find the generated project root directory."""
    candidate = output_dir / project_name
    if (candidate / "src" / "pages.ts").exists():
        return candidate
    if (output_dir / "src" / "pages.ts").exists():
        return output_dir
    return None


def _write_placeholder_page(page_file: Path, component_name: str, label: str, project_name: str) -> None:
    """Write a simple placeholder .tsx when a page has no matching type/resource."""
    page_file.write_text(
        f"export function {component_name}() {{\n"
        f"  return (\n"
        f'    <div className="p-6">\n'
        f'      <h1 className="text-2xl font-bold mb-4">{label}</h1>\n'
        f'      <p className="text-gray-600">This is the {label} page of {title_case(project_name)}.</p>\n'
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


def generate_page_components(
    project_root: Path,
    pages: list[dict],
    project_name: str,
    uikit_name: str = "",
    api_client_name: str = "",
    all_resources: list[str] | None = None,
) -> None:
    """Generate individual page component files and update pages.ts registry.

    Pages with ``resource`` + ``type`` fields dispatch to the matching page-type
    emitter (``list``, ``form``, ``dashboard``, or any plugin-registered type).
    Pages without both of those keys fall back to a simple placeholder
    component.

    When ``uikit_name`` is provided, generated pages import shadcn components
    (Button, Input, Table, Card, etc.) from the ui-kit package.
    """
    routes_dir = project_root / "src" / "routes"
    routes_dir.mkdir(parents=True, exist_ok=True)

    registry = get_registry()
    ctx = PageContext(
        project_root=project_root,
        project_name=project_name,
        uikit_name=uikit_name,
        api_client_name=api_client_name,
        all_resources=list(all_resources) if all_resources else [],
    )

    imports: list[str] = ['import type { ComponentType } from "react";']
    imports.append('import { HomePage } from "./routes/HomePage";')
    registry_entries: list[str] = ["  default: HomePage,"]

    for page in pages:
        path = page.get("path", "")
        label = page.get("label", title_case(path))
        component_name = pascal_case(path.replace("/", "-")) + "Page"
        resource = page.get("resource")
        page_type = page.get("type")

        page_file = routes_dir / f"{component_name}.tsx"
        if not page_file.exists():
            info = registry.get(page_type) if (page_type and resource) else None
            if info is not None:
                info.emit(page, ctx)
            else:
                _write_placeholder_page(page_file, component_name, label, project_name)
            console.print(f"  Created page: src/routes/{component_name}.tsx")

        imports.append(f'import {{ {component_name} }} from "./routes/{component_name}";')
        registry_entries.append(f'  "{path}": {component_name},')

    # Write updated pages.ts
    pages_ts = project_root / "src" / "pages.ts"
    content = "\n".join(imports)
    content += "\n\nexport const pages: Record<string, ComponentType> = {\n"
    content += "\n".join(registry_entries)
    content += "\n};\n"
    pages_ts.write_text(content)
    console.print(f"  Updated: src/pages.ts ({len(pages)} pages registered)")
