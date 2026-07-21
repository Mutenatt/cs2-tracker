import { defineConfig } from "@playwright/test";

// Config minima para el driver de verificación visual (e2e/verify.mjs).
// No corre en CI -- es una herramienta de auto-verificación manual para
// comparar cada vista nueva/cambiada contra el mockup aprobado antes de
// dar una fase por terminada. Requiere backend (cs2-api) + frontend
// (npm run dev) ya corriendo en :8000 / :5173.
export default defineConfig({
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1280, height: 900 },
  },
});
