import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { pages } from "./pages";
import "./i18n";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

export interface AppProps {
  activePage?: string;
  tenantId?: string;
  basePath?: string;
}

/**
 * Root component exposed as the Module Federation remote module.
 * Wraps in QueryClientProvider so TanStack Query hooks work when
 * loaded via Module Federation (MFE has its own React instance).
 */
export default function App({ activePage, basePath = "/" }: AppProps = {}) {
  const { t } = useTranslation();
  const PageComponent = (activePage && pages[activePage]) || pages["default"];
  (window as unknown as Record<string, unknown>).__MFE_BASE_PATH__ = basePath;

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-root">
        {PageComponent ? <PageComponent /> : <p>{t("pageNotFound")}</p>}
      </div>
    </QueryClientProvider>
  );
}
