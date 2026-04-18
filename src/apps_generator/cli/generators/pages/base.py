"""Shared helpers used by multiple page-type emitters."""

from __future__ import annotations

from pathlib import Path

from apps_generator.utils.naming import pascal_case, title_case

from .registry import PageContext


def detect_lookup(field: dict, all_resources: list[str]) -> dict | None:
    """Auto-detect if a field should be a lookup to another resource.

    Matches patterns like ``dogName`` -> resource ``dog``, ``categoryId`` ->
    resource ``category``. Returns a lookup config dict or ``None``.
    """
    fname = field["name"]
    for res in all_resources:
        res_lower = res.lower()
        fname_lower = fname.lower()
        if fname_lower in (f"{res_lower}name", f"{res_lower}id", f"{res_lower}_name", f"{res_lower}_id"):
            value_field = "id" if fname_lower.endswith("id") else "name"
            return {"resource": res, "valueField": value_field, "labelField": "name"}
    return None


def page_target(page: dict, ctx: PageContext) -> tuple[Path, str, str]:
    """Return ``(dest, component_name, label)`` for a page config.

    ``dest`` is the absolute ``.tsx`` file path under
    ``ctx.project_root/src/routes``. ``component_name`` is PascalCase +
    ``"Page"`` suffix. ``label`` falls back to ``title_case(path)`` when not
    provided.
    """
    path = page.get("path", "")
    label = page.get("label", title_case(path))
    component = pascal_case(path.replace("/", "-")) + "Page"
    dest = ctx.project_root / "src" / "routes" / f"{component}.tsx"
    return dest, component, label
