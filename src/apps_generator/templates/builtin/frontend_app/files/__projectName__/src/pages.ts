import type { ComponentType } from "react";
import { HomePage } from "./routes/HomePage";

/**
 * Page registry — maps page path names to components.
 * When the shell passes `activePage`, this lookup determines what renders.
 * The "default" key is used when no activePage is specified (standalone mode).
 *
 * New pages are added here automatically by the CLI when using --pages,
 * or you can add them manually.
 */
export const pages: Record<string, ComponentType> = {
  default: HomePage,
};
