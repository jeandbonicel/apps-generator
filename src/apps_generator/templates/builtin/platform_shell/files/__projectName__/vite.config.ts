{% raw %}
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { federation } from "@module-federation/vite";
import { readFileSync } from "fs";

// Read remote apps from public/remotes.json at build time
let remotes: Record<string, { type: string; name: string; entry: string }> = {};
try {
  const remotesJson = JSON.parse(
    readFileSync("./public/remotes.json", "utf-8"),
  );
  for (const app of remotesJson) {
    remotes[app.name] = {
      type: "module",
      name: app.name,
      entry: `${app.url}/remoteEntry.js`,
    };
  }
} catch {
  // No remotes configured yet
}
{% endraw %}

export default defineConfig({
  plugins: [
    react(),
    federation({
      name: "host",
      remotes,
      shared: {
        react: { singleton: true, requiredVersion: "^18.0.0" },
        "react-dom": { singleton: true, requiredVersion: "^18.0.0" },
      },
    }),
  ],
  server: {
    port: {{ devPort }},
    proxy: {
      "{{ apiBaseUrl }}": {
        target: "http://localhost:{{ gatewayPort }}",
        changeOrigin: true,
      },
    },
  },
  build: {
    target: "chrome89",
  },
  test: {
    exclude: ["e2e/**", "node_modules/**"],
  },
});
