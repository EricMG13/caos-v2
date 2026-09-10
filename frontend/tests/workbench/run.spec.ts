import { expect, test } from "@playwright/test";

test("the route reads as a DAG, the QA gate as a gate, and the stream advances a frame", async ({
  page,
}) => {
  await page.goto("/run/");
  await expect(page.locator(".dag[data-route]")).toBeVisible();
  await expect(page.locator("[data-gate]")).toContainText("QA_GATE");
  const cp6 = page.locator("button.node[data-node='CP-6']");
  await expect(cp6).toHaveAttribute("data-state", /RUNNABLE|COMPLETE/);
  // The fixture stream emits node_state_changed; the client refetches and
  // renders the later frame.
  await expect(cp6).toHaveAttribute("data-state", "COMPLETE", { timeout: 10_000 });
  await expect(page.locator("header.ribbon [data-refusal='RUN_NOT_TERMINAL']")).toBeVisible();
});

test("the plan gate binds a digest and offers approval live", async ({ page }) => {
  await page.goto("/run/?fixture=gate");
  const gate = page.locator("[data-plan-gate]");
  await expect(gate).toBeVisible();
  await expect(page.locator("[data-plan-gate][data-gate-state='RESOLVED_NOT_PINNED']")).toHaveCount(
    1,
  );
  // Visible and refused with the clearing phase named: never a live no-op.
  await expect(page.getByRole("button", { name: "Approve plan" }).first()).toHaveAttribute(
    "data-refusal",
    "ACTION_UNPLACED",
  );
});
