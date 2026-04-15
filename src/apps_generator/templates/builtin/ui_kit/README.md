# ui-kit

Shared UI component library built with shadcn/ui, Tailwind CSS, and Storybook. Provides consistent components and design tokens across all micro-frontends and the platform shell.

## What it generates

A React component library that:
- Pre-installs **shadcn/ui** components (Button, Card, Badge, Input, Dialog, Table, Alert, Select, Tabs)
- Includes **layout components** (Page, PageHeader, PageSection, PageGrid) for consistent spacing
- Exports a **Tailwind preset** with shared design tokens (colors, spacing, border radius)
- Includes **Storybook** for component development and documentation
- Builds as an ESM library (Vite library mode)
- Deployable Storybook (Docker, K8s)
- Versionable npm package (GitHub Packages or npmjs.com)

## Usage

```bash
# Generate the UI kit
appgen generate ui-kit -o ./ui-kit -s projectName=my-ui-kit

# Link to shell and MFEs
appgen generate platform-shell -o ./shell -s projectName=my-platform --uikit ./ui-kit
appgen generate frontend-app -o ./orders -s projectName=orders --shell ./shell --uikit ./ui-kit
```

Then import components:
```tsx
import { Button, Card, Badge, Page, PageHeader, PageGrid } from "my-ui-kit";
```

## Development

```bash
cd my-ui-kit
npm install
npm run dev              # Storybook at http://localhost:6006
npm run build            # Build library to dist/
npm run build-storybook  # Build Storybook static site
```

## Adding more shadcn components

```bash
npx shadcn@latest add accordion checkbox dropdown-menu
```

Then export from `src/index.ts` and create a story in `stories/`.

## Components

### UI Components (shadcn/ui)
Button, Card, Badge, Input, Label, Dialog, Table, Alert, Select, Tabs

### Layout Components
- `<Page>` — max-width + padding + vertical section gap
- `<PageHeader title="..." description="...">` — title + actions
- `<PageSection title="...">` — section with consistent spacing
- `<PageGrid columns={3}>` — responsive grid

## Versioning

```bash
npm run release          # Bump patch + publish
npm run release:minor    # Bump minor + publish
npm run release:major    # Bump major + publish

# Or via git tags (CI publishes automatically)
git tag v0.2.0 && git push --tags
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `projectName` **(required)** | -- | Package name (kebab-case) |
| `primaryColor` | `blue` | shadcn color theme |
| `npmRegistry` | `github` | Publish to `github` (GitHub Packages) or `npm` (npmjs.com) |
| `nodeVersion` | `20` | Node.js version |
| `packageManager` | `pnpm` | npm, pnpm, or yarn |
