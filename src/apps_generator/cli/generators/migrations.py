"""Migration generation — generates Liquibase migration YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from apps_generator.utils.console import console
from apps_generator.utils.naming import snake_case

from apps_generator.cli.generators.resources import SQL_TYPES


def generate_migration(res_root: Path, entity: str, table: str, fields: list[dict], seq: int, name: str) -> None:
    """Generate Liquibase migration YAML."""
    changes_dir = res_root / "db" / "changelog" / "changes"
    changes_dir.mkdir(parents=True, exist_ok=True)

    migration_file = changes_dir / f"{seq:03d}-create-{name}.yaml"
    if migration_file.exists():
        return

    columns = [
        {"name": "id", "type": "BIGINT", "autoIncrement": True, "pk": True},
        {"name": "tenant_id", "type": "VARCHAR(255)", "nullable": False},
    ]

    for f in fields:
        ft = f.get("type", "string")
        sql_type = SQL_TYPES.get(ft, "VARCHAR(255)")
        if ft == "string":
            max_len = f.get("maxLength", 255)
            sql_type = f"VARCHAR({max_len})"
        col: dict = {"name": snake_case(f["name"]), "type": sql_type}
        if f.get("required"):
            col["nullable"] = False
        columns.append(col)

    columns.append({"name": "created_at", "type": "TIMESTAMP", "nullable": False})
    columns.append({"name": "updated_at", "type": "TIMESTAMP", "nullable": False})

    # Build YAML
    col_entries = []
    for c in columns:
        constraints = {}
        if c.get("pk"):
            constraints["primaryKey"] = True
        if c.get("nullable") is False and not c.get("pk"):
            constraints["nullable"] = False

        entry: dict = {"name": c["name"], "type": c["type"]}
        if c.get("autoIncrement"):
            entry["autoIncrement"] = True
        if constraints:
            entry["constraints"] = constraints
        col_entries.append({"column": entry})

    changeset: dict = {
        "id": f"{seq:03d}-create-{name}",
        "author": "generator",
        "changes": [
            {"createTable": {"tableName": table, "columns": col_entries}},
            {
                "createIndex": {
                    "tableName": table,
                    "indexName": f"idx_{table}_tenant_id",
                    "columns": [{"column": {"name": "tenant_id"}}],
                }
            },
        ],
    }

    # Add unique constraints
    for f in fields:
        if f.get("unique"):
            changeset["changes"].append(
                {
                    "addUniqueConstraint": {
                        "tableName": table,
                        "columnNames": snake_case(f["name"]),
                        "constraintName": f"uq_{table}_{snake_case(f['name'])}",
                    }
                }
            )

    migration_file.write_text(
        yaml.dump(
            {"databaseChangeLog": [{"changeSet": changeset}]},
            default_flow_style=False,
            sort_keys=False,
        )
    )

    # Update master changelog
    master = res_root / "db" / "changelog" / "db.changelog-master.yaml"
    if master.exists():
        with open(master) as mf:
            master_data = yaml.safe_load(mf) or {}
        changelog = master_data.get("databaseChangeLog", [])
        include_path = f"db/changelog/changes/{seq:03d}-create-{name}.yaml"
        if not any(e.get("include", {}).get("file") == include_path for e in changelog):
            changelog.append({"include": {"file": include_path}})
            master_data["databaseChangeLog"] = changelog
            with open(master, "w") as mf:
                yaml.dump(master_data, mf, default_flow_style=False, sort_keys=False)

    console.print(f"    Created: db/changelog/changes/{seq:03d}-create-{name}.yaml")
