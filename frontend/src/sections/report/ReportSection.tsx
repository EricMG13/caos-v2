// Report: the draft revision and the opinion (IA_SPEC.md 4.7). Dark surface —
// a draft is not filed output, so no paper here. Left: the deliverable this
// revision feeds; centre: the revision (draft, revisions or figures, by tab);
// right: the opinion, the freeze refusal, the revisions, the lineage.
import { OpinionColumn } from "./OpinionColumn";
import { FigureRegister, RevisionTable } from "./ReportViews";
import { RevisionEditor } from "./RevisionEditor";
import type { ViewProps } from "@/app/views";
import type { DeliverableSection, Opinion } from "@/wire/report";

/** `rev_4` → `rev_5`: the next edit is a new revision, never an amendment.
 *  Walks the trailing digit run by hand rather than `/(\d+)$/` — a regex
 *  SonarQube flags as super-linear (typescript:S8786) though this shape
 *  cannot backtrack; the loop is exactly as clear and has no such shape. */
export function nextRevisionId(id: string): string {
  let end = id.length;
  while (end > 0) {
    const code = id.charCodeAt(end - 1);
    if (code < 48 || code > 57) break; // not '0'-'9'
    end -= 1;
  }
  const digits = id.slice(end);
  return digits ? id.slice(0, end) + String(Number(digits) + 1) : id;
}

function SectionList({ sections, revision }: { sections: DeliverableSection[]; revision: string }) {
  return (
    <section className="pnl" aria-labelledby="sections-title">
      <header>
        <h2 id="sections-title">Deliverable</h2>
        <span className="cp">{sections.length} SECTIONS · ROUTE ORDER</span>
      </header>
      <ul className="pb flush" aria-label="Sections of the deliverable">
        {sections.map((section) => {
          const feeds = section.kind === "NARRATIVE";
          return (
            <li
              key={section.n}
              className={`secrow${feeds ? " on" : ""}`}
              data-section-kind={section.kind}
              aria-current={feeds ? "true" : undefined}
            >
              <span className="n tabular">§{section.n}</span>
              <span>{section.title}</span>
              <span className="src tabular">
                {section.module_id ?? (feeds ? `${revision} FEEDS` : "HOST")}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function ReportSection({ document, tab }: ViewProps<"report">) {
  const { body, chrome } = document;
  const active = tab ?? chrome.tabs[0]?.id ?? "draft";
  const next = nextRevisionId(body.revision.id);
  const opinions = [body.opinion, body.prior_opinion].filter((o): o is Opinion => o !== null);
  return (
    <div className="cols three" data-report>
      <div className="col">
        <SectionList sections={body.sections} revision={body.revision.id} />
      </div>
      <div className="col" role="tabpanel" id={`view-${active}`} aria-labelledby={`tab-${active}`}>
        {active === "revisions" ? (
          <RevisionTable
            revisions={body.revisions}
            current={body.revision.id}
            opinions={opinions}
          />
        ) : active === "figures" ? (
          <FigureRegister paragraphs={body.paragraphs} />
        ) : (
          <RevisionEditor revision={body.revision} paragraphs={body.paragraphs} next={next} />
        )}
      </div>
      <div className="col right">
        <OpinionColumn body={body} role={chrome.served_role} />
      </div>
    </div>
  );
}
