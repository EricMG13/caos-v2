import { expect, test } from "@playwright/test";
import { SECTIONS } from "../../scripts/fixture-routes.mjs";

for (const section of SECTIONS) {
  test(`${section}: the four bands sit above the body in order, one nav, served role read-only`, async ({
    page,
  }) => {
    await page.goto(`/${section}/`);
    await expect(page.locator("main#body [data-surface-state='loading']")).toHaveCount(0);
    const bands = page.locator("header.ribbon, section.brief, section.tabs, section.verdict");
    await expect(bands).toHaveCount(4);
    const order = await bands.evaluateAll((nodes) =>
      nodes.map((node) => node.className.split(" ")[0]),
    );
    expect(order).toEqual(["ribbon", "brief", "tabs", "verdict"]);
    // The bands precede the frame in DOM order.
    const framePreceded = await page.evaluate(() => {
      const frame = document.querySelector(".frame");
      const verdict = document.querySelector(".verdict");
      return Boolean(
        frame &&
        verdict &&
        verdict.compareDocumentPosition(frame) & Node.DOCUMENT_POSITION_FOLLOWING,
      );
    });
    expect(framePreceded).toBe(true);
    await expect(page.locator("nav")).toHaveCount(1);
    const role = page.locator("[data-served-role]");
    await expect(role).toHaveCount(1);
    await expect(role.locator("button, a, select, input")).toHaveCount(0);
    // Exactly one primary action in the ribbon.
    await expect(page.locator("header.ribbon [data-primary]")).toHaveCount(1);
  });
}
