import { pages } from "./pages";
import "./i18n";

export interface AppProps {
  activePage?: string;
  tenantId?: string;
  basePath?: string;
}

/**
 * Root component exposed as the Module Federation remote module.
 *
 * With @module-federation/vite, React is shared as a singleton —
 * hooks (useState, useEffect, etc.) work correctly across the
 * Module Federation boundary.
 *
 * - `activePage`: which page section to render (from shell's vertical sidebar)
 * - `basePath`: the URL prefix this MFE is mounted at (e.g., "/orders/list")
 */
export default function App({ activePage, basePath = "/" }: AppProps = {}) {
  const PageComponent = (activePage && pages[activePage]) || pages["default"];

  // Store basePath on window for the lightweight MFE router
  (window as unknown as Record<string, unknown>).__MFE_BASE_PATH__ = basePath;

  return (
    <div className="app-root">
      {PageComponent ? <PageComponent /> : <p>Page not found</p>}
    </div>
  );
}
