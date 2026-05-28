import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite dev-server configuration for the React frontend.
// /api calls are proxied to the local Express backend on port 5000.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:5000",
    },
  },
});
