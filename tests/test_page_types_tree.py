"""Tests for the ``tree`` page type — hierarchical view via react-arborist."""

from __future__ import annotations

from pathlib import Path

from apps_generator.cli.generators.pages import (
    generate_page_components,
    get_registry,
)


# ── Registration ───────────────────────────────────────────────────────────


def test_tree_type_is_registered() -> None:
    info = get_registry().get("tree")
    assert info is not None
    assert info.source == "builtin"
    assert info.required_fields == ["resource"]
    assert info.description


# ── Emitter fixture ────────────────────────────────────────────────────────


def _generate_department_tree(tmp_path: Path, *, uikit: str = "my-ui", fields: list[dict] | None = None) -> str:
    project_root = tmp_path / "app"
    (project_root / "src" / "routes").mkdir(parents=True)
    page = {
        "path": "org",
        "label": "Org Chart",
        "resource": "department",
        "type": "tree",
        "fields": fields
        if fields is not None
        else [
            {"name": "name", "type": "string"},
            {"name": "head", "type": "string"},
        ],
    }
    generate_page_components(
        project_root=project_root,
        pages=[page],
        project_name="demo",
        uikit_name=uikit,
        api_client_name="my-api",
    )
    return (project_root / "src" / "routes" / "OrgPage.tsx").read_text()


# ── Data fetch ─────────────────────────────────────────────────────────────


def test_tree_fetches_flat_list_via_use_query(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path)
    assert "useQuery<PageResponse<Department>>" in tsx
    assert '"/department"' in tsx
    # Uses a generous page size so a single call typically returns the whole tree
    assert 'size: "1000"' in tsx
    # Distinct queryKey so the tree doesn't reuse the list page's cached slice
    assert '"department", "tree"' in tsx


# ── Flat-to-nested builder ─────────────────────────────────────────────────


def test_tree_builds_nested_structure_by_parent_id(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path)
    # Indexed by id for O(1) parent lookup
    assert "byId.set(String(item.id)" in tsx
    # Dangling children (parent not in result) fall through as roots
    assert "if (parent) parent.children!.push(node);" in tsx
    assert "else roots.push(node);" in tsx
    # buildTree is wrapped in useMemo so it doesn't rerun on unrelated state changes
    assert "useMemo(() => buildTree(items)" in tsx


def test_tree_labels_nodes_with_first_string_field(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path)
    assert "label: String(item.name ?? item.id)" in tsx


def test_tree_falls_back_to_id_when_no_string_field(tmp_path: Path) -> None:
    """If the config has no string field, the node label is the id (still navigable)."""
    tsx = _generate_department_tree(
        tmp_path,
        fields=[{"name": "sortOrder", "type": "integer"}],
    )
    assert "label: String(item.id ?? item.id)" in tsx


# ── Rendering ──────────────────────────────────────────────────────────────


def test_tree_imports_react_arborist(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path)
    assert 'import { Tree, type NodeRendererProps } from "react-arborist"' in tsx
    # And is actually rendered
    assert "<Tree<TreeNode>" in tsx


def test_tree_configures_arborist_props(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path)
    assert "openByDefault={false}" in tsx
    assert "width={600}" in tsx
    assert "height={500}" in tsx
    assert "indent={24}" in tsx
    assert "rowHeight={32}" in tsx


def test_tree_node_renderer_toggles_or_navigates(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path)
    # Internal node click toggles open/closed
    assert "if (node.isInternal) node.toggle()" in tsx
    # Leaf click navigates to the detail page via the ?id= convention
    assert "else window.location.search = `?id=${node.id}`" in tsx
    # Caret reflects open/closed state
    assert '{node.isInternal ? (node.isOpen ? "▾" : "▸") : "•"}' in tsx


def test_tree_shows_empty_and_error_states(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path)
    assert 't("noDataFound")' in tsx
    assert 't("loading")' in tsx
    assert 't("failedToLoad")' in tsx


# ── Wrappers ───────────────────────────────────────────────────────────────


def test_tree_uikit_branch_uses_card_wrapper(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path, uikit="my-ui")
    assert 'from "my-ui"' in tsx
    for sym in ["Card", "CardContent", "CardHeader", "CardTitle"]:
        assert sym in tsx, f"missing ui-kit import: {sym}"
    # CardTitle shows the total count
    assert "<CardTitle>Org Chart ({items.length})</CardTitle>" in tsx


def test_tree_plain_branch_uses_raw_heading_and_bordered_div(tmp_path: Path) -> None:
    tsx = _generate_department_tree(tmp_path, uikit="")
    # No ui-kit imports
    assert "Card" not in tsx
    # Plain wrapper still has the title + count
    assert "Org Chart ({items.length})" in tsx
    assert '<div className="rounded-lg border">' in tsx
