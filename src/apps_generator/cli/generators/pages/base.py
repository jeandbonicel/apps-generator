"""Shared helpers used by multiple page-type emitters."""

from __future__ import annotations

from pathlib import Path

from apps_generator.utils.naming import pascal_case, title_case

from .registry import PageContext


def detect_lookup(
    field: dict,
    all_resources: list[str],
    *,
    current_resource: str | None = None,
) -> dict | None:
    """Auto-detect if a field should be a lookup to another resource.

    Two paths, in order of preference:

    1. **Explicit** — ``type: "reference"`` with a ``target`` naming another
       resource. This is the first-class path: the caller has declared the
       FK intent, so we honour it even when ``target == current_resource``
       (self-references are the whole point of tree-style hierarchies).
    2. **Heuristic** — name-based match for configs without an explicit
       reference type: ``dogName`` → resource ``dog``, ``categoryId`` →
       resource ``category``. ``current_resource`` is skipped here to
       avoid nonsense self-matches on fields that happen to share a name
       prefix with their own resource.

    Returns a lookup config dict or ``None``.
    """
    if field.get("type") == "reference":
        target = field.get("target")
        if target and target in all_resources:
            # FK id lives on the entity; label picks the first string-ish field
            # of the target by convention (``name``). Users can override via
            # ``lookup.labelField`` in the page config if they've got a
            # different display field.
            return {"resource": target, "valueField": "id", "labelField": "name"}
        return None

    fname = field["name"]
    for res in all_resources:
        if current_resource is not None and res == current_resource:
            continue
        res_lower = res.lower()
        fname_lower = fname.lower()
        if fname_lower in (f"{res_lower}name", f"{res_lower}id", f"{res_lower}_name", f"{res_lower}_id"):
            value_field = "id" if fname_lower.endswith("id") else "name"
            return {"resource": res, "valueField": value_field, "labelField": "name"}
    return None


def normalize_row_link(raw: str | None) -> str | None:
    """Coerce a page-config ``rowLink`` value into a leading-slash sub-path.

    The MFE router's ``navigateTo`` takes a path rooted at the MFE's base
    path; ``/detail`` and ``detail`` both resolve to the same place, but
    normalising here keeps the emitted JSX consistent across page types.
    Returns ``None`` when the caller didn't opt in.
    """
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw:
        return None
    return raw if raw.startswith("/") else "/" + raw


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
