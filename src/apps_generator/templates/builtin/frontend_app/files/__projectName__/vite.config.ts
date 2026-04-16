import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { federation } from "@module-federation/vite";

export default defineConfig({
  plugins: [
    react(),
    federation({
      name: "{{ projectName | camel_case }}",
      filename: "remoteEntry.js",
      exposes: {
        "{{ exposedModule }}": "./src/App.tsx",
      },
      shared: {
        react: { singleton: true, requiredVersion: "^18.0.0" },
        "react-dom": { singleton: true, requiredVersion: "^18.0.0" },
      },
    }),
  ],
  server: {
    port: {{ devPort }},
    origin: "http://localhost:{{ devPort }}",
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
});
