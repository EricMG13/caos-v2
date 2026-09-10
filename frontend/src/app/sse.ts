// The run-event tail. Name-only: the client reads `event.type` and refetches
// the section document; it never renders an event payload. `authority_changed`
// marks the region stale until the refetch lands.
export const EVENT_NAMES = [
  "node_state_changed",
  "attempt_recorded",
  "gate_opened",
  "run_terminal",
  "source_withdrawn",
  "authority_changed",
] as const;
export type EventName = (typeof EVENT_NAMES)[number];

export interface Tail {
  close(): void;
}

export interface TailHandlers {
  onEvent(name: EventName): void;
  onStale(): void;
}

export function eventsUrl(caseId: string | null, fixture: string | null): string {
  const params = new URLSearchParams();
  if (caseId) params.set("case", caseId);
  if (fixture) params.set("fixture", fixture);
  const search = params.toString();
  return `/api/events${search ? `?${search}` : ""}`;
}

export function openTail(url: string, handlers: TailHandlers): Tail {
  if (typeof EventSource === "undefined") return { close() {} };
  const source = new EventSource(url);
  for (const name of EVENT_NAMES) {
    source.addEventListener(name, () => {
      if (name === "authority_changed") handlers.onStale();
      handlers.onEvent(name);
    });
  }
  // A finite stream says so; the client closes rather than reconnecting forever.
  source.addEventListener("stream_end", () => source.close());
  return { close: () => source.close() };
}
