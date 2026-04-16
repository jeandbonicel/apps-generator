"""Tests for TypeScript type generation and data-aware frontend pages."""

import json
from pathlib import Path

from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template
from apps_generator.cli.generators.resources import parse_resources
from apps_generator.cli.generators.types import generate_resource_types
from apps_generator.cli.generators.pages import (
    parse_pages,
    find_project_root,
    generate_page_components,
)


# ── TypeScript type generation ───────────────────────────────────────────────

def _setup_api_client(tmp_path: Path) -> Path:
    """Generate an api-client and return its src/ directory."""
    template = resolve_template("api-client")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "api-client",
        cli_values={"projectName": "my-api-client"},
        interactive=False,
    )
    return result / "my-api-client" / "src"


def test_generate_resource_types_creates_files(tmp_path: Path):
    api_src = _setup_api_client(tmp_path)
    resources = parse_resources('[{"name":"product","fields":[{"name":"name","type":"string","required":true},{"name":"price","type":"decimal","required":true}]}]')

    generate_resource_types(api_src, resources)

    assert (api_src / "resources" / "product.ts").exists()
    assert (api_src / "resources" / "index.ts").exists()


def test_generate_resource_types_content(tmp_path: Path):
    api_src = _setup_api_client(tmp_path)
    resources = parse_resources(json.dumps([{
        "name": "product",
        "fields": [
            {"name": "name", "type": "string", "required": True},
            {"name": "description", "type": "text"},
            {"name": "price", "type": "decimal", "required": True},
            {"name": "active", "type": "boolean"},
        ]
    }]))

    generate_resource_types(api_src, resources)

    ts = (api_src / "resources" / "product.ts").read_text()

    # Response interface
    assert "export interface Product {" in ts
    assert "  id: number;" in ts
    assert "  tenantId: string;" in ts
    assert "  name: string;" in ts
    assert "  description: string | null;" in ts  # optional → nullable
    assert "  price: number;" in ts                # required → non-null
    assert "  active: boolean | null;" in ts       # optional boolean
    assert "  createdAt: string;" in ts
    assert "  updatedAt: string;" in ts

    # Create request
    assert "export interface CreateProductRequest {" in ts
    assert "  name: string;" in ts       # required → non-optional
    assert "  description?: string;" in ts  # optional → ?
    assert "  price: number;" in ts
    assert "  active?: boolean;" in ts

    # PageResponse generic
    assert "export interface PageResponse<T> {" in ts
    assert "  content: T[];" in ts


def test_generate_resource_types_barrel_export(tmp_path: Path):
    api_src = _setup_api_client(tmp_path)
    resources = parse_resources('[{"name":"product","fields":[]},{"name":"order","fields":[]}]')

    generate_resource_types(api_src, resources)

    barrel = (api_src / "resources" / "index.ts").read_text()
    assert 'export * from "./product";' in barrel
    assert 'export * from "./order";' in barrel


def test_generate_resource_types_updates_main_index(tmp_path: Path):
    api_src = _setup_api_client(tmp_path)
    resources = parse_resources('[{"name":"product","fields":[]}]')

    generate_resource_types(api_src, resources)

    main_index = (api_src / "index.ts").read_text()
    assert 'export * from "./resources";' in main_index


def test_generate_resource_types_all_field_types(tmp_path: Path):
    api_src = _setup_api_client(tmp_path)
    resources = parse_resources(json.dumps([{
        "name": "everything",
        "fields": [
            {"name": "s", "type": "string", "required": True},
            {"name": "t", "type": "text"},
            {"name": "i", "type": "integer"},
            {"name": "l", "type": "long"},
            {"name": "d", "type": "decimal", "required": True},
            {"name": "b", "type": "boolean"},
            {"name": "dt", "type": "date"},
            {"name": "dtt", "type": "datetime"},
        ]
    }]))

    generate_resource_types(api_src, resources)

    ts = (api_src / "resources" / "everything.ts").read_text()
    assert "  s: string;" in ts       # required string
    assert "  t: string | null;" in ts  # optional text → nullable
    assert "  i: number | null;" in ts  # optional int → nullable
    assert "  l: number | null;" in ts
    assert "  d: number;" in ts       # required decimal
    assert "  b: boolean | null;" in ts
    assert "  dt: string | null;" in ts
    assert "  dtt: string | null;" in ts


