"""End-to-end tests: generate a full tenant app stack and verify all pieces connect."""

import json
from pathlib import Path

import yaml

from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template
from apps_generator.cli.generators.resources import parse_resources, generate_resource_scaffolding
from apps_generator.cli.generators.types import generate_resource_types
from apps_generator.cli.generators.pages import parse_pages, find_project_root, generate_page_components
from apps_generator.cli.generators.shell import register_in_shell
from apps_generator.cli.generators.gateway import register_in_gateway
from apps_generator.cli.generators.linking import (
    register_uikit,
    register_api_client,
    find_consumer_root,
    find_java_root,
    find_resources_root,
    find_api_client_src,
)


def _gen(template_name: str, tmp_path: Path, name: str, cli: dict) -> Path:
    """Shorthand: resolve template + generate."""
    template = resolve_template(template_name)
    return generate(
        template_dir=template.path,
        output_dir=tmp_path / name,
        cli_values=cli,
        interactive=False,
    )


def test_full_stack_generation(tmp_path: Path):
    """Generate a complete tenant app: gateway + backend with CRUD + shell + MFE with data pages.

    Verifies:
    - All templates generate without errors
    - Backend has tenant-scoped CRUD for the resource
    - TypeScript types are generated in api-client
    - Frontend pages import typed API and fetch data
    - Shell has MFE registered in remotes.json
    - Gateway has backend route configured
    """

    # 1. Generate infrastructure
    _gen("ui-kit", tmp_path, "uikit", {"projectName": "test-ui"})
    _gen("api-client", tmp_path, "client", {"projectName": "test-client"})
    gw_dir = _gen("api-gateway", tmp_path, "gw", {
        "projectName": "test-gw", "groupId": "com.t", "basePackage": "com.t.gw",
        "features.oauth2": "false",
    })
    shell_dir = _gen("platform-shell", tmp_path, "shell", {"projectName": "test-shell"})

    # 2. Generate backend with resources
    resource_json = json.dumps([{
        "name": "task",
        "fields": [
            {"name": "title", "type": "string", "required": True, "maxLength": 200},
            {"name": "done", "type": "boolean"},
            {"name": "due-date", "type": "date"},
        ]
    }])

    be_dir = _gen("api-domain", tmp_path, "be", {
        "projectName": "task-service",
        "groupId": "com.t",
        "basePackage": "com.t.task",
        "features.oauth2": "false",
    })

    java_root = find_java_root(be_dir, "task-service", "com.t.task")
    res_root = find_resources_root(be_dir, "task-service")
    resources = parse_resources(resource_json)
    generate_resource_scaffolding(java_root, res_root, resources, "com.t.task", "task-service")

    # 3. Generate TypeScript types in api-client
    api_client_src = find_api_client_src(tmp_path / "client")
    generate_resource_types(api_client_src, resources)

    # 4. Register backend in gateway
    register_in_gateway(gateway_path=gw_dir, service_name="task-service")

    # 5. Link uikit + api-client to shell
    shell_root = find_consumer_root(shell_dir, "test-shell")
    register_uikit(uikit_path=tmp_path / "uikit", consumer_root=shell_root)
    register_api_client(api_client_path=tmp_path / "client", consumer_root=shell_root)

    # 6. Generate frontend with resource-aware pages
    fe_dir = _gen("frontend-app", tmp_path, "fe", {
        "projectName": "tasks", "devPort": "5001",
    })
    fe_root = find_project_root(fe_dir, "tasks")

    pages = parse_pages(json.dumps([
        {"path": "list", "label": "All Tasks", "resource": "task", "type": "list",
         "fields": [{"name": "title", "type": "string"}, {"name": "done", "type": "boolean"}, {"name": "due-date", "type": "date"}]},
        {"path": "new", "label": "New Task", "resource": "task", "type": "form",
         "fields": [{"name": "title", "type": "string", "required": True}, {"name": "done", "type": "boolean"}, {"name": "due-date", "type": "date"}]},
    ]))
    generate_page_components(fe_root, pages, "tasks")

    # Link dependencies to frontend
    fe_consumer = find_consumer_root(fe_dir, "tasks")
    register_uikit(uikit_path=tmp_path / "uikit", consumer_root=fe_consumer)
    register_api_client(api_client_path=tmp_path / "client", consumer_root=fe_consumer)

    # Register in shell
    register_in_shell(shell_path=shell_dir, app_name="tasks", dev_port="5001", menu_label="Tasks", pages=pages)

    # ── VERIFY BACKEND ──────────────────────────────────────────────────

    # Entity extends TenantAwareEntity (provides id, tenantId, timestamps, Hibernate filter)
    entity = (java_root / "domain" / "model" / "Task.java").read_text()
    assert "extends TenantAwareEntity" in entity
    assert "private String title;" in entity
    assert "private Boolean done;" in entity
    assert "private LocalDate dueDate;" in entity  # kebab → camelCase

    # Service uses TenantContext for writes, Hibernate filter for reads
    service = (java_root / "domain" / "service" / "TaskService.java").read_text()
    assert "TenantContext.requireCurrentTenantId()" in service
    assert "repository.findAll(pageable)" in service  # auto-scoped by Hibernate filter

    # Controller endpoints
    ctrl = (java_root / "interfaces" / "rest" / "TaskController.java").read_text()
    assert '@RequestMapping("/task")' in ctrl

    # DTO validation
    create_dto = (java_root / "interfaces" / "rest" / "dto" / "CreateTaskRequest.java").read_text()
    assert "@NotBlank" in create_dto  # title is required string

    # Migration
    migration = (res_root / "db" / "changelog" / "changes" / "002-create-task.yaml").read_text()
    assert "tasks" in migration  # table name (plural)
    assert "tenant_id" in migration
    assert "due_date" in migration  # kebab → snake_case

    # ── VERIFY TYPESCRIPT TYPES ─────────────────────────────────────────

    ts = (api_client_src / "resources" / "task.ts").read_text()
    assert "export interface Task {" in ts
    assert "  title: string;" in ts
    assert "  done: boolean | null;" in ts
    assert "  dueDate: string | null;" in ts
    assert "export interface CreateTaskRequest {" in ts

    # ── VERIFY FRONTEND PAGES ───────────────────────────────────────────

    list_page = (fe_root / "src" / "routes" / "ListPage.tsx").read_text()
    assert "useApiClient" in list_page
    assert '"/task"' in list_page
    assert "Title" in list_page  # column header
    assert "Done" in list_page

    form_page = (fe_root / "src" / "routes" / "NewPage.tsx").read_text()
    assert "CreateTaskRequest" in form_page
    assert 'type="checkbox"' in form_page  # boolean field
    assert 'type="date"' in form_page      # date field

    # ── VERIFY GATEWAY ROUTES ───────────────────────────────────────────

    from apps_generator.cli.generators.gateway import find_gateway_routes
    routes_yaml = yaml.safe_load(find_gateway_routes(gw_dir).read_text())
    routes = routes_yaml["spring"]["cloud"]["gateway"]["routes"]
    assert any(r["id"] == "task-service" for r in routes)
    assert any("Path=/api/**" in r["predicates"] for r in routes)

    # ── VERIFY SHELL REMOTES ────────────────────────────────────────────

    remotes = json.loads((shell_dir / "test-shell" / "public" / "remotes.json").read_text())
    assert len(remotes) == 1
    assert remotes[0]["name"] == "tasks"
    assert len(remotes[0]["pages"]) == 2
    assert remotes[0]["pages"][0]["path"] == "list"
    assert remotes[0]["pages"][1]["path"] == "new"

    # ── VERIFY DEPENDENCIES LINKED ──────────────────────────────────────

    fe_pkg = json.loads((fe_consumer / "package.json").read_text())
    assert "test-ui" in fe_pkg["dependencies"]
    assert "test-client" in fe_pkg["dependencies"]

    shell_pkg = json.loads((shell_root / "package.json").read_text())
    assert "test-ui" in shell_pkg["dependencies"]
    assert "test-client" in shell_pkg["dependencies"]


