"""Shell integration — register frontend apps in a platform-shell project."""

from __future__ import annotations

import json
from pathlib import Path

from apps_generator.utils.console import console
from apps_generator.utils.naming import title_case


def find_remotes_json(shell_path: Path) -> Path | None:
    """Find remotes.json inside a shell project directory."""
    shell_path = shell_path.resolve()

    candidate = shell_path / "public" / "remotes.json"
    if candidate.exists():
        return candidate

    if shell_path.is_dir():
        for child in shell_path.iterdir():
            if child.is_dir():
                candidate = child / "public" / "remotes.json"
                if candidate.exists():
                    return candidate

    return None


def register_in_shell(
    shell_path: Path,
    app_name: str,
    dev_port: str,
    menu_label: str,
    pages: list[dict] | None = None,
) -> None:
    """Add a frontend app entry to the shell's remotes.json."""
    remotes_file = find_remotes_json(shell_path)
    if remotes_file is None:
        console.print("[yellow]Warning:[/yellow] Could not find shell's remotes.json — skipping registration.")
        return

    with open(remotes_file) as f:
        remotes: list[dict] = json.load(f)

    existing_names = {r.get("name") for r in remotes}
    if app_name in existing_names:
        console.print(f"[yellow]App '{app_name}' already registered in shell — skipping.[/yellow]")
        return

    new_entry: dict = {
        "name": app_name,
        "url": f"http://localhost:{dev_port}",
        "menuLabel": menu_label,
        "menuIcon": "",
    }

    if pages:
        new_entry["pages"] = [
            {"path": p["path"], "label": p.get("label", title_case(p["path"]))}
            for p in pages
        ]

    remotes.append(new_entry)

    with open(remotes_file, "w") as f:
        json.dump(remotes, f, indent=2)
        f.write("\n")

    # Add translation keys for nav labels to shell's locale files
    if pages:
        add_nav_translations(remotes_file.parent.parent, app_name, menu_label, pages)

    pages_info = f" ({len(pages)} pages)" if pages else ""
    console.print(
        f"[green]Registered '{app_name}' in shell at {remotes_file}{pages_info}[/green]\n"
        f"  URL: http://localhost:{dev_port}\n"
        f"  Menu: {menu_label}"
    )
    if pages:
        for p in pages:
            console.print(f"    /{app_name}/{p['path']} — {p.get('label', p['path'])}")


def add_nav_translations(
    shell_project_root: Path,
    app_name: str,
    menu_label: str,
    pages: list[dict],
) -> None:
    """Add navigation translation keys to the shell's locale files."""
    locales_dir = shell_project_root / "src" / "i18n" / "locales"
    if not locales_dir.exists():
        return

    nav_keys = {}
    for p in pages:
        nav_keys[p["path"]] = p.get("label", title_case(p["path"]))

    for locale_file in locales_dir.glob("*.json"):
        try:
            with open(locale_file) as f:
                translations = json.load(f)

            if "nav" not in translations:
                translations["nav"] = {}
            if app_name not in translations["nav"]:
                translations["nav"][app_name] = {}

            for path, label in nav_keys.items():
                if path not in translations["nav"][app_name]:
                    translations["nav"][app_name][path] = label

            with open(locale_file, "w") as f:
                json.dump(translations, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except (json.JSONDecodeError, OSError):
            pass