# ── Data-aware frontend pages ────────────────────────────────────────────────

def _setup_frontend(tmp_path: Path) -> Path:
    """Generate a frontend-app and return the project root."""
    template = resolve_template("frontend-app")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "fe",
        cli_values={"projectName": "products", "devPort": "5002"},
        interactive=False,
    )
    return result / "products"


def test_list_page_with_resource(tmp_path: Path):
    """Page with resource+type='list' generates a data-fetching table component."""
    project = _setup_frontend(tmp_path)
    pages = parse_pages(json.dumps([
        {"path": "list", "label": "All Products", "resource": "product", "type": "list",
         "fields": [{"name": "name", "type": "string"}, {"name": "price", "type": "decimal"}, {"name": "stock", "type": "integer"}]}
    ]))

    generate_page_components(project, pages, "products")

    page_file = project / "src" / "routes" / "ListPage.tsx"
    assert page_file.exists()
    content = page_file.read_text()

    # Imports
    assert "useApiClient" in content
    assert "useQuery" in content
    assert "my-api-client/react" in content
    assert "my-api-client" in content

    # API call
    assert '"/product"' in content
    assert "page" in content
    assert "size" in content

    # Table columns
    assert "Name" in content
    assert "Price" in content
    assert "Stock" in content

    # States
    assert "Loading" in content
    assert "No data found" in content

    # Pagination
    assert "Previous" in content
    assert "Next" in content


def test_form_page_with_resource(tmp_path: Path):
    """Page with resource+type='form' generates a form with typed inputs."""
    project = _setup_frontend(tmp_path)
    pages = parse_pages(json.dumps([
        {"path": "new", "label": "New Product", "resource": "product", "type": "form",
         "fields": [
            {"name": "name", "type": "string", "required": True},
            {"name": "description", "type": "text"},
            {"name": "price", "type": "decimal", "required": True},
            {"name": "active", "type": "boolean"},
         ]}
    ]))

    generate_page_components(project, pages, "products")

    page_file = project / "src" / "routes" / "NewPage.tsx"
    assert page_file.exists()
    content = page_file.read_text()

    # Imports
    assert "useApiClient" in content
    assert "useMutation" in content
    assert "CreateProductRequest" in content

    # Form inputs by type
    assert 'type="text"' in content     # string → text input
    assert "<textarea" in content        # text → textarea
    assert 'type="number"' in content    # decimal → number
    assert 'step="0.01"' in content      # decimal step
    assert 'type="checkbox"' in content  # boolean → checkbox

    # Required markers
    assert "Name *" in content
    assert "Price *" in content

    # Submit
    assert "Create" in content
    assert "Creating..." in content
    assert "Created successfully" in content

    # API call
    assert '"/product"' in content


def test_placeholder_page_without_resource(tmp_path: Path):
    """Page without resource stays as a simple placeholder."""
    project = _setup_frontend(tmp_path)
    pages = parse_pages('[{"path":"about","label":"About"}]')

    generate_page_components(project, pages, "products")

    page = (project / "src" / "routes" / "AboutPage.tsx").read_text()
    assert "About" in page
    assert "useApiClient" not in page  # no data fetching
    assert "useQuery" not in page


def test_pages_registry_with_mixed_types(tmp_path: Path):
    """pages.ts correctly registers both resource-aware and placeholder pages."""
    project = _setup_frontend(tmp_path)
    pages = parse_pages(json.dumps([
        {"path": "list", "label": "List", "resource": "product", "type": "list", "fields": [{"name": "name", "type": "string"}]},
        {"path": "about", "label": "About"},
    ]))

    generate_page_components(project, pages, "products")

    pages_ts = (project / "src" / "pages.ts").read_text()
    assert "ListPage" in pages_ts
    assert "AboutPage" in pages_ts
    assert '"list"' in pages_ts
    assert '"about"' in pages_ts
