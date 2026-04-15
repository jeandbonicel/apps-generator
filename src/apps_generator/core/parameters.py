"""Parameter resolution — merging defaults, user values, validation, interactive prompts."""

from __future__ import annotations

from typing import Any

import jsonschema
import typer
from rich.prompt import Prompt

from apps_generator.models.context import GenerationContext
from apps_generator.utils import naming
from apps_generator.utils.console import console


def merge_parameters(
    defaults: dict[str, Any],
    file_values: dict[str, Any],
    cli_values: dict[str, str],
) -> dict[str, Any]:
    """Merge parameter sources: defaults <- file values <- CLI overrides."""
    result = dict(defaults)
    result.update(file_values)

    for key, value in cli_values.items():
        # Support nested keys via dot notation: features.docker=false
        if "." in key:
            parts = key.split(".", 1)
            if parts[0] not in result or not isinstance(result[parts[0]], dict):
                result[parts[0]] = {}
            # Parse boolean-like strings
            result[parts[0]][parts[1]] = _parse_value(value)
        else:
            result[key] = _parse_value(value)

    return result


def _parse_value(value: str) -> Any:
    """Parse a CLI string value to its appropriate type."""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def validate_parameters(params: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Validate parameters against a JSON Schema. Returns list of error messages."""
    if not schema:
        return []

    validator = jsonschema.Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(params)]


def prompt_missing_params(
    params: dict[str, Any],
    schema: dict[str, Any],
    interactive: bool = True,
) -> dict[str, Any]:
    """Prompt for missing required parameters if in interactive mode."""
    if not schema or not interactive:
        return params

    required = schema.get("required", [])
    properties = schema.get("properties", {})

    for param_name in required:
        if param_name in params and params[param_name]:
            continue

        prop = properties.get(param_name, {})
        description = prop.get("description", param_name)
        default = prop.get("default", "")
        examples = prop.get("examples", [])

        hint = description
        if examples:
            hint += f" (e.g., {examples[0]})"

        value = Prompt.ask(
            f"  [bold]{param_name}[/bold] — {hint}",
            default=str(default) if default else None,
            console=console,
        )

        if value:
            params[param_name] = _parse_value(value)

    return params


def derive_variants(params: dict[str, Any], derived_configs: list[dict]) -> dict[str, Any]:
    """Generate naming variants for specified parameters.

    For a param 'projectName' with value 'order-service', generates:
    - projectNameCamel = 'orderService'
    - projectNamePascal = 'OrderService'
    - projectNameSnake = 'order_service'
    - projectNameKebab = 'order-service'
    - projectNameTitle = 'Order Service'
    """
    variant_funcs = {
        "camel": naming.camel_case,
        "pascal": naming.pascal_case,
        "snake": naming.snake_case,
        "kebab": naming.kebab_case,
        "upper_snake": naming.upper_snake_case,
        "path": naming.package_to_path,
        "title": naming.title_case,
    }

    for config in derived_configs:
        source = config.get("source", "") if isinstance(config, dict) else config.source
        variants = config.get("variants", ["camel", "pascal", "snake", "kebab"]) if isinstance(config, dict) else config.variants
        value = params.get(source, "")

        if not value:
            continue

        for variant in variants:
            func = variant_funcs.get(variant)
            if func:
                key = f"{source}{naming.capitalize_first(variant)}"
                params[key] = func(str(value))

    return params


def build_context(
    defaults: dict[str, Any],
    file_values: dict[str, Any],
    cli_values: dict[str, str],
    schema: dict[str, Any],
    derived_configs: list,
    features: list,
    interactive: bool = True,
) -> GenerationContext:
    """Build the full generation context from all parameter sources."""
    # Merge
    params = merge_parameters(defaults, file_values, cli_values)

    # Interactive prompts for missing required params
    if interactive:
        params = prompt_missing_params(params, schema, interactive)

    # Validate
    errors = validate_parameters(params, schema)
    if errors:
        console.print("[red]Parameter validation errors:[/red]")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(1)

    # Extract feature flags
    feature_flags: dict[str, bool] = {}
    schema_features = params.pop("features", {})
    if isinstance(schema_features, dict):
        feature_flags.update(schema_features)

    # Apply feature defaults from manifest
    for feature in features:
        fname = feature.name if hasattr(feature, "name") else feature.get("name", "")
        fdefault = feature.default if hasattr(feature, "default") else feature.get("default", True)
        if fname and fname not in feature_flags:
            feature_flags[fname] = fdefault

    # Derive naming variants
    params = derive_variants(params, derived_configs)

    return GenerationContext(params=params, features=feature_flags)
