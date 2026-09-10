import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { UNAVAILABLE_WORDING, classify, fetchSection, sectionUrl } from "@/app/transport";
import { PINNED_KEYS, keysMatch } from "@/wire/keys";
import { SECTIONS } from "@/wire";

const FIXTURES = `${resolve(process.cwd(), "fixtures")}/`;

function fixture(name: string): Record<string, unknown> {
  return JSON.parse(readFileSync(`${FIXTURES}${name}`, "utf8"));
}

describe("the wire", () => {
  test("test_wire_pinned_keys_match_fixtures", () => {
    const documents = [
      ...SECTIONS.map((section) => `${section}.json`),
      ...readdirSync(`${FIXTURES}states`).map((name) => `states/${name}`),
      ...readdirSync(`${FIXTURES}run/frames`).map((name) => `run/frames/${name}`),
    ];
    expect(documents.length).toBeGreaterThanOrEqual(9);
    for (const name of documents) {
      const document = fixture(name);
      expect(keysMatch(document), name).toBe(true);
      expect(
        Object.keys(document).every((key) => (PINNED_KEYS as readonly string[]).includes(key)),
      ).toBe(true);
    }
  });

  test("a document with a key outside the pinned set is refused", () => {
    const document = fixture("admin.json");
    const status = classify({ ...document, widget: {} });
    expect(status).toEqual({
      kind: "error",
      refusal: { code: "WIRE_KEYS_MISMATCH", clears: expect.any(String) },
    });
    expect(
      classify({ ...document, chrome: { ...(document["chrome"] as object), extra: 1 } }).kind,
    ).toBe("error");
  });

  test("test_observed_empty_requires_timestamp", () => {
    const document = fixture("admin.json");
    expect(classify({ ...document, observed_empty: true, observed_at: "" })).toMatchObject({
      kind: "error",
      refusal: { code: "OBSERVED_EMPTY_UNTIMED" },
    });
    expect(classify({ ...document, observed_empty: true })).toMatchObject({
      kind: "observed-empty",
      observed_at: document["observed_at"],
    });
  });

  test("partial renders through warning status with its notes", () => {
    const document = fixture("admin.json");
    expect(
      classify({ ...document, status: "partial", notes: ["CP-3 not accepted"] }),
    ).toMatchObject({
      kind: "partial",
      notes: ["CP-3 not accepted"],
    });
  });
});

describe("the transport", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("a request that never reached the server is offline, with no engine text", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    expect(await fetchSection("analysis", {})).toEqual({ kind: "offline" });
  });

  test("an observed 404 is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 404 })));
    expect(await fetchSection("analysis", { case: "private" })).toEqual({ kind: "unavailable" });
    expect(UNAVAILABLE_WORDING).toBe("Unavailable or not permitted.");
  });

  test("any other non-2xx is a typed refusal, never exception text", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(new Response("Traceback (most recent call last)", { status: 500 }))
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({ code: "STORE_UNAVAILABLE", clears: "The store answers." }),
            {
              status: 503,
            },
          ),
        ),
    );
    const opaque = await fetchSection("run", {});
    expect(opaque).toEqual({
      kind: "error",
      refusal: { code: "RESPONSE_INVALID", clears: expect.any(String) },
    });
    expect(JSON.stringify(opaque)).not.toContain("Traceback");
    expect(await fetchSection("run", {})).toEqual({
      kind: "error",
      refusal: { code: "STORE_UNAVAILABLE", clears: "The store answers." },
    });
  });

  test("the fixture parameter travels with the request", () => {
    expect(sectionUrl("committee", { case: "C-1", fixture: "reader" })).toBe(
      "/api/sections/committee?case=C-1&fixture=reader",
    );
    expect(sectionUrl("committee", {})).toBe("/api/sections/committee");
  });
});
