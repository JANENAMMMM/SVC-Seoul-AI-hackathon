import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8130,
    proxy: {
      "/api": "http://127.0.0.1:8131",
      "/health": "http://127.0.0.1:8131",
    },
  },
  build: { outDir: "dist" },
});
