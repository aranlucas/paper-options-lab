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
      let releaseFixture: () => void = () => {};
      const fixtureHeld = new Promise<void>((resolve) => {
        releaseFixture = resolve;
      });
      let fixtureRequested: () => void = () => {};
      const requested = new Promise<void>((resolve) => {
        fixtureRequested = resolve;
      });
      await page.route("**/api/fixture/flat", async (route) => {
        fixtureRequested();
        await fixtureHeld;
        await route.continue();
      });
      await page.getByLabel("Dataset", { exact: true }).selectOption("flat");
      await requested;
      await page.getByLabel("Max loss / position ($)", { exact: true }).fill("50");
      releaseFixture();
      const compare = page.getByRole("button", { name: "Compare & replay", exact: true });
      await expect.poll(() => compare.isEnabled()).toBe(true);
      await compare.click();
      await page.getByText("0 eligible", { exact: true }).waitFor();
      expect(await page.locator(".ledger tbody").innerText()).toContain("position risk limit");
      await page.getByLabel("Max loss / position ($)", { exact: true }).fill("500");
      await page.getByLabel("Dataset", { exact: true }).selectOption("rally");
      await page.getByText("6 eligible", { exact: true }).waitFor();
      let releaseInvalidImportFixture: () => void = () => {};
      const invalidImportFixtureHeld = new Promise<void>((resolve) => {
        releaseInvalidImportFixture = resolve;
      });
      let invalidImportFixtureRequested: () => void = () => {};
      const invalidImportRequested = new Promise<void>((resolve) => {
        invalidImportFixtureRequested = resolve;
      });
      await page.unroute("**/api/fixture/flat");
      await page.route("**/api/fixture/flat", async (route) => {
        invalidImportFixtureRequested();
        await invalidImportFixtureHeld;
        await route.continue();
      });
      await page.getByLabel("Dataset", { exact: true }).selectOption("flat");
      await invalidImportRequested;
      await page.locator("input[type=file]").setInputFiles({
        name: "invalid.json",
        mimeType: "application/json",
        buffer: Buffer.from("{"),
      });
      await expect.poll(() => page.getByRole("alert").innerText()).toContain("JSON");
      releaseInvalidImportFixture();
      await expect.poll(() => compare.isEnabled()).toBe(false);
      await page.getByLabel("Dataset", { exact: true }).selectOption("rally");
      await page.getByText("6 eligible", { exact: true }).waitFor();
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
