"""Tests for gateway registration, api-client linking, and docker-compose generation."""

import json
from pathlib import Path

import yaml

from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template
from apps_generator.cli.generators.gateway import register_in_gateway, find_gateway_routes
from apps_generator.cli.generators.linking import (
    register_api_client,
    find_consumer_root,
    find_api_client_src,
)


# ── Gateway registration ────────────────────────────────────────────────────

def _setup_gateway(tmp_path: Path) -> Path:
    """Generate a gateway and return the output dir."""
    template = resolve_template("api-gateway")
    return generate(
        template_dir=template.path,
        output_dir=tmp_path / "gw",
        cli_values={
            "projectName": "my-gateway",
            "groupId": "com.test",
            "basePackage": "com.test.gw",
            "features.oauth2": "false",
        },
        interactive=False,
    )


def test_register_in_gateway(tmp_path: Path):
    """--gateway registers a backend's route in routes.yaml."""
    gw_dir = _setup_gateway(tmp_path)

    register_in_gateway(gateway_path=gw_dir, service_name="order-service")

    routes_file = find_gateway_routes(gw_dir)
    assert routes_file is not None

    data = yaml.safe_load(routes_file.read_text())
    routes = data.get("spring", {}).get("cloud", {}).get("gateway", {}).get("routes", [])
    assert len(routes) == 1
    assert routes[0]["id"] == "order-service"
    assert "Path=/api/**" in routes[0]["predicates"]
    assert "StripPrefix=1" in routes[0]["filters"]


def test_register_multiple_services_in_gateway(tmp_path: Path):
    """Multiple backends get separate routes with incrementing ports."""
    gw_dir = _setup_gateway(tmp_path)

    register_in_gateway(gateway_path=gw_dir, service_name="order-service")
    register_in_gateway(gateway_path=gw_dir, service_name="product-service")

    routes_file = find_gateway_routes(gw_dir)
    data = yaml.safe_load(routes_file.read_text())
    routes = data["spring"]["cloud"]["gateway"]["routes"]
    assert len(routes) == 2

    names = [r["id"] for r in routes]
    assert "order-service" in names
    assert "product-service" in names

    # Ports should be different
    ports = [r["uri"].split(":")[-1] for r in routes]
    assert len(set(ports)) == 2  # unique ports


def test_register_duplicate_service_skipped(tmp_path: Path):
    """Registering the same service twice doesn't create a duplicate route."""
    gw_dir = _setup_gateway(tmp_path)

    register_in_gateway(gateway_path=gw_dir, service_name="order-service")
    register_in_gateway(gateway_path=gw_dir, service_name="order-service")

    routes_file = find_gateway_routes(gw_dir)
    data = yaml.safe_load(routes_file.read_text())
    routes = data["spring"]["cloud"]["gateway"]["routes"]
    assert len(routes) == 1


def test_gateway_strips_service_suffix_for_api_prefix(tmp_path: Path):
    """'order-service' → route predicate Path=/api/**."""
    gw_dir = _setup_gateway(tmp_path)
    register_in_gateway(gateway_path=gw_dir, service_name="order-service")

    routes_file = find_gateway_routes(gw_dir)
    data = yaml.safe_load(routes_file.read_text())
    route = data["spring"]["cloud"]["gateway"]["routes"][0]
    assert "Path=/api/**" in route["predicates"]


def test_gateway_no_security_config_without_oauth2(tmp_path: Path):
    """Gateway generated with oauth2=false has no SecurityConfig.java."""
    gw_dir = _setup_gateway(tmp_path)
    security_files = list((gw_dir / "my-gateway").rglob("SecurityConfig.java"))
    assert len(security_files) == 0


def test_gateway_has_security_headers_filter(tmp_path: Path):
    """Gateway generates a SecurityHeadersFilter that adds OWASP headers."""
    gw_dir = _setup_gateway(tmp_path)
    filters = list((gw_dir / "my-gateway").rglob("SecurityHeadersFilter.java"))
    assert len(filters) == 1
    content = filters[0].read_text()
    assert "X-Content-Type-Options" in content
    assert "X-Frame-Options" in content
    assert "nosniff" in content


def test_shell_nginx_has_security_headers(tmp_path: Path):
    """Shell nginx config includes security headers."""
    template = resolve_template("platform-shell")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "sh",
        cli_values={"projectName": "my-shell"},
        interactive=False,
    )
    nginx = (result / "my-shell" / "docker" / "nginx.conf").read_text()
    assert "X-Frame-Options" in nginx
    assert "X-Content-Type-Options" in nginx
    assert "Content-Security-Policy" in nginx
    assert "Referrer-Policy" in nginx
    assert "frame-ancestors 'none'" in nginx


# ── API client linking ───────────────────────────────────────────────────────

def _setup_api_client(tmp_path: Path) -> Path:
    """Generate an api-client and return its output dir."""
    template = resolve_template("api-client")
    return generate(
        template_dir=template.path,
        output_dir=tmp_path / "client",
        cli_values={"projectName": "my-api-client"},
        interactive=False,
    )


