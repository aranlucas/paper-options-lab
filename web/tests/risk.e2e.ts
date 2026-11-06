import { test } from "@e2e-dev/web";
import { expect } from "e2e";

test("risk limit blocks paper opens and recovers after correction", async ({
  app,
  screen,
  browser,
}) => {
  await app.open("/");
  await expect(screen.getByText("6 eligible", { exact: true })).toBeVisible();
  await screen.getByLabel("Max loss / position ($)", { exact: true }).fill("50");
  await expect(screen.getByRole("alert")).toHaveText(
    "Inputs changed. Compare again to apply the new limits.",
  );
  await screen.getByRole("button", "Compare & replay").click();
  await expect(screen.getByText("0 eligible", { exact: true })).toBeVisible();
  await expect(browser.locator(".ledger tbody")).not.toContainText("opened");
  await expect(browser.locator(".ledger tbody")).toContainText("position risk limit");
  await screen.getByLabel("Max loss / position ($)", { exact: true }).fill("500");
  await screen.getByRole("button", "Compare & replay").click();
  await expect(screen.getByText("6 eligible", { exact: true })).toBeVisible();
  await expect(browser.locator(".ledger tbody")).toContainText("opened");
  await expect(browser.locator(".ledger tbody")).toContainText("settled");
});
