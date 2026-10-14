import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { tsconfigPaths: true },
  test: { include: ["../test/**/*.test.ts"], environment: "node", maxWorkers: 1 },
});
