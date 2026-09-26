/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // The browser talks to the same origin; Vite forwards /api to FastAPI.
    // No CORS configuration is needed in development.
    proxy: {
      "/api": process.env.API_PROXY_TARGET ?? "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // Playwright specs live in e2e/ and run with `npm run test:e2e`.
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      include: ["src/**"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/test/**", "src/main.tsx"],
      // Same floor as the backend; CI fails below it.
      thresholds: { lines: 80, statements: 80, functions: 80, branches: 75 },
    },
  },
});
