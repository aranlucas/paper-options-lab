// Run with the installed Playwright CLI:
// playwright-cli --session paper-options run-code --filename tests/browser_qa.js
async (page) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));

  const check = (value, label) => {
    if (!value) throw new Error(label);
  };

  await page.goto("http://127.0.0.1:8792");
  await page.getByText("6 eligible", { exact: true }).waitFor({ state: "visible" });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.getByRole("button", { name: "Call spreads", exact: true }).click();
  check((await page.locator(".spread-table tbody tr").count()) === 3, "Call filter");
  await page
    .getByRole("button", { name: "Call 100 / 105 1 spread · ×100 · Nov 1", exact: true })
    .click();
  check(
    await page.getByRole("heading", { name: "Call 100 / 105", exact: true }).isVisible(),
    "Spread inspector",
  );
  check(
    await page
      .locator(".detail-sub")
      .innerText()
      .then((t) => t.includes("European cash settlement")),
    "Exercise and settlement metadata",
  );
  const before = await page.locator(".scenario-readout").innerText();
  await page.getByRole("slider", { name: "Hypothetical settlement value" }).focus();
  await page.keyboard.press("ArrowRight");
  check((await page.locator(".scenario-readout").innerText()) !== before, "Payoff slider");
  await page.getByLabel("Show rejected", { exact: true }).check();
  check((await page.locator(".spread-table tbody tr").count()) > 3, "Rejected toggle");

  const rejected = page
    .locator(".spread-table tr")
    .filter({ has: page.locator(".rejected") })
    .first();

  await rejected.getByRole("button").click();
  check(
    await page.getByRole("heading", { name: "Why it was rejected" }).isVisible(),
    "Rejection inspector",
  );
  await page.getByLabel("Max loss / position ($)", { exact: true }).fill("50");
  check(
    (await page.getByRole("alert").innerText()) ===
      "Inputs changed. Compare again to apply the new limits.",
    "Invalidates old risk results",
  );
  check((await page.locator(".spread-table tbody tr").count()) === 1, "Clears old candidates");
  await page.getByRole("button", { name: "Compare & replay", exact: true }).click();
  await page.getByText("0 eligible", { exact: true }).waitFor({ state: "visible" });
  check(
    await page
      .locator(".ledger tbody")
      .innerText()
      .then((t) => !t.includes("opened")),
    "Risk budget blocks paper opens",
  );
  await page.getByLabel("Max loss / position ($)", { exact: true }).fill("500");
  await page.getByRole("button", { name: "Compare & replay", exact: true }).click();
  await page.getByText("6 eligible", { exact: true }).waitFor({ state: "visible" });
  await page.getByLabel("Dataset", { exact: true }).selectOption("pending");
  await page
    .getByText("Settlement or close pending", { exact: true })
    .waitFor({ state: "visible" });
  check(
    await page
      .locator(".provenance")
      .innerText()
      .then((t) => t.includes("Equity is unreported")),
    "Unresolved equity withheld",
  );
  await page.getByLabel("Dataset", { exact: true }).selectOption("stale");
  await page.getByText("0 eligible", { exact: true }).waitFor({ state: "visible" });
  check(
    await page
      .locator(".ledger tbody")
      .innerText()
      .then((t) => t.includes("stale quote")),
    "Stale data fails closed",
  );
  await page.locator("input[type=file]").setInputFiles("fixtures/rally.json");
  await page.getByText("6 eligible", { exact: true }).waitFor({ state: "visible" });
  check(
    (await page.getByLabel("Dataset", { exact: true }).inputValue()) === "imported",
    "Local JSON import",
  );
  await page.getByLabel("Show rejected", { exact: true }).uncheck();
  await page.getByRole("button", { name: "All spreads", exact: true }).click();
  await page
    .getByRole("button", { name: "Call 100 / 105 1 spread · ×100 · Nov 1", exact: true })
    .click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export dataset", exact: true }).click();
  const download = await downloadPromise;
  check(download.suggestedFilename().endsWith(".json"), "Dataset export");
  await page.getByLabel("Dataset", { exact: true }).selectOption("rally");
  await page.getByText("6 eligible", { exact: true }).waitFor({ state: "visible" });
  await page
    .getByRole("button", { name: "Call 100 / 105 1 spread · ×100 · Nov 1", exact: true })
    .click();
  await page.screenshot({ path: "output/playwright/desktop.png", fullPage: false });
  await page.screenshot({ path: "output/playwright/desktop-full.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  check(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    "Mobile page overflow",
  );
  await page.screenshot({ path: "output/playwright/mobile.png" });
  await page.locator(".inspector").scrollIntoViewIfNeeded();
  await page.screenshot({ path: "output/playwright/mobile-payoff.png" });
  check(
    await page.getByRole("slider", { name: "Hypothetical settlement value" }).isVisible(),
    "Mobile payoff",
  );
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.evaluate(() => window.scrollTo(0, 0));
  check(errors.length === 0, `Browser errors: ${errors.join("; ")}`);

  return { passed: true, checks: 17, desktop: "1440×1050", mobile: "390×844", pageErrors: errors };
};