def test_register_api_client_adds_dependency(tmp_path: Path):
    """--api-client adds a file: dependency to the consumer's package.json."""
    client_dir = _setup_api_client(tmp_path)

    shell_template = resolve_template("platform-shell")
    shell_dir = generate(
        template_dir=shell_template.path,
        output_dir=tmp_path / "shell",
        cli_values={"projectName": "my-shell"},
        interactive=False,
    )

    consumer = find_consumer_root(shell_dir, "my-shell")
    assert consumer is not None

    register_api_client(api_client_path=client_dir, consumer_root=consumer)

    pkg = json.loads((consumer / "package.json").read_text())
    assert "my-api-client" in pkg["dependencies"]
    assert pkg["dependencies"]["my-api-client"].startswith("file:")


def test_register_api_client_copies_local_deps(tmp_path: Path):
    """--api-client copies the library into local-deps/ for Docker builds."""
    client_dir = _setup_api_client(tmp_path)

    fe_template = resolve_template("frontend-app")
    fe_dir = generate(
        template_dir=fe_template.path,
        output_dir=tmp_path / "fe",
        cli_values={"projectName": "my-app", "devPort": "5001"},
        interactive=False,
    )

    consumer = find_consumer_root(fe_dir, "my-app")
    register_api_client(api_client_path=client_dir, consumer_root=consumer)

    local_deps = consumer / "local-deps" / "my-api-client"
    assert local_deps.exists()
    assert (local_deps / "package.json").exists()


def test_find_api_client_src(tmp_path: Path):
    """find_api_client_src locates the src/ dir inside the api-client project."""
    client_dir = _setup_api_client(tmp_path)
    src = find_api_client_src(client_dir)
    assert src is not None
    assert (src / "client.ts").exists()
    assert (src / "react.ts").exists()


# ── Docker compose generation ────────────────────────────────────────────────

def test_docker_compose_scans_projects(tmp_path: Path):
    """docker-compose command scans workspace and generates correct services."""
    from apps_generator.cli.docker_compose import _scan_workspace

    # Generate a minimal workspace
    gw_template = resolve_template("api-gateway")
    be_template = resolve_template("api-domain")
    fe_template = resolve_template("frontend-app")
    sh_template = resolve_template("platform-shell")

    generate(template_dir=gw_template.path, output_dir=tmp_path / "gateway",
             cli_values={"projectName": "gw", "groupId": "com.t", "basePackage": "com.t.gw"},
             interactive=False)
    generate(template_dir=be_template.path, output_dir=tmp_path / "backend",
             cli_values={"projectName": "svc", "groupId": "com.t", "basePackage": "com.t.svc"},
             interactive=False)
    generate(template_dir=fe_template.path, output_dir=tmp_path / "fe",
             cli_values={"projectName": "app", "devPort": "5001"},
             interactive=False)
    generate(template_dir=sh_template.path, output_dir=tmp_path / "shell",
             cli_values={"projectName": "shell"},
             interactive=False)

    projects = _scan_workspace(tmp_path)
    types = {p["type"] for p in projects}
    assert "api-gateway" in types
    assert "api-domain" in types
    assert "frontend-app" in types
    assert "platform-shell" in types


def test_docker_compose_env_substitution(tmp_path: Path):
    """Generated docker-compose uses ${} env vars for postgres credentials."""
    from apps_generator.cli.docker_compose import _scan_workspace, _build_compose

    be_template = resolve_template("api-domain")
    generate(template_dir=be_template.path, output_dir=tmp_path / "be",
             cli_values={"projectName": "svc", "groupId": "com.t", "basePackage": "com.t.svc"},
             interactive=False)

    projects = _scan_workspace(tmp_path)
    compose = _build_compose(projects, tmp_path)

    pg = compose["services"]["postgres"]
    assert "${POSTGRES_USER:-postgres}" in str(pg["environment"]["POSTGRES_USER"])
    assert "${POSTGRES_PASSWORD:-postgres}" in str(pg["environment"]["POSTGRES_PASSWORD"])


def test_docker_compose_gateway_url_for_shell(tmp_path: Path):
    """Shell service gets GATEWAY_URL pointing to the gateway container."""
    from apps_generator.cli.docker_compose import _scan_workspace, _build_compose

    gw_template = resolve_template("api-gateway")
    sh_template = resolve_template("platform-shell")

    generate(template_dir=gw_template.path, output_dir=tmp_path / "gw",
             cli_values={"projectName": "my-gw", "groupId": "com.t", "basePackage": "com.t.gw"},
             interactive=False)
    generate(template_dir=sh_template.path, output_dir=tmp_path / "shell",
             cli_values={"projectName": "shell"},
             interactive=False)

    projects = _scan_workspace(tmp_path)
    compose = _build_compose(projects, tmp_path)

    shell_svc = compose["services"]["shell"]
    assert "environment" in shell_svc
    assert "GATEWAY_URL" in shell_svc["environment"]
    assert "my-gw" in shell_svc["environment"]["GATEWAY_URL"]
