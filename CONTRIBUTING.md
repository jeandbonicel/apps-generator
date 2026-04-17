# Contributing to Apps Generator

Thank you for your interest in contributing. This guide covers how to set up your development environment, run tests, and submit changes.

## Prerequisites

- Python 3.11+
- Node.js 20+ (for testing generated projects)
- Docker (for integration tests and docker-compose generation)
- Git

## Development Setup

```bash
# Clone the repo
git clone https://github.com/jeandbonicel/apps-generator.git
cd apps-generator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
make install
# or: pip install -e ".[dev]"

# (Optional) Install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Running Checks

```bash
make ci          # Run all checks (lint + typecheck + test)
make test        # Run tests only
make lint        # Run ruff linter
make typecheck   # Run mypy type checker
make format      # Auto-format code with ruff
make clean       # Remove caches and build artifacts
```

## Pull Request Process

1. **Fork** the repository and create a branch from `main`
2. **Make your changes** — add tests for new features
3. **Run `make ci`** — all checks must pass
4. **Push** your branch and open a Pull Request
5. Fill in the PR template checklist
6. Wait for CI to pass and a maintainer to review

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new field type support for UUID
fix: resolve table alignment in generated list pages
docs: update getting-started guide with dashboard example
chore: update ruff to v0.6
refactor: extract page generators into separate module
test: add translation completeness tests
```

## Code Style

- **Linter:** ruff (configured in `pyproject.toml`)
- **Line length:** 120 characters
- **Python version:** 3.11+ (type hints, `match` statements OK)
- **Formatting:** ruff format (run `make format`)

## Template Development

When modifying template files in `src/apps_generator/templates/builtin/`:

- **Jinja2 syntax:** Use `{{ variable }}` for template variables, `{% if condition %}` for conditionals
- **JSX files:** Wrap files that use JSX `{{ }}` patterns in `{% raw %}` / `{% endraw %}` to prevent Jinja2 conflicts
- **Conditional files:** Use `.conditions.yaml` to include/exclude files based on feature flags
- **Filename variables:** Use `__variableName__` or `__variableName|filter__` patterns
- **Parameter schemas:** Update `parameters-schema.json` AND `parameters-defaults.yaml` when adding new parameters

## Translations

All UI strings must be translated. Currently supported: **English (en)** and **French (fr)**.

- Shell translations: `platform_shell/.../src/i18n/locales/{en,fr}.json`
- Frontend translations: `frontend_app/.../src/i18n/locales/{en,fr}.json`
- Use `t("keyName")` in components, never hardcode English strings
- Run `pytest tests/test_translations.py` to verify completeness
- Tests will **fail** if you add an EN key without a matching FR key

## Adding a New Template

1. Create a directory in `src/apps_generator/templates/builtin/<template-name>/`
2. Add `manifest.yaml`, `parameters-schema.json`, `parameters-defaults.yaml`
3. Add template files in `files/`
4. Register in `templates/registry.py`
5. Add tests in `tests/`
6. Add a README.md for the template

## Branch Protection

The `main` branch is protected:
- All PRs require passing CI checks
- Direct pushes to main are not allowed
- PRs should be reviewed before merging

## Questions?

Open a [Discussion](https://github.com/jeandbonicel/apps-generator/discussions) or an [Issue](https://github.com/jeandbonicel/apps-generator/issues).
