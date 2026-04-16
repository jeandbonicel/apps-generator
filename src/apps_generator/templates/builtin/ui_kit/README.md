# ui-kit

Shared UI component library built with shadcn/ui, Tailwind CSS, and Storybook. Provides consistent components and design tokens across all micro-frontends and the platform shell.

## What it generates

A React component library that:
- Pre-installs **shadcn/ui** components (Button, Card, Badge, Input, Dialog, Table, Alert, Select, Tabs)
- Includes **Toast** components (Toast, ToastTitle, ToastDescription) with variants and a Toaster context
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
import { Toaster, useToast } from "my-ui-kit";
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
Button, Card (CardHeader, CardTitle, CardDescription, CardContent, CardFooter), Badge, Input, Label, Dialog (DialogPortal, DialogOverlay, DialogClose, DialogTrigger, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription), Table (TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption), Alert (AlertTitle, AlertDescription), Select (SelectGroup, SelectValue, SelectTrigger, SelectContent, SelectLabel, SelectItem, SelectSeparator), Tabs (TabsList, TabsTrigger, TabsContent)

### Toast Components

The toast system provides non-intrusive notification messages with three parts:

- **Toast** -- the container element with variant styling (`default`, `destructive`, `success`), close button, and animation
- **ToastTitle** -- bold title text within a toast
- **ToastDescription** -- description text within a toast

Variants:
- `default` -- neutral border and background
- `destructive` -- red/destructive styling for errors
- `success` -- green styling for success messages

### Toaster

The **Toaster** component provides a context-based toast notification system:

- Wrap your app (or a subtree) with `<Toaster>` to enable toast notifications
- Call `useToast()` from any child component to get the `toast()` function
- Toasts render in a portal at the bottom-right of the viewport
- Each toast auto-dismisses after 5 seconds (configurable via `duration`)

```tsx
import { Toaster, useToast } from "my-ui-kit";

function App() {
  return (
    <Toaster>
      <MyContent />
    </Toaster>
  );
}

function MyContent() {
  const { toast } = useToast();

  return (
    <button onClick={() => toast({
      title: "Saved",
      description: "Your changes have been saved.",
      variant: "success",
    })}>
      Save
    </button>
  );
}
```

The `toast()` function accepts:
- `title` (optional) -- bold heading
- `description` (required) -- body text
- `variant` (optional) -- `"default"`, `"destructive"`, or `"success"`
- `duration` (optional) -- milliseconds before auto-dismiss (default: 5000)

### Layout Components
- `<Page>` -- max-width + padding + vertical section gap
- `<PageHeader title="..." description="...">` -- title + actions
- `<PageSection title="...">` -- section with consistent spacing
- `<PageGrid columns={3}>` -- responsive grid

### Utilities
- `cn()` -- class name merge utility (clsx + tailwind-merge)
- `buttonVariants` -- CVA variants for Button
- `badgeVariants` -- CVA variants for Badge
- `toastVariants` -- CVA variants for Toast

## Exports

The full list of exports from `src/index.ts`:

```typescript
// UI Components
Button, buttonVariants, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,
Badge, badgeVariants, Input, Label, Dialog, DialogPortal, DialogOverlay, DialogClose,
DialogTrigger, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription,
Table, TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption,
Alert, AlertTitle, AlertDescription, Select, SelectGroup, SelectValue, SelectTrigger,
SelectContent, SelectLabel, SelectItem, SelectSeparator, Tabs, TabsList, TabsTrigger, TabsContent,
Toast, ToastTitle, ToastDescription, toastVariants, Toaster, useToast,

// Layout
Page, PageHeader, PageSection, PageGrid,

// Utilities
cn
```

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
