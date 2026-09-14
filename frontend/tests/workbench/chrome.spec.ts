import { expect, test, type Page } from "@playwright/test";
import { DISABLED_SECTIONS, SECTIONS, sectionRoute } from "../../scripts/fixture-routes.mjs";

// Directory and Upload read the v1 wire as of slice 4.1h; `composeChrome`
// (brief 4.1, decision 5) composes an empty `ribbon.actions` for every v1
// section, because 4.1 offers no action. Run and Analysis still read the
// legacy wire, with their fixtures' own primary action, until slices 4.1i-j.
const V1_SECTIONS = ["directory", "upload", "run"];

/** The API paths a page asked for while it loaded. */
function apiRequests(page: Page): string[] {
  const seen: string[] = [];
  page.on("request", (request) => {
    const { pathname } = new URL(request.url());
    if (pathname.startsWith("/api/")) seen.push(pathname);
  });
  return seen;
}

for (const section of SECTIONS) {
  const disabled = DISABLED_SECTIONS.includes(section);
  test(`${section}: the four bands sit above the body in order, one nav, served role read-only`, async ({
    page,
  }) => {
    const requests = apiRequests(page);
    await page.goto(sectionRoute(section, disabled ? "reader" : null));
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
    const demo = page.getByRole("complementary", { name: "Demonstration mode" });
    await expect(demo).toContainText("READ-ONLY DEMONSTRATION");
    await expect(demo).toContainText("NOTHING IS PERSISTED");
    for (const off of DISABLED_SECTIONS) {
      await expect(page.locator(`nav a[data-section='${off}']`)).toContainText("Unavailable");
    }
    if (disabled) {
      // Disabled in every mode, demo included: no document, no request, no tail.
      await expect(page.locator("main#body [data-surface-state='unavailable']")).toHaveCount(1);
      await expect(page.locator("[data-served-role]")).toHaveCount(0);
      await expect(page.locator("header.ribbon [data-primary]")).toHaveCount(0);
      expect(requests).toEqual([]);
      return;
    }
    const role = page.locator("[data-served-role]");
    await expect(role).toHaveCount(1);
    await expect(role.locator("button, a, select, input")).toHaveCount(0);
    // A v1 section's composed ribbon offers no action (brief 4.1, decision
    // 5); a still-legacy section keeps its fixture's one primary action.
    const primaryCount = V1_SECTIONS.includes(section) ? 0 : 1;
    await expect(page.locator("header.ribbon [data-primary]")).toHaveCount(primaryCount);
  });
}

test("a case section with no case is unavailable and sends no request", async ({ page }) => {
  const requests = apiRequests(page);
  await page.goto("/analysis/");
  await expect(page.locator("main#body [data-surface-state='unavailable']")).toHaveCount(1);
  expect(requests).toEqual([]);
});
