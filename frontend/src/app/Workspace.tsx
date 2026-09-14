// One screen. The chrome never changes; only the body does (IA_SPEC.md 1).
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { INITIAL, accepts, issue, navigate, ticket, type Authority } from "./authority";
import { SECTION_LABELS, isEnabledSection } from "./sections";
import { eventsUrl, openTail } from "./sse";
import { LedgerProvider } from "./ledger";
import {
  OFFLINE_WORDING,
  fetchSection,
  sectionUrl,
  type RegionStatus,
  type WorkspaceDocument,
} from "./transport";
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
import type { SectionDocument as V1Document } from "@/wire/v1";

const LOADING: RegionStatus = { kind: "loading" };
const UNAVAILABLE: RegionStatus = { kind: "unavailable" };

/** The legacy chrome a document carries, or the one composed for a v1 document. */
function chromeOf(section: Section, status: RegionStatus): Chrome | null {
  if (!("document" in status)) return null;
  const { document } = status;
  if (!isV1(document)) return document.chrome;
  return isEnabledSection(section) ? composeChrome(section, document) : null;
}

function isV1(document: WorkspaceDocument): document is V1Document {
  return !("ribbon" in document.chrome);
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
  // The key whose authority changed while its document was on the wire.
  const staleKey = useRef<string | null>(null);

  const load = useCallback(async () => {
    authority.current = issue(authority.current);
    const sent = ticket(authority.current);
    const next = await fetchSection(section, { case: caseId, run: runId, fixture });
    // A late response, for a case the user has left or superseded by a later
    // request, is discarded, never rendered.
    if (!accepts(authority.current, sent)) return;
    const value: RegionStatus =
      staleKey.current === key && "document" in next && next.kind !== "stale"
        ? { kind: "stale", document: next.document }
        : next;
    setResult({ key, value });
  }, [section, caseId, runId, fixture, key]);

  const reload = useCallback(() => {
    staleKey.current = null;
    void load();
  }, [load]);

  // The tail opens before the first fetch so a fixture stream's frame counter
  // is reset before the document it drives is read.
  useEffect(() => {
    if (!requested) return undefined;
    const tail = openTail(eventsUrl(caseId, fixture), {
      onEvent: (name) => {
        if (name !== "authority_changed") void load();
      },
      onStale: () => {
        staleKey.current = key;
        setResult((current) => {
          if (!current || current.key !== key) return current;
          const status = current.value;
          return "document" in status && status.kind !== "stale"
            ? { key: current.key, value: { kind: "stale", document: status.document } }
            : current;
        });
      },
    });
    return () => tail.close();
  }, [load, requested, caseId, fixture, key]);

  useEffect(() => {
    authority.current = navigate(authority.current, caseId);
    if (requested) void load();
  }, [load, requested, caseId]);

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
            <RegionState status={status} onReload={reload}>
              {(doc) => <View key={doc.observed_at} document={doc} tab={activeTab} />}
            </RegionState>
          </LedgerProvider>
        </main>
      </div>
    </div>
  );
}
