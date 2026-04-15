{% raw %}
import { Link, useRouterState } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import type { RemotePage } from "../types";
import { RemoteAppLoader } from "./RemoteAppLoader";

interface RemoteAppLayoutProps {
  remoteName: string;
  pages: RemotePage[];
  currentPage: string;
}

export function RemoteAppLayout({ remoteName, pages, currentPage }: RemoteAppLayoutProps) {
  const { t } = useTranslation();
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const basePath = `/${remoteName}/${currentPage}`;

  return (
    <div className="flex flex-1 overflow-hidden h-full">
      {pages.length > 0 && (
        <aside className="w-48 bg-background border-r shrink-0 overflow-y-auto">
          <nav className="flex flex-col py-3">
            {pages.map((page) => {
              const pagePath = `/${remoteName}/${page.path}`;
              const isActive = currentPath === pagePath || currentPath.startsWith(pagePath + "/");
              // Try translation key "nav.<remoteName>.<pagePath>", fallback to label
              const label = t(`nav.${remoteName}.${page.path}`, { defaultValue: page.label });

              return (
                <Link
                  key={page.path}
                  to={pagePath}
                  className={`px-4 py-2 text-sm ${
                    isActive
                      ? "bg-accent text-accent-foreground font-medium border-r-2 border-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  }`}
                >
                  {page.icon && <span className="mr-2">{page.icon}</span>}
                  {label}
                </Link>
              );
            })}
          </nav>
        </aside>
      )}
      <div className="flex-1 overflow-auto p-6">
        <RemoteAppLoader remoteName={remoteName} activePage={currentPage} basePath={basePath} />
      </div>
    </div>
  );
}
{% endraw %}
