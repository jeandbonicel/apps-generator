import {
  createRouter,
  createRootRoute,
  createRoute,
  redirect,
} from "@tanstack/react-router";
import { AppShell } from "./layout/AppShell";
import { HomePage } from "./routes/index";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { RemoteAppLayout } from "./layout/RemoteAppLayout";
import { RemoteAppLoader } from "./layout/RemoteAppLoader";
import { getRemotes } from "./config/remotes";

const rootRoute = createRootRoute({
  component: ProtectedRoute,
});

const shellRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "shell",
  component: AppShell,
});

const indexRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/",
  component: HomePage,
});

export function createAppRouter() {
  const remoteApps = getRemotes();

  const remoteRoutes = remoteApps.flatMap((app) => {
    const pages = app.pages ?? [];

    if (pages.length === 0) {
      // No pages — single wildcard route, no sidebar
      return [
        createRoute({
          getParentRoute: () => shellRoute,
          path: `/${app.name}/$`,
          component: () => (
            <div className="p-6">
              <RemoteAppLoader remoteName={app.name} basePath={`/${app.name}`} />
            </div>
          ),
        }),
      ];
    }

    // Redirect /{app} to first page
    const parentRedirect = createRoute({
      getParentRoute: () => shellRoute,
      path: `/${app.name}`,
      beforeLoad: () => {
        throw redirect({ to: `/${app.name}/${pages[0].path}` });
      },
    });

    // Wildcard route per page — catches /{app}/{page}, /{app}/{page}/123, etc.
    const pageRoutes = pages.map((page) =>
      createRoute({
        getParentRoute: () => shellRoute,
        path: `/${app.name}/${page.path}/$`,
        component: () => (
          <RemoteAppLayout
            remoteName={app.name}
            pages={pages}
            currentPage={page.path}
          />
        ),
      }),
    );

    return [parentRedirect, ...pageRoutes];
  });

  const routeTree = rootRoute.addChildren([
    shellRoute.addChildren([indexRoute, ...remoteRoutes]),
  ]);

  return createRouter({ routeTree });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
