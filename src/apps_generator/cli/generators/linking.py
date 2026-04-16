"""Project linking — register shared libraries (ui-kit, api-client) as dependencies."""

from __future__ import annotations

import json
from pathlib import Path

from apps_generator.utils.console import console


def find_consumer_root(output_dir: Path, project_name: str) -> Path | None:
    """Find the generated project root directory (for shell or frontend-app)."""
    candidate = output_dir / project_name
    if (candidate / "package.json").exists():
        return candidate
    if (output_dir / "package.json").exists():
        return output_dir
    return None


def copy_lib_to_local_deps(lib_dir: Path, consumer_root: Path, lib_name: str) -> None:
    """Copy a shared library into consumer's local-deps/ for Docker builds."""
    import shutil
    local_deps = consumer_root / "local-deps" / lib_name
    local_deps.mkdir(parents=True, exist_ok=True)

    # Copy package.json
    shutil.copy2(lib_dir / "package.json", local_deps / "package.json")

    # Copy dist/ if it exists (built library)
    dist_dir = lib_dir / "dist"
    if dist_dir.exists():
        dest_dist = local_deps / "dist"
        if dest_dist.exists():
            shutil.rmtree(dest_dist)
        shutil.copytree(dist_dir, dest_dist)

    # Copy source files referenced in package.json exports (tailwind-preset, globals.css)
    for src_file in ["src/tailwind-preset.ts", "src/globals.css"]:
        src = lib_dir / src_file
        if src.exists():
            dest = local_deps / src_file
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)


def find_uikit_package_json(uikit_path: Path) -> Path | None:
    """Find package.json inside a ui-kit project directory."""
    candidate = uikit_path / "package.json"
    if candidate.exists():
        return candidate

    if uikit_path.is_dir():
        for child in uikit_path.iterdir():
            if child.is_dir():
                candidate = child / "package.json"
                if candidate.exists():
                    return candidate

    return None


def register_uikit(uikit_path: Path, consumer_root: Path) -> str:
    """Add ui-kit as a file: dependency and extend Tailwind config.

    Returns the ui-kit package name (empty string if linking failed).
    """
    uikit_path = uikit_path.resolve()

    uikit_pkg_path = find_uikit_package_json(uikit_path)
    if uikit_pkg_path is None:
        console.print("[yellow]Warning:[/yellow] Could not find ui-kit's package.json — skipping.")
        return ""

    with open(uikit_pkg_path) as f:
        uikit_pkg = json.load(f)

    uikit_name = uikit_pkg.get("name", "")
    if not uikit_name:
        console.print("[yellow]Warning:[/yellow] ui-kit package.json has no name — skipping.")
        return ""

    uikit_dir = uikit_pkg_path.parent.resolve()

    # Copy library into local-deps/ (for Docker builds)
    copy_lib_to_local_deps(uikit_dir, consumer_root, uikit_name)

    # 1. Add file: dependency pointing to local-deps/ (works both locally and in Docker)
    consumer_pkg_path = consumer_root / "package.json"
    with open(consumer_pkg_path) as f:
        consumer_pkg = json.load(f)

    deps = consumer_pkg.get("dependencies", {})
    deps[uikit_name] = f"file:./local-deps/{uikit_name}"
    consumer_pkg["dependencies"] = deps

    with open(consumer_pkg_path, "w") as f:
        json.dump(consumer_pkg, f, indent=2)
        f.write("\n")

    # 2. Update tailwind.config.ts with shadcn theme + ui-kit content path
    tailwind_path = consumer_root / "tailwind.config.ts"
    if tailwind_path.exists():
        tailwind_content = f'''/** @type {{import('tailwindcss').Config}} */
export default {{
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{{ts,tsx}}",
    "./local-deps/{uikit_name}/src/**/*.{{ts,tsx}}",
  ],
  theme: {{
    extend: {{
      colors: {{
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {{
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        }},
        secondary: {{
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        }},
        destructive: {{
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        }},
        muted: {{
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        }},
        accent: {{
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        }},
        popover: {{
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        }},
        card: {{
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        }},
      }},
      borderRadius: {{
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      }},
    }},
  }},
  plugins: [],
}};
'''
        tailwind_path.write_text(tailwind_content)

    # 3. Replace consumer's index.css with ui-kit's globals.css (includes Tailwind + CSS variables)
    uikit_css = uikit_dir / "src" / "globals.css"
    index_css = consumer_root / "src" / "index.css"
    if index_css.exists() and uikit_css.exists():
        index_css.write_text(uikit_css.read_text())

    console.print(
        f"[green]Linked ui-kit '{uikit_name}' to {consumer_root.name}[/green]\n"
        f"  Dependency: {uikit_name} -> file:./local-deps/{uikit_name}\n"
        f"  Tailwind: shadcn theme applied"
    )
    return uikit_name


def register_api_client(api_client_path: Path, consumer_root: Path) -> None:
    """Add api-client as a file: dependency to a consumer project."""
    api_client_path = api_client_path.resolve()

    pkg_path = find_uikit_package_json(api_client_path)
    if pkg_path is None:
        console.print("[yellow]Warning:[/yellow] Could not find api-client's package.json — skipping.")
        return

    with open(pkg_path) as f:
        pkg = json.load(f)

    client_name = pkg.get("name", "")
    if not client_name:
        console.print("[yellow]Warning:[/yellow] api-client package.json has no name — skipping.")
        return

    client_dir = pkg_path.parent.resolve()

    # Copy library into local-deps/ (for Docker builds)
    copy_lib_to_local_deps(client_dir, consumer_root, client_name)

    # Add file: dependency pointing to local-deps/
    consumer_pkg_path = consumer_root / "package.json"
    with open(consumer_pkg_path) as f:
        consumer_pkg = json.load(f)

    deps = consumer_pkg.get("dependencies", {})
    deps[client_name] = f"file:./local-deps/{client_name}"
    consumer_pkg["dependencies"] = deps

    with open(consumer_pkg_path, "w") as f:
        json.dump(consumer_pkg, f, indent=2)
        f.write("\n")

    console.print(
        f"[green]Linked api-client '{client_name}' to {consumer_root.name}[/green]\n"
        f"  Dependency: {client_name} -> file:./local-deps/{client_name}"
    )


def find_java_root(output_dir: Path, project_name: str, base_package: str) -> Path | None:
    """Find the Java source root for a generated api-domain project."""
    from apps_generator.utils.naming import package_to_path
    pkg_path = package_to_path(base_package)
    candidates = [
        output_dir / project_name / "src" / "main" / "java" / pkg_path,
        output_dir / "src" / "main" / "java" / pkg_path,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_resources_root(output_dir: Path, project_name: str) -> Path | None:
    """Find the resources root for a generated api-domain project."""
    candidates = [
        output_dir / project_name / "src" / "main" / "resources",
        output_dir / "src" / "main" / "resources",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_api_client_src(api_client_path: Path) -> Path | None:
    """Find the src/ directory in an api-client project."""
    api_client_path = api_client_path.resolve()
    for child in [api_client_path] + list(api_client_path.iterdir()):
        if child.is_dir() and (child / "src").is_dir():
            return child / "src"
    return None
