// The workspace under events (brief 4.4, decisions 2 and 5): which names
// refetch, one fetch in flight, reconnects, refusals and late responses.
import { readFileSync } from "node:fs";
import { act, fireEvent, render } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router";
import { Workspace } from "@/app/Workspace";
import type { Section } from "@/wire";

const text = (path: string): string => readFileSync(new URL(path, import.meta.url), "utf8");
const json = (path: string): Record<string, unknown> => JSON.parse(text(path));

const CASE = "00000000-0000-4000-8000-000000000001";
const OTHER = "00000000-0000-4000-8000-0000000000ff";
const analysis = () => json("../../fixtures/analysis.json");
const otherCase = () => JSON.parse(text("../../fixtures/analysis.json").replaceAll(CASE, OTHER));

class FakeSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  static all: FakeSource[] = [];
  readonly listeners = new Map<string, () => void>();
  readyState = FakeSource.CONNECTING;
  closed = false;
  constructor(readonly url: string) {
    FakeSource.all.push(this);
  }
  addEventListener(name: string, handler: () => void) {
    this.listeners.set(name, handler);
  }
  close() {
    this.closed = true;
    this.readyState = FakeSource.CLOSED;
  }
}

interface Sent {
  url: string;
  signal: AbortSignal | undefined;
  answer(body: unknown, status?: number): void;
}
let sent: Sent[] = [];

beforeEach(() => {
  sent = [];
  FakeSource.all = [];
  vi.stubGlobal("EventSource", FakeSource);
  vi.stubGlobal(
    "fetch",
    (url: string, init?: RequestInit) =>
      new Promise<Response>((resolve) => {
        sent.push({
          url,
          signal: init?.signal ?? undefined,
          answer: (body, status = 200) => resolve(new Response(JSON.stringify(body), { status })),
        });
      }),
  );
});
afterEach(() => vi.unstubAllGlobals());

const settle = () => act(() => new Promise((resolve) => setTimeout(resolve, 0)));

async function answer(index: number, body: unknown, status = 200) {
  sent[index]!.answer(body, status);
  await settle();
}

async function fire(name: string) {
  const source = FakeSource.all.at(-1)!;
  act(() => source.listeners.get(name)?.());
  await settle();
}

function SwitchCase() {
  const go = useNavigate();
  return (
    <button type="button" data-switch onClick={() => go(`/analysis/?case=${OTHER}`)}>
      switch
    </button>
  );
}

async function mount(section: Section, path: string) {
  const view = render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="*"
          element={
            <>
              <Workspace section={section} />
              <SwitchCase />
            </>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
  await settle();
  return view;
}

const region = (container: HTMLElement) => container.querySelector("main#body")!;
const confidence = (container: HTMLElement) =>
  region(container).querySelector("[data-confidence]")?.textContent ?? null;

describe("the workspace under its event tail", () => {
  test("test_an_event_refetches_only_the_sections_it_names", async () => {
    await mount("upload", `/upload/?case=${CASE}`);
    expect(sent).toHaveLength(1);
    await answer(0, json("../../fixtures/upload.json"));
    expect(FakeSource.all[0]!.url).toBe(`/api/v1/cases/${CASE}/events`);
    for (const name of ["run_progress", "handoff_accepted", "run_terminal", "runs_changed"]) {
      await fire(name);
    }
    expect(sent).toHaveLength(1);
    await fire("sources_changed");
    expect(sent).toHaveLength(2);
  });

  test("an analysis workspace ignores run progress and refetches on an accepted handoff", async () => {
    await mount("analysis", `/analysis/?case=${CASE}`);
    await answer(0, analysis());
    await fire("run_progress");
    expect(sent).toHaveLength(1);
    await fire("handoff_accepted");
    expect(sent).toHaveLength(2);
  });

  test("test_names_arriving_mid_flight_cause_exactly_one_more_fetch", async () => {
    await mount("analysis", `/analysis/?case=${CASE}`);
    await fire("handoff_accepted");
    await fire("run_terminal");
    await fire("sources_changed");
    expect(sent).toHaveLength(1);
    await answer(0, analysis());
    expect(sent).toHaveLength(2);
    await answer(1, analysis());
    expect(sent).toHaveLength(2);
  });

  test("test_a_reconnect_refetches_the_visible_documents", async () => {
    await mount("analysis", `/analysis/?case=${CASE}`);
    await answer(0, analysis());
    await fire("open");
    expect(sent).toHaveLength(1);
    FakeSource.all[0]!.readyState = FakeSource.CONNECTING;
    await fire("error");
    await fire("open");
    expect(sent).toHaveLength(2);
  });

  test("test_a_refused_reconnect_closes_the_tail_and_the_region_is_unavailable", async () => {
    const { container } = await mount("analysis", `/analysis/?case=${CASE}`);
    await answer(0, analysis());
    expect(confidence(container)).not.toBeNull();
    FakeSource.all[0]!.readyState = FakeSource.CLOSED;
    await fire("error");
    expect(FakeSource.all[0]!.closed).toBe(true);
    expect(region(container).querySelector("[data-surface-state='unavailable']")).not.toBeNull();
    expect(confidence(container)).toBeNull();
  });

  test("test_a_late_response_after_a_case_switch_is_discarded", async () => {
    const { container } = await mount("analysis", `/analysis/?case=${CASE}`);
    const first = sent[0]!;
    const firstTail = FakeSource.all[0]!;
    act(() => fireEvent.click(container.querySelector("[data-switch]")!));
    await settle();
    expect(first.signal?.aborted).toBe(true);
    expect(firstTail.closed).toBe(true);
    expect(FakeSource.all.at(-1)!.url).toBe(`/api/v1/cases/${OTHER}/events`);
    const other = otherCase();
    other.body.handoffs[0].confidence_score = 7;
    await answer(1, other);
    expect(confidence(container)).toMatch(/^7 /);
    // The left case answers late: discarded, never rendered.
    await answer(0, analysis());
    expect(confidence(container)).toMatch(/^7 /);
    expect(region(container).querySelector("[data-surface-state]")).toBeNull();
  });
});
