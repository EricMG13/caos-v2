import { expect, test } from "@playwright/test";

test("Escape returns focus to the chip that opened the drawer", async ({ page }) => {
  await page.goto("/analysis/");
  const chip = page.locator("[data-chip='D-04 p.68 ¶2']").first();
  await chip.click();
  const drawer = page.locator("[data-evidence-drawer]");
  await expect(drawer).toBeVisible();
  await expect(drawer).toHaveAttribute("aria-modal", "true");
  await expect(drawer.locator("img")).toHaveAttribute("src", /D-04-p68\.svg$/);
  await expect(drawer.locator(".bbox")).toHaveCount(1);
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(chip).toBeFocused();
});
