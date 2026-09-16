import { expect, test } from "@playwright/test";

test("the rail is the only navigation and reaches all nine sections", async ({ page }) => {
  await page.goto("/directory/");
  const links = page.locator("nav a[data-section]");
  await expect(links).toHaveCount(9);
  await links.filter({ hasText: "Committee" }).click();
  await expect(page).toHaveURL(/\/committee\/$/);
  await expect(page.locator("nav a[aria-current='page']")).toHaveAttribute(
    "data-section",
    "committee",
  );
  await expect(page.locator("main#body [data-surface-state='unavailable']")).toHaveCount(1);
});

test("command-K opens nothing", async ({ page }) => {
  await page.goto("/analysis/");
  await page.keyboard.press("ControlOrMeta+KeyK");
  await expect(page.locator("[role='dialog']")).toHaveCount(0);
});

test("a pre-v2 slug forwards with its query intact and history replaced", async ({ page }) => {
  await page.goto("/directory/");
  // `commit`, not the default `load`: the slug forwards itself as soon as the
  // document runs, so waiting for the load event of a page that is already
  // being replaced is a race. WebKit lost it twice under CI load, timing out
  // in `goto` at 30s. The assertion below polls, so nothing is given up.
  await page.goto("/deepdive/?case=CASE-2026-CVNA01", { waitUntil: "commit" });
  await expect(page).toHaveURL(/\/analysis\/\?case=CASE-2026-CVNA01$/);
  await page.goBack();
  // The forward replaced history: back lands on the entry before the slug.
  await expect(page).toHaveURL(/\/directory\/$/);
});

test("an absent route shares the private-404 wording", async ({ page }) => {
  await page.goto("/nothing/");
  await expect(page.locator("main#body")).toContainText("Unavailable or not permitted.");
  await page.goto("/analysis/?case=CASE-2026-CVNA01&fixture=unavailable");
  await expect(page.locator("main#body")).toContainText("Unavailable or not permitted.");
});

test("demo fixture HTTP is read-only before fixture selection", async ({ request }) => {
  const get = await request.get("/api/v1/directory");
  expect(get.status()).toBe(200);
  expect(await get.json()).toHaveProperty("chrome");
  const run = await request.get("/api/v1/cases/CASE-2026-CVNA01/run");
  expect(run.status()).toBe(200);
  // Only the v1 paths of the four enabled sections are served.
  for (const path of ["/api/sections/directory", "/api/v1/cases/CASE-2026-CVNA01/book"]) {
    expect((await request.get(path)).status(), path).toBe(404);
  }

  const post = await request.post("/api/v1/directory?fixture=../../directory");
  expect(post.status()).toBe(405);
  expect(post.headers()["allow"]).toBe("GET, HEAD");
  expect(await post.json()).toEqual({
    code: "READ_ONLY_DEMO",
    clears: "a real API handles commands",
  });
});
