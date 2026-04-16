"""Gateway integration — register backend services in an api-gateway project."""

from __future__ import annotations

from pathlib import Path

import yaml

from apps_generator.utils.console import console


def find_gateway_routes(gateway_path: Path) -> Path | None:
    """Find routes.yaml in a gateway project."""
    # Direct: gateway_path/src/main/resources/routes.yaml
    candidate = gateway_path / "src" / "main" / "resources" / "routes.yaml"
    if candidate.exists():
        return candidate

    # One level down
    if gateway_path.is_dir():
        for child in gateway_path.iterdir():
            if child.is_dir():
                candidate = child / "src" / "main" / "resources" / "routes.yaml"
                if candidate.exists():
                    return candidate

    return None


def register_in_gateway(gateway_path: Path, service_name: str) -> None:
    """Add a backend service route to the gateway's routes.yaml."""
    gateway_path = gateway_path.resolve()

    # Find routes.yaml
    routes_file = find_gateway_routes(gateway_path)
    if routes_file is None:
        console.print("[yellow]Warning:[/yellow] Could not find gateway's routes.yaml — skipping.")
        return

    with open(routes_file) as f:
        routes_config = yaml.safe_load(f) or {}

    routes = routes_config.get("spring", {}).get("cloud", {}).get("gateway", {}).get("routes", [])
    if not isinstance(routes, list):
        routes = []

    # Check if already registered
    existing_ids = {r.get("id") for r in routes}
    if service_name in existing_ids:
        console.print(f"[yellow]Service '{service_name}' already registered in gateway — skipping.[/yellow]")
        return

    # Derive API path from service name: "order-service" -> "order", "user-service" -> "user"
    api_prefix = service_name.replace("-service", "").replace("_service", "")

    # Auto-assign port (8081, 8082, ...) based on existing routes
    base_port = 8081
    existing_ports = set()
    for r in routes:
        uri = r.get("uri", "")
        if ":" in uri:
            try:
                existing_ports.add(int(uri.rsplit(":", 1)[1]))
            except (ValueError, IndexError):
                pass
    port = base_port
    while port in existing_ports:
        port += 1

    new_route = {
        "id": service_name,
        "uri": f"http://localhost:{port}",
        "predicates": [f"Path=/api/{api_prefix}/**"],
        "filters": ["StripPrefix=1"],
    }
    routes.append(new_route)

    # Write back
    routes_config.setdefault("spring", {}).setdefault("cloud", {}).setdefault("gateway", {})["routes"] = routes
    with open(routes_file, "w") as f:
        yaml.dump(routes_config, f, default_flow_style=False, sort_keys=False)

    console.print(
        f"[green]Registered '{service_name}' in gateway[/green]\n"
        f"  Route: /api/{api_prefix}/** -> http://localhost:{port}\n"
        f"  Config: {routes_file}"
    )
