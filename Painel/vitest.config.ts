import { defineConfig } from "vitest/config";
import path from "path";
import { fileURLToPath } from "url";

const currentDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      reportsDirectory: "./coverage",
      exclude: [
        "coverage/**",
        "dist/**",
        "e2e/**",
        "*.config.*",
        "lighthouserc.cjs",
        "src/test/**",
        "src/**/*.d.ts",
        "src/main.tsx",
        "src/components/ui/**",
      ],
    },
  },
  resolve: {
    alias: { "@": path.resolve(currentDir, "./src") },
  },
});
