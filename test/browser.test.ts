import { chromium } from "playwright-core";
import { expect, it, vi } from "vitest";
import { readFile } from "node:fs/promises";
import browserQA from "./browser-qa.test.js";

it.skipIf(!process.env.BROWSER_TEST)(
  "dashboard interactions and stale import isolation",
  async () => {
    await vi.waitFor(
      async () => {
        expect((await fetch("http://127.0.0.1:8792/api/health")).ok).toBe(true);
      },
      { timeout: 10000 },
    );
    const browser = await chromium.launch({ headless: true });

    try {
      const page = await browser.newPage();
      await browserQA(page);
      const rally = await readFile(new URL("../fixtures/rally.json", import.meta.url));
      await page.evaluate((content) => {
        File.prototype.text = function () {
          return new Promise<string>((resolve) => {
            document.addEventListener(
              "release-import",
              () => {
                resolve(content);
              },
              { once: true },
            );
          });
        };
      }, rally.toString());
      await page.locator("input[type=file]").setInputFiles({
        name: "slow.json",
        mimeType: "application/json",
        buffer: rally,
      });
      await page.getByLabel("Dataset", { exact: true }).selectOption("stale");
      await expect.poll(() => page.locator(".ledger tbody").innerText()).toContain("stale quote");
      await page.evaluate(async () => {
        document.dispatchEvent(new Event("release-import"));
        await new Promise<void>((resolve) => {
          requestAnimationFrame(() => resolve());
        });
      });
      expect(await page.getByLabel("Dataset", { exact: true }).inputValue()).toBe("stale");
      await page.getByRole("button", { name: "Compare & replay", exact: true }).click();
      await page.getByText("0 eligible", { exact: true }).waitFor();
      expect(await page.locator(".ledger tbody").innerText()).toContain("stale quote");
    } finally {
      await browser.close();
    }
  },
  60000,
);
