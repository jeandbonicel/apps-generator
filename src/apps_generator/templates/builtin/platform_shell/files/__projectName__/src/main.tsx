import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { init } from "@module-federation/enhanced/runtime";
import "./i18n";
{% if authProvider == "clerk" %}
import { ClerkProvider } from "@clerk/clerk-react";
{% else %}
import { AuthProvider } from "./auth/AuthProvider";
import { TenantProvider } from "./tenants/TenantProvider";
{% endif %}
import { loadRemotes, getRemotes } from "./config/remotes";
import { createAppRouter } from "./router";
{% if features.tailwind %}
import "./index.css";
{% endif %}

{% if authProvider == "clerk" %}
const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "{{ clerkPublishableKey }}";
{% endif %}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Load remote config then initialize Module Federation runtime
loadRemotes().then(() => {
  const remoteApps = getRemotes();

  // Initialize Module Federation runtime with dynamic remotes
  if (remoteApps.length > 0) {
    init({
      name: "host",
      remotes: remoteApps.map((app) => ({
        name: app.name,
        entry: `${app.url}/remoteEntry.js`,
      })),
    });
  }

  const router = createAppRouter();

  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
{% if authProvider == "clerk" %}
        <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
          <RouterProvider router={router} />
        </ClerkProvider>
{% else %}
        <AuthProvider>
          <TenantProvider>
            <RouterProvider router={router} />
          </TenantProvider>
        </AuthProvider>
{% endif %}
      </QueryClientProvider>
    </React.StrictMode>,
  );
});
