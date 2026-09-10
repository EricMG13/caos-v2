import { expect, test } from "@playwright/test";

const FIELDS = [
  "definition",
  "period",
  "scenario",
  "evidence_date",
  "computed_at",
  "snapshot",
  "method",
  "derivation",
  "citations",
  "supporting_research",
];

test("a Book cell opens the ten-field passport and Escape returns focus", async ({ page }) => {
  await page.goto("/book/");
  const cell = page.locator("table.cases button.cellbtn[data-passport-id]").first();
  await cell.click();
  const passport = page.locator("[data-passport]");
  await expect(passport).toBeVisible();
  for (const field of FIELDS) {
    await expect(passport.locator(`[data-passport-field='${field}']`)).toHaveCount(1);
  }
  await page.keyboard.press("Escape");
  await expect(passport).toHaveCount(0);
  await expect(cell).toBeFocused();
});

test("a projected Model cell carries its driver and the driver's evidence", async ({ page }) => {
  await page.goto("/model/");
  await page.locator("table.proj button.cellbtn[data-passport-id]").first().click();
  const passport = page.locator("[data-passport]");
  await expect(passport).toBeVisible();
  for (const field of FIELDS) {
    await expect(passport.locator(`[data-passport-field='${field}']`)).toHaveCount(1);
  }
  await expect(passport.locator("[data-passport-field='driver'] [data-chip]")).toHaveCount(1);
});
