# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-04-17

### Added
- Enum field type with Java enums, TypeScript union types, and `<select>` dropdowns in forms
- Smart form generation: datetime picker, resource lookups (e.g. `dogName` auto-detects `dog` resource and renders dropdown), "Create one first" message when lookup is empty
- Auto-build shared libs during linking (no manual `pnpm build` needed before Docker)
- ESLint v9 flat config for frontend-app and platform-shell templates
- PostgreSQL service container in api-domain CI workflow for Testcontainers

### Fixed
- Git init now runs at inner project directory (not outer wrapper directory)
- Page generator uses actual api-client package name from `--api-client` flag (was hardcoded as `my-api-client`)
- Gradle wrapper stubs replaced with real Gradle 8.8 wrapper (jar + properties)
- YAML workflow templates use `{{ '...' }}` instead of `{% raw %}{% endraw %}` (fixes Jinja2 `trim_blocks` eating newlines)
- CI workflows trigger on push to `main` AND `master` (was PR-only)
- Null-safe list page rendering for decimal, date, and string fields (shows "—" for null)
- Module Federation MFE builds use `minify: false` to fix React shared module variable mangling
- `.gitignore` ordering: `!gradle/wrapper/gradle-wrapper.jar` exception now comes after `*.jar` rule

## [0.1.0] - 2026-04-17

### Added

- 6 built-in templates: platform-shell, frontend-app, api-domain, api-gateway, api-client, ui-kit
- CRUD resource generation from JSON schema (`--resources` parameter)
- TypeScript type generation from resource definitions (`--api-client` on api-domain)
- Data-aware page generation: list (table + pagination), form (create/edit), dashboard (stats + charts)
- Hibernate `@Filter` for ORM-level tenant isolation via TenantAwareEntity
- Correlation ID tracing across shell, gateway, and backend services
- Security headers on shell nginx (CSP, X-Frame-Options), MFE nginx, and gateway
- Error boundary for MFE crash recovery with "Try again" UI
- Toast notification system (shadcn version with ui-kit, lightweight fallback without)
- 26 shadcn/ui components in ui-kit including Recharts chart wrappers
- Testcontainers integration tests generated per resource
- `appgen sync types` command to regenerate TypeScript types from OpenAPI spec
- `appgen docker-compose` to auto-generate docker-compose.yaml from workspace
- Full EN/FR i18n support with translation completeness tests
- ShellContextSync for window global sync (auth token + tenant ID)
- DevSecurityConfig (@Profile("local")) for development without OIDC provider
- 89+ automated tests covering all generators, templates, and translations
- Comprehensive documentation: 9 guides in docs/, CLAUDE.md for AI context
- `/create-app` Claude Code skill for supervisor workflow
- 23 Storybook stories for all ui-kit components
