import { expect, test } from "@playwright/test";

test("the residual is its own column and unavailability propagates forward", async ({ page }) => {
  await page.goto("/model/");
  const downside = page.locator("table.proj[data-projection][data-case='DOWNSIDE']");
  await expect(downside).toBeVisible();
  await expect(downside.locator("th.resid")).toHaveCount(1);
  const unavailable = downside.locator("tr.unav[data-reason]");
  await expect(unavailable).toHaveCount(1);
  await expect(unavailable).toContainText(/tolerance/i);
  const propagated = downside.locator("tr.prop[data-propagated='true']");
  expect(await propagated.count()).toBeGreaterThan(0);
  // A propagated period names its origin and never reads as a number.
  const text = (await propagated.first().innerText()).trim();
  expect(text).toMatch(/propagated/i);
  expect(text).not.toMatch(/^\S*\d[\d,.]*\s*$/m);
  await expect(page.locator("table.proj[data-case='BASE'] tr.unav")).toHaveCount(0);
});
