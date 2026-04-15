import { Link, useRouterState } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { getRemotes } from "../config/remotes";

export function AppTabs() {
  const { t } = useTranslation();
  const remoteApps = getRemotes();
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;

  return (
    <nav className="flex items-center gap-1 px-4 bg-background border-b shrink-0">
      <Link
        to="/"
        className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
          currentPath === "/"
            ? "border-primary text-primary"
            : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
        }`}
      >
        {t("home")}
      </Link>
      {remoteApps.map((app) => {
        const isActive = currentPath.startsWith(`/${app.name}`);
        const defaultPath = app.pages && app.pages.length > 0
          ? `/${app.name}/${app.pages[0].path}`
          : `/${app.name}`;

        return (
          <Link
            key={app.name}
            to={defaultPath}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              isActive
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`}
          >
            {app.menuIcon && <span className="mr-1.5">{app.menuIcon}</span>}
            {app.menuLabel}
          </Link>
        );
      })}
    </nav>
  );
}
