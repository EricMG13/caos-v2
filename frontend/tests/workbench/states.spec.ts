import { expect, test } from "@playwright/test";

test("offline is one page-level sentence and never engine text", async ({ page }) => {
  await page.goto("/analysis/?fixture=offline");
  const alert = page.locator("[data-page-alert]");
  await expect(alert).toHaveCount(1);
  await expect(alert).toHaveText("The request did not reach the server.");
  await expect(page.getByText("The request did not reach the server.")).toHaveCount(1);
  await expect(page.locator("main#body [data-surface-state='offline']")).toHaveCount(1);
  await expect(page.locator("body")).not.toContainText(/TypeError|Failed to fetch|ECONNRESET/);
});

test("observed-empty is timestamped and never inferred", async ({ page }) => {
  await page.goto("/book/?fixture=observed-empty");
  const region = page.locator("main#body [data-surface-state='observed-empty']");
  await expect(region).toBeVisible();
  await expect(region.locator("time[datetime]")).toHaveCount(1);
});

test("a typed refusal shows its code and what clears it", async ({ page }) => {
  await page.goto("/analysis/?fixture=error");
  const region = page.locator("main#body [data-surface-state='error']");
  await expect(region).toContainText("STORE_UNAVAILABLE");
  await expect(region).toContainText("Clears when");
});

test("partial renders through warning status with its notes and the body", async ({ page }) => {
  await page.goto("/analysis/?fixture=partial");
  await expect(page.locator("main#body [data-surface-state='partial']")).toBeVisible();
  await expect(page.locator("table.fin[data-financials]")).toBeVisible();
});

test("an authority change marks the region stale until an explicit reload", async ({ page }) => {
  await page.goto("/analysis/?fixture=stale");
  const stale = page.locator("main#body [data-surface-state='stale']");
  await expect(stale).toBeVisible({ timeout: 10_000 });
  await stale.getByRole("button", { name: "RELOAD" }).click();
  await expect(stale).toHaveCount(0);
});