def test_full_stack_no_resources_still_works(tmp_path: Path):
    """A backend without resources still generates correctly (health endpoint only)."""
    be_dir = _gen("api-domain", tmp_path, "be", {
        "projectName": "empty-svc",
        "groupId": "com.t",
        "basePackage": "com.t.empty",
        "features.oauth2": "false",
    })

    project = be_dir / "empty-svc"
    assert (project / "build.gradle.kts").exists()

    # Health controller exists
    health_files = list(project.rglob("HealthController.java"))
    assert len(health_files) == 1

    # No resource controllers
    ctrl_files = [f for f in project.rglob("*Controller.java") if "Health" not in f.name]
    assert len(ctrl_files) == 0

    # Shared infra still generated
    assert any(project.rglob("TenantContext.java"))
    assert any(project.rglob("GlobalExceptionHandler.java"))


def test_frontend_without_api_client_still_works(tmp_path: Path):
    """A frontend without --api-client generates placeholder pages (no typed imports)."""
    fe_dir = _gen("frontend-app", tmp_path, "fe", {
        "projectName": "simple-app", "devPort": "5001",
    })
    fe_root = find_project_root(fe_dir, "simple-app")

    pages = parse_pages('[{"path":"home","label":"Home Page"}]')
    generate_page_components(fe_root, pages, "simple-app")

    page = (fe_root / "src" / "routes" / "HomePage.tsx").read_text()
    # Placeholder — no data fetching
    assert "useApiClient" not in page
    assert "useQuery" not in page
