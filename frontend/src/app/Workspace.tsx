// One screen. The chrome never changes; only the body does (IA_SPEC.md 1).
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { INITIAL, accepts, issue, navigate, refetches, ticket, type Authority } from "./authority";
import { SECTION_LABELS, isEnabledSection } from "./sections";
import { eventsUrl, openTail } from "./sse";
import { LedgerProvider } from "./ledger";
import { OFFLINE_WORDING, fetchSection, sectionUrl, type RegionStatus } from "./transport";
import { SECTION_VIEWS } from "./views";
import { DecisionBrief } from "@/chrome/DecisionBrief";
import { Rail } from "@/chrome/Rail";
import { Ribbon } from "@/chrome/Ribbon";
import { SectionTabs } from "@/chrome/SectionTabs";
import { VerdictStrip } from "@/chrome/VerdictStrip";
import { composeChrome, markDisabled } from "@/chrome/compose";
import { fallbackChrome } from "@/chrome/fallback";
import { PageAlert } from "@/states/PageAlert";
import { RegionState } from "@/states/RegionState";
import type { Chrome, Section } from "@/wire";

const LOADING: RegionStatus = { kind: "loading" };
const UNAVAILABLE: RegionStatus = { kind: "unavailable" };

/** The chrome composed for a v1 document. A disabled section never fetches,
    so it never reaches here with a document to compose from. */
function chromeOf(section: Section, status: RegionStatus): Chrome | null {
  if (!("document" in status)) return null;
  return isEnabledSection(section) ? composeChrome(section, status.document) : null;
}

interface Keyed<T> {
  key: string;
  value: T;
}

export function Workspace({ section }: { section: Section }) {
  const [params] = useSearchParams();
  const caseId = params.get("case");
  const caseSearch = caseId ? `?case=${encodeURIComponent(caseId)}` : "";
  const runId = params.get("run");
  const fixture = import.meta.env.MODE === "demo" ? params.get("fixture") : null;
  // A disabled section, or a case section with no case, sends no request and
  // opens no tail: it is `unavailable` in every mode (brief 4.1, decision 9).
  const requested = sectionUrl(section, { case: caseId, run: runId, fixture }) !== null;
  // Everything the reader sees is keyed on the request that produced it, so a
  // navigation shows `loading` without a render-time state write.
  const key = `${section}|${caseId ?? ""}|${runId ?? ""}|${fixture ?? ""}`;
  const [result, setResult] = useState<Keyed<RegionStatus> | null>(null);
  const [tabChoice, setTabChoice] = useState<Keyed<string> | null>(null);
  const authority = useRef<Authority>(INITIAL);

  useEffect(() => {
    if (!requested) return undefined;
    authority.current = navigate(authority.current, caseId);
    // At most one fetch in flight; a name arriving mid-flight marks it dirty
    // and exactly one more fetch follows (decision 5).
    let flight: { controller: AbortController; dirty: boolean } | null = null;
    const put = (value: RegionStatus) => setResult({ key, value });

    const load = () => {
      if (flight) {
        flight.dirty = true;
        return;
      }
      const mine = { controller: new AbortController(), dirty: false };
      flight = mine;
      authority.current = issue(authority.current);
      const sent = ticket(authority.current);
      void fetchSection(
        section,
        { case: caseId, run: runId, fixture },
        mine.controller.signal,
      ).then((next) => {
        // A late response, for a case or run the user has left, is discarded.
        if (!accepts(authority.current, sent)) return;
        flight = null;
        put(next);
        if (mine.dirty) load();
      });
    };
    const cancel = () => {
      flight?.controller.abort();
      flight = null;
      authority.current = issue(authority.current);
    };

    // Directory has no stream. The tail opens before the first fetch so a
    // fixture stream's frame counter is reset before the document it drives.
    const tail =
      caseId && section !== "directory"
        ? openTail(eventsUrl(caseId, runId, fixture), {
            onEvent: (name) => {
              if (refetches(name, section)) load();
            },
            onReconnect: load,
            // A closed stream is a refusal or, in Firefox, a connection that
            // never opened: EventSource cannot tell them apart. The document
            // read can, so it decides: 404 unavailable, no connection offline.
            onRefused: load,
          })
        : null;
    load();
    return () => {
      tail?.close();
      cancel();
    };
  }, [requested, section, caseId, runId, fixture, key]);

  const status = requested ? (result?.key === key ? result.value : LOADING) : UNAVAILABLE;
  const chrome = chromeOf(section, status);
  const activeTab =
    (tabChoice?.key === key ? tabChoice.value : null) ?? chrome?.tabs[0]?.id ?? null;
  const View = SECTION_VIEWS[section];
  // With no document there is still a section: the bands carry its state.
  const fallback = fallbackChrome(status);

  return (
    <div className="ap" data-section={section}>
      <Ribbon
        ribbon={(chrome ?? fallback).ribbon}
        subject={chrome?.subject ?? null}
        tabs={chrome?.tabs.map((tab) => tab.id)}
        onTab={(id) => setTabChoice({ key, value: id })}
      />
      <DecisionBrief brief={(chrome ?? fallback).brief} />
      <SectionTabs
        label={SECTION_LABELS[section]}
        tabs={chrome?.tabs ?? []}
        active={activeTab}
        onSelect={(id) => setTabChoice({ key, value: id })}
      />
      <VerdictStrip verdict={(chrome ?? fallback).verdict} />
      <div className="frame">
        <Rail
          section={section}
          entries={markDisabled(chrome?.rail ?? null)}
          local={chrome?.rail_local ?? null}
          servedRole={chrome?.served_role ?? null}
          search={caseSearch}
        />
        <main className="body" id="body" aria-label={SECTION_LABELS[section]}>
          {status.kind === "offline" ? <PageAlert sentence={OFFLINE_WORDING} /> : null}
          <LedgerProvider>
            <RegionState status={status}>
              {(doc) => <View key={doc.observed_at} document={doc} tab={activeTab} />}
            </RegionState>
          </LedgerProvider>
        </main>
      </div>
    </div>
  );
}
