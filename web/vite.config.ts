import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// A porta 5173 (padrao do Vite) ja esta na allowlist de CORS da API (api/settings.py).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
