"""Integration tests for template generation."""

from pathlib import Path

from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template


def test_generate_platform_shell(tmp_output: Path):
    template = resolve_template("platform-shell")
    assert template is not None

    result = generate(
        template_dir=template.path,
        output_dir=tmp_output,
        cli_values={"projectName": "test-shell"},
        interactive=False,
    )

    assert (result / "test-shell" / "package.json").exists()
    assert (result / "test-shell" / "src" / "auth" / "AuthProvider.tsx").exists()
    assert (result / "test-shell" / "src" / "tenants" / "TenantSwitcher.tsx").exists()
    assert (result / "test-shell" / "vite.config.ts").exists()

    # Verify no unrendered Jinja2 in package.json
    pkg = (result / "test-shell" / "package.json").read_text()
    assert "test-shell" in pkg
    assert "{{" not in pkg


def test_generate_frontend_app(tmp_output: Path):
    template = resolve_template("frontend-app")
    assert template is not None

    result = generate(
        template_dir=template.path,
        output_dir=tmp_output,
        cli_values={"projectName": "orders", "devPort": "5001"},
        interactive=False,
    )

    assert (result / "orders" / "package.json").exists()
    assert (result / "orders" / "vite.config.ts").exists()

    vite_cfg = (result / "orders" / "vite.config.ts").read_text()
    assert 'name: "orders"' in vite_cfg
    assert "5001" in vite_cfg


def test_generate_api_domain(tmp_output: Path):
    template = resolve_template("api-domain")
    assert template is not None

    result = generate(
        template_dir=template.path,
        output_dir=tmp_output,
        cli_values={
            "projectName": "order-service",
            "groupId": "com.example",
            "basePackage": "com.example.orders",
        },
        interactive=False,
    )

    assert (result / "order-service" / "build.gradle.kts").exists()

    # Check Java package structure
    app_java = list((result / "order-service").rglob("*Application.java"))
    assert len(app_java) == 1
    content = app_java[0].read_text()
    assert "package com.example.orders;" in content
    assert "OrderServiceApplication" in content


def test_generate_platform_shell_has_remotes_json(tmp_output: Path):
    """Shell generates with an empty remotes.json for runtime config."""
    template = resolve_template("platform-shell")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_output,
        cli_values={"projectName": "my-shell"},
        interactive=False,
    )

    remotes_file = result / "my-shell" / "public" / "remotes.json"
    assert remotes_file.exists()

    import json

    remotes = json.loads(remotes_file.read_text())
    assert remotes == []

    # Config loads from remotes.json, not baked-in
    config_ts = (result / "my-shell" / "src" / "config" / "remotes.ts").read_text()
    assert "loadRemotes" in config_ts
    assert "getRemotes" in config_ts


def test_shell_linking_registers_frontend(tmp_path: Path):
    """Generating a frontend-app with --shell writes to the shell's remotes.json."""
    shell_template = resolve_template("platform-shell")
    fe_template = resolve_template("frontend-app")

    # Step 1: Generate shell
    shell_dir = tmp_path / "shell"
    generate(
        template_dir=shell_template.path,
        output_dir=shell_dir,
        cli_values={"projectName": "my-shell"},
        interactive=False,
    )

    remotes_file = shell_dir / "my-shell" / "public" / "remotes.json"
    assert remotes_file.exists()

    # Step 2: Generate frontend app with --shell linking
    fe_dir = tmp_path / "orders"
    generate(
        template_dir=fe_template.path,
        output_dir=fe_dir,
        cli_values={"projectName": "orders", "devPort": "5001"},
        interactive=False,
    )

    # Manually call the registration (simulates --shell flag)
    from apps_generator.cli.generators.shell import register_in_shell

    register_in_shell(
        shell_path=shell_dir,
        app_name="orders",
        dev_port="5001",
        menu_label="Orders",
    )

    import json

    remotes = json.loads(remotes_file.read_text())
    assert len(remotes) == 1
    assert remotes[0]["name"] == "orders"
    assert remotes[0]["url"] == "http://localhost:5001"
    assert remotes[0]["menuLabel"] == "Orders"

    # Step 3: Add another app
    fe_dir2 = tmp_path / "users"
    generate(
        template_dir=fe_template.path,
        output_dir=fe_dir2,
        cli_values={"projectName": "users", "devPort": "5002"},
        interactive=False,
    )
    register_in_shell(
        shell_path=shell_dir,
        app_name="users",
        dev_port="5002",
        menu_label="Users",
    )

    remotes = json.loads(remotes_file.read_text())
    assert len(remotes) == 2
    assert remotes[1]["name"] == "users"
    assert remotes[1]["url"] == "http://localhost:5002"


def test_shell_linking_no_duplicates(tmp_path: Path):
    """Registering the same app twice doesn't create duplicates."""
    shell_template = resolve_template("platform-shell")

    shell_dir = tmp_path / "shell"
    generate(
        template_dir=shell_template.path,
        output_dir=shell_dir,
        cli_values={"projectName": "my-shell"},
        interactive=False,
    )

    from apps_generator.cli.generators.shell import register_in_shell

    register_in_shell(shell_path=shell_dir, app_name="orders", dev_port="5001", menu_label="Orders")
    register_in_shell(shell_path=shell_dir, app_name="orders", dev_port="5001", menu_label="Orders")

    import json

    remotes_file = shell_dir / "my-shell" / "public" / "remotes.json"
    remotes = json.loads(remotes_file.read_text())
    assert len(remotes) == 1


