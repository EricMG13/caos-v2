import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { EvidenceProvider } from "@/evidence/EvidenceContext";
import { AdminSection } from "@/sections/admin/AdminSection";
import type { DocumentOf } from "@/wire";

const fixture: DocumentOf<"admin"> = JSON.parse(
  readFileSync(resolve(process.cwd(), "fixtures/admin.json"), "utf8"),
);

function mount(document: DocumentOf<"admin">) {
  return render(
    <MemoryRouter>
      <EvidenceProvider>
        <AdminSection document={document} tab={null} />
      </EvidenceProvider>
    </MemoryRouter>,
  );
}

describe("Admin", () => {
  test("test_admin_names_what_is_missing", () => {
    const { container } = mount(fixture);
    const region = container.querySelector<HTMLElement>("[data-unavailable-capability]");
    expect(region).not.toBeNull();
    expect(region).toHaveClass("unavail");
    expect(
      within(region!).getByRole("heading", { name: "Admin is unavailable in this deployment" }),
    ).toBeInTheDocument();
    expect(region!.querySelectorAll(".missing div")).toHaveLength(4);
    expect(within(region!).getAllByRole("listitem")).toHaveLength(fixture.body.missing.length);
    for (const item of fixture.body.missing) {
      expect(region).toHaveTextContent(item.name.split(" · ")[0]!);
      expect(region).toHaveTextContent(item.code);
    }
    // The unavailable state is shape and word, never hue alone.
    expect(region!.querySelector('[data-severity="WARNING"]')).toHaveAttribute(
      "data-shape",
      "triangle",
    );
  });

  test("admin does not pretend: no settings form, no toggles, no controls", () => {
    const { container } = mount(fixture);
    expect(container.querySelector("form")).toBeNull();
    expect(screen.queryAllByRole("switch")).toHaveLength(0);
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
    expect(screen.queryAllByRole("textbox")).toHaveLength(0);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(container.querySelector("[data-unavailable-capability]")).toHaveTextContent(
      "This deployment serves no administration route.",
    );
  });
});
