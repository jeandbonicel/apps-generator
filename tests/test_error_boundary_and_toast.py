"""Tests for ErrorBoundary and ToastProvider generation in the shell template."""

import json
from pathlib import Path

from apps_generator.core.generator import generate
from apps_generator.templates.registry import resolve_template
from apps_generator.cli.generators.toast import generate_toast_provider
from apps_generator.cli.generators.linking import register_uikit, find_consumer_root


def _gen_shell(tmp_path: Path, name: str = "my-shell") -> Path:
    template = resolve_template("platform-shell")
    return generate(
        template_dir=template.path,
        output_dir=tmp_path / "sh",
        cli_values={"projectName": name},
        interactive=False,
    )


# ── ErrorBoundary ────────────────────────────────────────────────────────────

def test_shell_has_error_boundary(tmp_path: Path):
    """ErrorBoundary is always generated in the shell template."""
    result = _gen_shell(tmp_path)
    eb = result / "my-shell" / "src" / "shell" / "ErrorBoundary.tsx"
    assert eb.exists()
    content = eb.read_text()
    assert "class ErrorBoundary" in content
    assert "getDerivedStateFromError" in content
    assert "componentDidCatch" in content
    assert "Try again" in content


def test_error_boundary_wired_in_main(tmp_path: Path):
    """main.tsx wraps RouterProvider with ErrorBoundary."""
    result = _gen_shell(tmp_path)
    main = (result / "my-shell" / "src" / "main.tsx").read_text()
    assert "ErrorBoundary" in main
    assert "import { ErrorBoundary }" in main


# ── ToastProvider without ui-kit ─────────────────────────────────────────────

def test_toast_provider_builtin_version(tmp_path: Path):
    """Without --uikit, shell gets a self-contained toast (no external imports)."""
    result = _gen_shell(tmp_path)
    project_root = find_consumer_root(result, "my-shell")

    generate_toast_provider(project_root, has_uikit=False, uikit_name="")

    toast = project_root / "src" / "shell" / "ToastProvider.tsx"
    assert toast.exists()
    content = toast.read_text()

    # Self-contained: no ui-kit imports
    assert "my-ui-kit" not in content
    assert "useToast" in content
    assert "ToastProvider" in content
    assert "createContext" in content
    assert "createPortal" in content
    assert "role=\"alert\"" in content


def test_toast_provider_builtin_has_variants(tmp_path: Path):
    """Built-in toast supports default, destructive, and success variants."""
    result = _gen_shell(tmp_path)
    project_root = find_consumer_root(result, "my-shell")

    generate_toast_provider(project_root, has_uikit=False, uikit_name="")

    content = (project_root / "src" / "shell" / "ToastProvider.tsx").read_text()
    assert "destructive" in content
    assert "success" in content
    assert "default" in content


# ── ToastProvider with ui-kit ────────────────────────────────────────────────

def test_toast_provider_uikit_version(tmp_path: Path):
    """With --uikit, shell imports Toaster/useToast from the ui-kit package."""
    result = _gen_shell(tmp_path)
    project_root = find_consumer_root(result, "my-shell")

    generate_toast_provider(project_root, has_uikit=True, uikit_name="my-ui-kit")

    toast = project_root / "src" / "shell" / "ToastProvider.tsx"
    assert toast.exists()
    content = toast.read_text()

    assert 'from "my-ui-kit"' in content
    assert "Toaster" in content
    assert "useToast" in content


def test_toast_provider_not_overwritten(tmp_path: Path):
    """Generating ToastProvider twice doesn't overwrite the first version."""
    result = _gen_shell(tmp_path)
    project_root = find_consumer_root(result, "my-shell")

    generate_toast_provider(project_root, has_uikit=False, uikit_name="")
    content_v1 = (project_root / "src" / "shell" / "ToastProvider.tsx").read_text()

    # Second call with different params should NOT overwrite
    generate_toast_provider(project_root, has_uikit=True, uikit_name="my-ui-kit")
    content_v2 = (project_root / "src" / "shell" / "ToastProvider.tsx").read_text()

    assert content_v1 == content_v2  # unchanged


# ── ui-kit Toast component ───────────────────────────────────────────────────

def test_uikit_has_toast_components(tmp_path: Path):
    """ui-kit template generates Toast and Toaster components."""
    template = resolve_template("ui-kit")
    result = generate(
        template_dir=template.path,
        output_dir=tmp_path / "uikit",
        cli_values={"projectName": "my-ui-kit"},
        interactive=False,
    )

    project = result / "my-ui-kit"
    assert (project / "src" / "components" / "ui" / "toast.tsx").exists()
    assert (project / "src" / "components" / "ui" / "toaster.tsx").exists()

    # Toast has variants
    toast = (project / "src" / "components" / "ui" / "toast.tsx").read_text()
    assert "toastVariants" in toast
    assert "destructive" in toast
    assert "success" in toast

    # Toaster has context and portal
    toaster = (project / "src" / "components" / "ui" / "toaster.tsx").read_text()
    assert "useToast" in toaster
    assert "createPortal" in toaster

    # Exported from index.ts
    index = (project / "src" / "index.ts").read_text()
    assert "Toast" in index
    assert "Toaster" in index
    assert "useToast" in index


# ── Integration: shell with --uikit ──────────────────────────────────────────

def test_shell_with_uikit_gets_uikit_toast(tmp_path: Path):
    """Full integration: generate shell + uikit, link them, verify toast imports from uikit."""
    uikit_template = resolve_template("ui-kit")
    uikit_dir = generate(
        template_dir=uikit_template.path,
        output_dir=tmp_path / "uikit",
        cli_values={"projectName": "my-ui-kit"},
        interactive=False,
    )

    shell_dir = _gen_shell(tmp_path, "test-shell")
    consumer = find_consumer_root(shell_dir, "test-shell")

    uikit_name = register_uikit(uikit_path=uikit_dir, consumer_root=consumer)
    assert uikit_name == "my-ui-kit"

    generate_toast_provider(consumer, has_uikit=True, uikit_name=uikit_name)

    toast = (consumer / "src" / "shell" / "ToastProvider.tsx").read_text()
    assert 'from "my-ui-kit"' in toast
