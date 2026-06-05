import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 3000,
    host: "0.0.0.0",
    allowedHosts: ["drop-kit.app", "dropkit.me", "localhost"],
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
    watch: {
      ignored: ["**/node_modules/**", "**/.git/**", "**/build/**", "**/dist/**"],
    },
  },
  build: {
    outDir: "build",
    sourcemap: false,
  },
});