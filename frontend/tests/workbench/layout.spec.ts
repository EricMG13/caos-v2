import { expect, test, type Locator } from "@playwright/test";

// Layout the unit suite cannot see: jsdom lays nothing out, so a label that runs
// into its neighbour or text cut through the middle of a line is only caught
// where an engine draws the page. Each test measures what a reader sees.

/** Words that fit on a line and were broken across two anyway, and whether the
    box is wider inside than out -- a token that overflowed rather than broke. */
function breakage(locator: Locator) {
  return locator.evaluate((root) => {
    const width = root.getBoundingClientRect().width;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let broken = 0;
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      for (const match of node.textContent!.matchAll(/\S+/g)) {
        const range = document.createRange();
        range.setStart(node, match.index);
        range.setEnd(node, match.index + match[0].length);
        const rects = [...range.getClientRects()].filter((rect) => rect.width > 0);
        const span = rects.reduce((sum, rect) => sum + rect.width, 0);
        if (rects.length > 1 && span <= width) broken += 1;
      }
    }
    return { broken, overflow: root.scrollWidth > root.clientWidth };
  });
}

/** How many lines an element's own text is drawn on. */
function lines(locator: Locator) {
  return locator.evaluate((el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    const tops = [...range.getClientRects()]
      .filter((rect) => rect.width > 0)
      .map((rect) => Math.round(rect.top));
    return new Set(tops).size;
  });
}

test("route stage headers stay in their columns and node reasons are never cut mid-line", async ({
  page,
}) => {
  await page.goto("/run/?fixture=gate");
  await expect(page.locator(".dag[data-route]")).toBeVisible();
  const layout = await page.evaluate(() => {
    const headers = [...document.querySelectorAll(".stagehdr")].map((header) =>
      header.getBoundingClientRect(),
    );
    const nodes = [...document.querySelectorAll("button.node")];
    const firstRow = Math.min(...nodes.map((node) => node.getBoundingClientRect().top));
    const overlaps = headers.slice(1).filter((header, i) => headers[i]!.right > header.left + 0.5);
    const crowding = headers.filter((header) => header.bottom > firstRow + 0.5);
    const clipped = nodes.filter((node) => {
      const why = node.querySelector(".why")!.getBoundingClientRect();
      return why.bottom > node.getBoundingClientRect().bottom + 0.5;
    });
    return {
      headers: headers.length,
      overlaps: overlaps.length,
      crowding: crowding.length,
      clipped: clipped.length,
    };
  });
  expect(layout.headers).toBeGreaterThan(1);
  expect(layout).toMatchObject({ overlaps: 0, crowding: 0, clipped: 0 });
});

test("prose wraps between words; only an unbroken token breaks anywhere", async ({ page }) => {
  await page.goto("/model/");
  const breach = page.locator("[data-breach='DOWNSIDE'] dd.wrap");
  await expect(breach).toBeVisible();
  expect(await breakage(breach)).toEqual({ broken: 0, overflow: false });
  await page.goto("/committee/?fixture=filed");
  const receipt = page.locator("[data-receipt]");
  await expect(receipt).toBeVisible();
  expect(await breakage(receipt)).toEqual({ broken: 0, overflow: false });
});

test("module ids and timestamps never wrap inside themselves", async ({ page }) => {
  await page.goto("/report/");
  const sources = page.locator(".secrow .src");
  await expect(sources.first()).toBeVisible();
  for (const source of await sources.all()) {
    expect(await lines(source)).toBe(1);
    // Nothing forces a wrap at this width; the rule is what holds at a narrower one.
    expect(await source.evaluate((el) => getComputedStyle(el).whiteSpace)).toBe("nowrap");
  }
  await page.goto("/upload/");
  const stamp = page.locator("tr.wd [data-withdrawal] time").first();
  await expect(stamp).toBeVisible();
  expect(await lines(stamp)).toBe(1);
  expect(await stamp.evaluate((el) => getComputedStyle(el).whiteSpace)).toBe("nowrap");
});
