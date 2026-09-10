import { expect, test } from "@playwright/test";

test("a READER sees the filing control visible, refused, with its code", async ({ page }) => {
  await page.goto("/committee/?fixture=reader");
  await expect(page.locator("[data-served-role]")).toHaveAttribute("data-served-role", "READER");
  const file = page.locator(".ladder button[data-refusal='APPROVER_NOT_INDEPENDENT']");
  await expect(file).toBeVisible();
  await expect(file).toHaveAttribute("aria-disabled", "true");
  await expect(file).not.toHaveAttribute("disabled", /.*/);
  await expect(
    page.locator(".ladder .refusal[data-refusal='APPROVER_NOT_INDEPENDENT']"),
  ).toContainText("APPROVER_NOT_INDEPENDENT");
});

test("the signer sees the same refusal; a filed deliverable shows its receipt", async ({
  page,
}) => {
  await page.goto("/committee/");
  await expect(page.locator("[data-watermark]")).toHaveText("DRAFT — NOT FILED");
  await expect(
    page.locator(".ladder button[data-refusal='APPROVER_NOT_INDEPENDENT']"),
  ).toBeVisible();
  await page.goto("/committee/?fixture=filed");
  await expect(page.locator("[data-watermark]")).toHaveCount(0);
  await expect(page.locator(".rd-stamp")).toBeVisible();
  await expect(page.locator(".receipt")).toBeVisible();
});
