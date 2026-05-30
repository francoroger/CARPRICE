import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // proxy para o backend evita configurar CORS/URL no front
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
