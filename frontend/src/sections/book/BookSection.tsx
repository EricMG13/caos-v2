// Book, /book/ (IA_SPEC.md 4.4): the portfolio, compared honestly. Left, the
// facets and grouping; centre, the book table or the comparison, by tab.
// Selecting any cell opens the passport with its opener passed.
import { useEffect, useState } from "react";
import { CasesTable } from "./CasesTable";
import { Compare } from "./Compare";
import { Facets } from "./Facets";
import { useLedger } from "@/app/ledger";
import type { ViewProps } from "@/app/views";
import type { Refusal } from "@/wire";
import { useEvidence } from "@/evidence/EvidenceContext";
import type { Facet } from "@/wire/book";

type Checked = Record<string, ReadonlySet<string>>;

/** The served `on` flags are the filter at rest. */
function initialChecked(facets: Facet[]): Checked {
  return Object.fromEntries(
    facets.map((facet) => [
      facet.key,
      new Set(facet.options.filter((option) => option.on).map((option) => option.value)),
    ]),
  );
}

export function BookSection({ document, tab }: ViewProps<"book">) {
  const { chrome, body } = document;
  const activeTab = chrome.tabs.find((entry) => entry.id === tab) ?? chrome.tabs[0] ?? null;
  const [groupKey, setGroupKey] = useState(body.grouping.active);
  const [checked, setChecked] = useState<Checked>(() => initialChecked(body.facets));
  const [selected, setSelected] = useState<string | null>(null);
  const { openPassport } = useEvidence();
  const ledger = useLedger();
  const [refusedLens, setRefusedLens] = useState<Record<string, Refusal>>({});

  // Every compared case binds the accepted snapshot this document names. A
  // later document carrying a different snapshot for a bound case is refused
  // and named; only the explicit switch below moves the lens (IA_SPEC.md 5).
  const compareCases = body.compare.cases;
  useEffect(() => {
    const refused: Record<string, Refusal> = {};
    for (const entry of compareCases) {
      const refusal = ledger.bind(entry.case_id, entry.snapshot);
      if (refusal) refused[entry.case_id] = refusal;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the ledger is the external system this view synchronises with
    setRefusedLens(refused);
  }, [compareCases, ledger]);

  const switchLens = (caseId: string) => {
    ledger.release(caseId);
    const entry = compareCases.find((candidate) => candidate.case_id === caseId);
    if (entry) ledger.bind(entry.case_id, entry.snapshot);
    setRefusedLens((current) => {
      const next = { ...current };
      delete next[caseId];
      return next;
    });
  };

  const toggle = (facetKey: string, value: string) =>
    setChecked((current) => {
      const next = new Set(current[facetKey] ?? []);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return { ...current, [facetKey]: next };
    });

  // A filter acts only on what was served: a row without the attribute stays.
  const visible = body.rows.filter((row) =>
    body.facets.every((facet) => {
      const set = checked[facet.key];
      const value = row.attributes[facet.key];
      return !set || value === undefined || set.has(value);
    }),
  );

  const select = (passportId: string, opener: HTMLElement) => {
    setSelected(passportId);
    const passport = body.passports[passportId];
    if (passport) openPassport(passport, opener);
  };

  const compared = new Set(body.compare.cases.map((entry) => entry.case_id));
  const comparing = activeTab?.id === "compare";
  return (
    <div className="cols two-left" data-book-section>
      <div className="col left">
        <Facets
          facets={body.facets}
          checked={checked}
          onToggle={toggle}
          groupingKeys={body.grouping.keys}
          groupKey={groupKey}
          onGroup={setGroupKey}
          savedViews={body.saved_views}
        />
      </div>
      <div
        className="col"
        role="tabpanel"
        id={activeTab ? `view-${activeTab.id}` : undefined}
        aria-labelledby={activeTab ? `tab-${activeTab.id}` : undefined}
      >
        {comparing ? (
          <Compare
            compare={body.compare}
            columns={body.columns}
            passports={body.passports}
            selected={selected}
            onSelect={select}
            refusedLens={refusedLens}
            onSwitchLens={switchLens}
          />
        ) : (
          <CasesTable
            rows={visible}
            total={body.rows.length}
            columns={body.columns}
            groupKey={groupKey}
            activeKey={body.grouping.active}
            passports={body.passports}
            compared={compared}
            selected={selected}
            onSelect={select}
          />
        )}
      </div>
    </div>
  );
}
