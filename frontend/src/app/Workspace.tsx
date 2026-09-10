// One screen. The chrome never changes; only the body does (IA_SPEC.md 1).
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { INITIAL, accepts, issue, navigate, ticket, type Authority } from "./authority";
import { SECTION_LABELS } from "./sections";
import { eventsUrl, openTail } from "./sse";
import { LedgerProvider } from "./ledger";
import { OFFLINE_WORDING, fetchSection, type RegionStatus } from "./transport";
import { SECTION_VIEWS } from "./views";
import { DecisionBrief } from "@/chrome/DecisionBrief";
import { Rail } from "@/chrome/Rail";
import { Ribbon } from "@/chrome/Ribbon";
import { SectionTabs } from "@/chrome/SectionTabs";
import { VerdictStrip } from "@/chrome/VerdictStrip";
import { fallbackChrome } from "@/chrome/fallback";
import { PageAlert } from "@/states/PageAlert";
import { RegionState } from "@/states/RegionState";
import type { AnyDocument, Section } from "@/wire";

const LOADING: RegionStatus = { kind: "loading" };

function documentOf(status: RegionStatus): AnyDocument | null {
  return "document" in status ? status.document : null;
}

interface Keyed<T> {
  key: string;
  value: T;
}

export function Workspace({ section }: { section: Section }) {
  const [params] = useSearchParams();
  const caseId = params.get("case");
  const caseSearch = caseId ? `?case=${encodeURIComponent(caseId)}` : "";
  const fixture = params.get("fixture");
  // Everything the reader sees is keyed on the request that produced it, so a
  // navigation shows `loading` without a render-time state write.
  const key = `${section}|${caseId ?? ""}|${fixture ?? ""}`;
  const [result, setResult] = useState<Keyed<RegionStatus> | null>(null);
  const [tabChoice, setTabChoice] = useState<Keyed<string> | null>(null);
  const authority = useRef<Authority>(INITIAL);
  // The key whose authority changed while its document was on the wire.
  const staleKey = useRef<string | null>(null);

  const load = useCallback(async () => {
    authority.current = issue(authority.current);
    const sent = ticket(authority.current);
    const next = await fetchSection(section, { case: caseId, fixture });
    // A late response, for a case the user has left or superseded by a later
    // request, is discarded, never rendered.
    if (!accepts(authority.current, sent)) return;
    const value: RegionStatus =
      staleKey.current === key && "document" in next && next.kind !== "stale"
        ? { kind: "stale", document: next.document }
        : next;
    setResult({ key, value });
  }, [section, caseId, fixture, key]);

  const reload = useCallback(() => {
    staleKey.current = null;
    void load();
  }, [load]);

  // The tail opens before the first fetch so a fixture stream's frame counter
  // is reset before the document it drives is read.
  useEffect(() => {
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
  }, [load, caseId, fixture, key]);

  useEffect(() => {
    authority.current = navigate(authority.current, caseId);
    void load();
  }, [load, caseId]);

  const status = result?.key === key ? result.value : LOADING;
  const document = documentOf(status);
  const chrome = document?.chrome ?? null;
  const activeTab =
    (tabChoice?.key === key ? tabChoice.value : null) ?? chrome?.tabs[0]?.id ?? null;
  const View = SECTION_VIEWS[section];
  // With no document there is still a section: the bands carry its state.
  const fallback = fallbackChrome(status);

  return (
    <div className="ap" data-section={section}>
      <Ribbon ribbon={(chrome ?? fallback).ribbon} subject={chrome?.subject ?? null} />
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
          entries={chrome?.rail ?? null}
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
