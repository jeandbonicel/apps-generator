import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
{% if features.tailwind %}
import "./index.css";
{% endif %}

/**
 * Standalone bootstrap — used when running this micro-frontend
 * independently (npm run dev) rather than loaded via the platform shell.
 *
 * In standalone mode, basePath="/" so the entire URL path is the sub-path.
 * Navigate to /123 in dev mode to test the same route as /orders/list/123 in the shell.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App basePath="/" />
    </QueryClientProvider>
  </React.StrictMode>,
);
