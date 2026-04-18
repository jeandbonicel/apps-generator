"""``tree`` page type — hierarchical view of a self-referencing resource.

Fetches a flat paginated list from the resource's collection endpoint,
builds a tree from records whose ``parentId`` points to another record of
the same resource, and renders it with `react-arborist`_. Nodes are
collapsible, keyboard-navigable, and virtualized — suitable for
department hierarchies, folder structures, org charts, category trees.

The resource must expose:

* ``id`` — unique identifier (always present via ``TenantAwareEntity``)
* ``parentId`` — nullable reference to another record of the same resource.
  Records with ``parentId == null`` are roots.

Clicking a node navigates to ``./view?id={id}`` by convention, so that a
co-located ``detail`` page of the same resource opens that record. The
frontend-app's path-based routing (no URL params) makes this the natural
link target.

.. _react-arborist: https://github.com/brimdata/react-arborist
"""

from __future__ import annotations

from apps_generator.utils.naming import camel_case, pascal_case

from .base import page_target
from .registry import PageContext, PageTypeInfo, get_registry


def emit_tree(page: dict, ctx: PageContext) -> None:
    """Generate a tree page — flat-to-nested build + react-arborist Tree."""
    dest, component, label = page_target(page, ctx)
    resource = page.get("resource", "")
    fields = page.get("fields", [])
    entity = pascal_case(resource)
    _api_pkg = ctx.api_client_name or "my-api-client"
    ui = ctx.uikit_name

    # Pick the first string field as the node label; fall back to the record id
    # when no string field is configured.
    label_field = next((f for f in fields if f.get("type", "string") == "string"), None)
    label_fname = camel_case(label_field["name"]) if label_field else "id"

    # ui-kit imports — Tree pages lean on Card for the outer chrome; the
    # tree itself is react-arborist regardless of --uikit.
    if ui:
        ui_import = f'import {{ Card, CardContent, CardHeader, CardTitle }} from "{ui}";\n'
    else:
        ui_import = ""

    # Node renderer — we want the caret to reflect open/closed state, the label
    # to show the chosen field, and clicking a leaf to navigate to the detail
    # page of that record. Non-internal (leaf) nodes are clickable; internal
    # nodes toggle open/close, matching react-arborist defaults.
    node_renderer = (
        "  const Node = ({ node, style, dragHandle }: NodeRendererProps<TreeNode>) => (\n"
        "    <div\n"
        "      ref={dragHandle}\n"
        "      style={style}\n"
        '      className="flex items-center gap-2 px-2 rounded-sm cursor-pointer hover:bg-accent"\n'
        "      onClick={() => {\n"
        "        if (node.isInternal) node.toggle();\n"
        "        else window.location.search = `?id=${node.id}`;\n"
        "      }}\n"
        "    >\n"
        '      <span className="w-4 text-muted-foreground">\n'
        '        {node.isInternal ? (node.isOpen ? "▾" : "▸") : "•"}\n'
        "      </span>\n"
        "      <span>{node.data.label}</span>\n"
        "    </div>\n"
        "  );\n"
    )

    # Tree wrapper — ui-kit branch gets a Card; plain branch gets a bordered div.
    if ui:
        wrapper_open = (
            f"      <Card>\n"
            f"        <CardHeader>\n"
            f"          <CardTitle>{label} ({{items.length}})</CardTitle>\n"
            f"        </CardHeader>\n"
            f'        <CardContent className="p-0">'
        )
        wrapper_close = "        </CardContent>\n      </Card>"
    else:
        wrapper_open = (
            f'      <h1 className="text-2xl font-bold tracking-tight mb-4">{label} ({{items.length}})</h1>\n'
            f'      <div className="rounded-lg border">'
        )
        wrapper_close = "      </div>"

    # Empty state spans the tree container.
    empty_state = '          <p className="text-center text-muted-foreground py-8">{t("noDataFound")}</p>'

    dest.write_text(
        f'import {{ useMemo }} from "react";\n'
        f'import {{ useTranslation }} from "react-i18next";\n'
        f'import {{ useQuery }} from "@tanstack/react-query";\n'
        f'import {{ Tree, type NodeRendererProps }} from "react-arborist";\n'
        f'import {{ useApiClient }} from "{_api_pkg}/react";\n'
        f'import type {{ {entity}, PageResponse }} from "{_api_pkg}";\n'
        f"{ui_import}"
        f"\n"
        f"interface TreeNode {{\n"
        f"  id: string;\n"
        f"  label: string;\n"
        f"  children?: TreeNode[];\n"
        f"}}\n"
        f"\n"
        f"/**\n"
        f" * Build a nested tree from a flat list of records using ``parentId``.\n"
        f" * Records whose parent isn't in the list are treated as roots so the\n"
        f" * view degrades gracefully if pagination cuts off an ancestor.\n"
        f" */\n"
        f"function buildTree(items: {entity}[]): TreeNode[] {{\n"
        f"  const byId = new Map<string, TreeNode>();\n"
        f"  for (const item of items) {{\n"
        f"    byId.set(String(item.id), {{\n"
        f"      id: String(item.id),\n"
        f"      label: String(item.{label_fname} ?? item.id),\n"
        f"      children: [],\n"
        f"    }});\n"
        f"  }}\n"
        f"  const roots: TreeNode[] = [];\n"
        f"  for (const item of items) {{\n"
        f"    const node = byId.get(String(item.id))!;\n"
        f"    const parentId = (item as unknown as {{ parentId?: string | number | null }}).parentId;\n"
        f"    const parent = parentId != null ? byId.get(String(parentId)) : undefined;\n"
        f"    if (parent) parent.children!.push(node);\n"
        f"    else roots.push(node);\n"
        f"  }}\n"
        f"  return roots;\n"
        f"}}\n"
        f"\n"
        f"export function {component}() {{\n"
        f"  const {{ t }} = useTranslation();\n"
        f"  const api = useApiClient();\n"
        f"\n"
        f"  const {{ data, isLoading, error }} = useQuery<PageResponse<{entity}>>({{  \n"
        f'    queryKey: ["{resource}", "tree"],\n'
        f'    queryFn: () => api.get<PageResponse<{entity}>>("/{resource}", '
        f'{{ params: {{ page: "0", size: "1000" }} }}),\n'
        f"  }});\n"
        f"\n"
        f"  const items = data?.content ?? [];\n"
        f"  const treeData = useMemo(() => buildTree(items), [items]);\n"
        f"\n"
        f"{node_renderer}"
        f"\n"
        f'  if (isLoading) return <p className="text-muted-foreground">{{t("loading")}}</p>;\n'
        f'  if (error) return <p className="text-destructive">'
        f'{{t("failedToLoad")}}: {{(error as Error).message}}</p>;\n'
        f"\n"
        f"  return (\n"
        f'    <div className="space-y-4">\n'
        f"{wrapper_open}\n"
        f"          {{items.length === 0 ? (\n"
        f"{empty_state}\n"
        f"          ) : (\n"
        f"            <Tree<TreeNode>\n"
        f"              data={{treeData}}\n"
        f"              openByDefault={{false}}\n"
        f"              width={{600}}\n"
        f"              height={{500}}\n"
        f"              indent={{24}}\n"
        f"              rowHeight={{32}}\n"
        f"            >\n"
        f"              {{Node}}\n"
        f"            </Tree>\n"
        f"          )}}\n"
        f"{wrapper_close}\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


PAGE_TYPE = PageTypeInfo(
    name="tree",
    description="Hierarchical view for a self-referencing resource — flat-to-nested build by parentId, rendered via react-arborist.",
    emit=emit_tree,
    required_fields=["resource"],
)

get_registry().register(PAGE_TYPE)