def test_shell_linking_with_pages(tmp_path: Path):
    """Pages metadata is registered in remotes.json and page components are generated."""
    shell_template = resolve_template("platform-shell")
    fe_template = resolve_template("frontend-app")

    shell_dir = tmp_path / "shell"
    generate(
        template_dir=shell_template.path,
        output_dir=shell_dir,
        cli_values={"projectName": "my-shell"},
        interactive=False,
    )

    fe_dir = tmp_path / "orders"
    generate(
        template_dir=fe_template.path,
        output_dir=fe_dir,
        cli_values={
            "projectName": "orders",
            "devPort": "5001",
            "pages": '[{"path":"overview","label":"Overview"},{"path":"list","label":"Order List"}]',
        },
        interactive=False,
    )

    from apps_generator.cli.generators.pages import parse_pages, find_project_root, generate_page_components
    from apps_generator.cli.generators.shell import register_in_shell

    pages = parse_pages('[{"path":"overview","label":"Overview"},{"path":"list","label":"Order List"}]')
    project_root = find_project_root(fe_dir, "orders")
    assert project_root is not None
    generate_page_components(project_root, pages, "orders")

    register_in_shell(
        shell_path=shell_dir,
        app_name="orders",
        dev_port="5001",
        menu_label="Orders",
        pages=pages,
    )

    import json

    remotes_file = shell_dir / "my-shell" / "public" / "remotes.json"
    remotes = json.loads(remotes_file.read_text())
    assert len(remotes) == 1
    assert "pages" in remotes[0]
    assert len(remotes[0]["pages"]) == 2
    assert remotes[0]["pages"][0]["path"] == "overview"
    assert remotes[0]["pages"][1]["label"] == "Order List"

    # Verify page components were generated
    assert (project_root / "src" / "routes" / "OverviewPage.tsx").exists()
    assert (project_root / "src" / "routes" / "ListPage.tsx").exists()

    # Verify pages.ts registry
    pages_ts = (project_root / "src" / "pages.ts").read_text()
    assert "OverviewPage" in pages_ts
    assert "ListPage" in pages_ts
    assert '"overview"' in pages_ts
    assert '"list"' in pages_ts


def test_shell_has_horizontal_tabs(tmp_output: Path):
    """Shell generates with AppTabs instead of old Sidebar."""
    template = resolve_template("platform-shell")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_output,
        cli_values={"projectName": "my-shell"},
        interactive=False,
    )

    # AppTabs exists, old Sidebar doesn't
    assert (result / "my-shell" / "src" / "layout" / "AppTabs.tsx").exists()
    assert not (result / "my-shell" / "src" / "layout" / "Sidebar.tsx").exists()

    # AppShell uses AppTabs
    app_shell = (result / "my-shell" / "src" / "layout" / "AppShell.tsx").read_text()
    assert "AppTabs" in app_shell
    assert "Sidebar" not in app_shell

    # RemoteAppLayout exists for page sidebar
    assert (result / "my-shell" / "src" / "layout" / "RemoteAppLayout.tsx").exists()


def test_generate_ui_kit(tmp_output: Path):
    """UI kit template generates with shadcn components and Storybook."""
    template = resolve_template("ui-kit")
    assert template is not None

    result = generate(
        template_dir=template.path,
        output_dir=tmp_output,
        cli_values={"projectName": "my-ui-kit"},
        interactive=False,
    )

    project = result / "my-ui-kit"
    assert (project / "package.json").exists()
    assert (project / "src" / "index.ts").exists()
    assert (project / "src" / "lib" / "utils.ts").exists()
    assert (project / "src" / "globals.css").exists()
    assert (project / "src" / "tailwind-preset.ts").exists()
    assert (project / ".storybook" / "main.ts").exists()

    # shadcn components
    assert (project / "src" / "components" / "ui" / "button.tsx").exists()
    assert (project / "src" / "components" / "ui" / "card.tsx").exists()
    assert (project / "src" / "components" / "ui" / "dialog.tsx").exists()

    # Stories
    assert (project / "stories" / "Button.stories.tsx").exists()

    # Package exports
    pkg = (project / "package.json").read_text()
    assert "my-ui-kit" in pkg
    assert "storybook" in pkg


def test_uikit_linking(tmp_path: Path):
    """--uikit adds file: dependency and updates tailwind config."""
    uikit_template = resolve_template("ui-kit")
    shell_template = resolve_template("platform-shell")

    uikit_dir = tmp_path / "uikit"
    generate(
        template_dir=uikit_template.path,
        output_dir=uikit_dir,
        cli_values={"projectName": "my-ui-kit"},
        interactive=False,
    )

    shell_dir = tmp_path / "shell"
    generate(
        template_dir=shell_template.path,
        output_dir=shell_dir,
        cli_values={"projectName": "my-shell"},
        interactive=False,
    )

    from apps_generator.cli.generators.linking import register_uikit, find_consumer_root

    consumer_root = find_consumer_root(shell_dir, "my-shell")
    assert consumer_root is not None

    register_uikit(uikit_path=uikit_dir, consumer_root=consumer_root)

    import json

    pkg = json.loads((consumer_root / "package.json").read_text())
    assert "my-ui-kit" in pkg["dependencies"]
    assert pkg["dependencies"]["my-ui-kit"].startswith("file:")

    tailwind = (consumer_root / "tailwind.config.ts").read_text()
    assert "hsl(var(--primary))" in tailwind
    assert "my-ui-kit" in tailwind  # content path includes ui-kit


def test_templates_list():
    from apps_generator.templates.registry import list_templates

    templates = list_templates()
    names = [t.name for t in templates]
    assert "platform-shell" in names
    assert "frontend-app" in names
    assert "api-domain" in names
