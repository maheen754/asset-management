import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server: reachable from phones on the LAN (host: true) and forwards
// API + photo requests to the Flask backend, so no CORS setup is needed.
const BACKEND = process.env.VITE_BACKEND || "http://localhost:5000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": BACKEND,
      "/uploads": BACKEND,
    },
  },
});