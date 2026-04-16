"""Docker Compose generator — scans workspace and generates docker-compose.yaml."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml

from apps_generator.utils.console import console


def docker_compose(
    directory: Path = typer.Argument(".", help="Workspace directory to scan."),
    output: Path = typer.Option("docker-compose.yaml", "--output", "-o", help="Output file path."),
) -> None:
    """Generate a docker-compose.yaml from all projects in the workspace."""
    directory = directory.resolve()

    if not directory.is_dir():
        console.print(f"[red]Error:[/red] {directory} is not a directory.")
        raise typer.Exit(1)

    # Scan for projects
    projects = _scan_workspace(directory)

    if not projects:
        console.print("[yellow]No generated projects found in this directory.[/yellow]")
        raise typer.Exit(1)

    # Generate docker-compose
    compose = _build_compose(projects, directory)

    # Generate postgres init script if multiple backends need DBs
    backends = [p for p in projects if p["type"] == "api-domain"]
    if len(backends) > 1:
        init_script = _build_postgres_init_script(backends)
        init_path = directory / "docker" / "init-databases.sh"
        init_path.parent.mkdir(parents=True, exist_ok=True)
        init_path.write_text(init_script)
        init_path.chmod(0o755)
        console.print(f"  Created: {init_path}")

    # Write docker-compose.yaml
    output_path = directory / output if not output.is_absolute() else output
    with open(output_path, "w") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

    console.print(f"\n[green]Generated {output_path}[/green]")
    console.print(f"  Services: {len(compose['services'])}")
    for name in compose["services"]:
        console.print(f"    - {name}")
    console.print(f"\n  Run: docker compose up --build")


def _scan_workspace(directory: Path) -> list[dict]:
    """Scan a directory for generated projects and identify their types."""
    projects = []

    for child in sorted(directory.iterdir()):
        if not child.is_dir():
            continue

        # Check one level down (e.g., ./shell/my-platform/)
        for subdir in [child] + list(child.iterdir()):
            if not subdir.is_dir():
                continue

            project = _identify_project(subdir)
            if project:
                project["path"] = str(subdir.relative_to(directory))
                projects.append(project)
                break

    return projects


def _identify_project(path: Path) -> dict | None:
    """Identify a project type by examining its files."""
    # Frontend (shell or MFE): has package.json + vite.config.ts + docker/
    if (path / "package.json").exists() and (path / "docker" / "Dockerfile").exists():
        try:
            with open(path / "package.json") as f:
                pkg = json.load(f)
            name = pkg.get("name", path.name)

            # Check if it's a shell (has public/remotes.json)
            if (path / "public" / "remotes.json").exists():
                return {"type": "platform-shell", "name": name, "dir": path}

            # Check if it's a MFE (has remoteEntry in vite config)
            vite_config = path / "vite.config.ts"
            if vite_config.exists() and "remoteEntry" in vite_config.read_text():
                # Find the port from vite config
                port = 5001
                content = vite_config.read_text()
                import re
                port_match = re.search(r"port:\s*(\d+)", content)
                if port_match:
                    port = int(port_match.group(1))
                return {"type": "frontend-app", "name": name, "dir": path, "port": port}

        except (json.JSONDecodeError, OSError):
            pass

    # Java backend: has build.gradle.kts + docker/
    if (path / "build.gradle.kts").exists() and (path / "docker" / "Dockerfile").exists():
        name = path.name
        settings = path / "settings.gradle.kts"
        if settings.exists():
            import re
            match = re.search(r'rootProject\.name\s*=\s*"([^"]+)"', settings.read_text())
            if match:
                name = match.group(1)

        # Check if it's a gateway (has routes.yaml)
        if (path / "src" / "main" / "resources" / "routes.yaml").exists():
            return {"type": "api-gateway", "name": name, "dir": path}

        # It's a domain service
        return {"type": "api-domain", "name": name, "dir": path}

    return None


def _build_compose(projects: list[dict], workspace: Path) -> dict:
    """Build the docker-compose.yaml structure."""
    services: dict = {}

    backends = [p for p in projects if p["type"] == "api-domain"]
    gateways = [p for p in projects if p["type"] == "api-gateway"]
    frontends = [p for p in projects if p["type"] == "frontend-app"]
    shells = [p for p in projects if p["type"] == "platform-shell"]

    # PostgreSQL (if any backends need it)
    if backends:
        pg_service: dict = {
            "image": "postgres:16-alpine",
            "ports": ["5432:5432"],
            "environment": {
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "postgres",
            },
            "healthcheck": {
                "test": ["CMD-SHELL", "pg_isready -U postgres"],
                "interval": "5s",
                "timeout": "3s",
                "retries": 5,
            },
        }

        if len(backends) == 1:
            db_name = backends[0]["name"].replace("-", "_")
            pg_service["environment"]["POSTGRES_DB"] = db_name
        else:
            # Multiple backends — use init script to create multiple DBs
            pg_service["environment"]["POSTGRES_DB"] = "postgres"
            pg_service["volumes"] = ["./docker/init-databases.sh:/docker-entrypoint-initdb.d/init-databases.sh"]

        services["postgres"] = pg_service

    # Backend services
    port = 8081
    for backend in backends:
        db_name = backend["name"].replace("-", "_")
        svc: dict = {
            "build": {
                "context": f"./{backend['path']}",
                "dockerfile": "docker/Dockerfile",
            },
            "ports": [f"{port}:8080"],
            "environment": {
                "SERVER_PORT": "8080",
                "SPRING_DATASOURCE_URL": f"jdbc:postgresql://postgres:5432/{db_name}",
                "SPRING_DATASOURCE_USERNAME": "postgres",
                "SPRING_DATASOURCE_PASSWORD": "postgres",
                "SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_ISSUER_URI": "https://auth.example.com/realms/main",
            },
            "depends_on": {
                "postgres": {"condition": "service_healthy"},
            },
        }
        services[backend["name"]] = svc
        backend["docker_port"] = port
        port += 1

    # Gateway
    for gw in gateways:
        gw_env: dict = {
            "SERVER_PORT": "8080",
            "SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_ISSUER_URI": "https://auth.example.com/realms/main",
        }

        # Add route env vars pointing to Docker service names
        for i, backend in enumerate(backends):
            api_prefix = backend["name"].replace("-service", "").replace("_service", "")
            gw_env[f"SPRING_CLOUD_GATEWAY_ROUTES_{i}_ID"] = backend["name"]
            gw_env[f"SPRING_CLOUD_GATEWAY_ROUTES_{i}_URI"] = f"http://{backend['name']}:8080"
            gw_env[f"SPRING_CLOUD_GATEWAY_ROUTES_{i}_PREDICATES_0"] = f"Path=/api/{api_prefix}/**"
            gw_env[f"SPRING_CLOUD_GATEWAY_ROUTES_{i}_FILTERS_0"] = "StripPrefix=1"

        depends = [b["name"] for b in backends]
        services[gw["name"]] = {
            "build": {
                "context": f"./{gw['path']}",
                "dockerfile": "docker/Dockerfile",
            },
            "ports": ["8080:8080"],
            "environment": gw_env,
            "depends_on": depends,
        }

    # Frontend MFEs
    for fe in frontends:
        fe_port = fe.get("port", 5001)
        services[fe["name"]] = {
            "build": {
                "context": f"./{fe['path']}",
                "dockerfile": "docker/Dockerfile",
            },
            "ports": [f"{fe_port}:80"],
        }

    # Shell
    for shell in shells:
        depends = [gw["name"] for gw in gateways] + [fe["name"] for fe in frontends]
        services[shell["name"]] = {
            "build": {
                "context": f"./{shell['path']}",
                "dockerfile": "docker/Dockerfile",
            },
            "ports": ["80:80"],
            "depends_on": depends if depends else None,
        }
        # Remove None values
        if not depends:
            del services[shell["name"]]["depends_on"]

    return {"services": services}


def _build_postgres_init_script(backends: list[dict]) -> str:
    """Generate a PostgreSQL init script that creates multiple databases."""
    lines = ["#!/bin/bash", "set -e", ""]
    for backend in backends:
        db_name = backend["name"].replace("-", "_")
        lines.append(f'echo "Creating database: {db_name}"')
        lines.append(f'psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL')
        lines.append(f"    CREATE DATABASE {db_name};")
        lines.append(f"    GRANT ALL PRIVILEGES ON DATABASE {db_name} TO $POSTGRES_USER;")
        lines.append("EOSQL")
        lines.append("")
    return "\n".join(lines)
