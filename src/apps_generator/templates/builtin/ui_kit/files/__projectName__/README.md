# {{ projectTitle or projectName }}

Shared UI component library built with [shadcn/ui](https://ui.shadcn.com), Tailwind CSS, and Storybook.

## Development

```bash
npm install
npm run dev        # Storybook at http://localhost:6006
npm run build      # Build library to dist/
```

## Adding more components

```bash
npx shadcn@latest add accordion checkbox dropdown-menu
```

Then export from `src/index.ts` and create a story in `stories/`.

## Usage in other projects

Generated projects link to this library via the `--uikit` flag:

```bash
appgen generate frontend-app -o ./my-app --shell ./shell --uikit .
```

Then import components:

```tsx
import { Button, Card, Badge } from "{{ projectName }}";
```
