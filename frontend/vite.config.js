import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Proxy /api -> backend FastAPI en dev, para evitar CORS y hardcodear puertos.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: function (p) {
          return p.replace(/^\/api/, "");
        },
      },
    },
  },
});
