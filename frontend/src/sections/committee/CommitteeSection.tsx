// Committee: the deliverable the host renders from the frozen snapshot
// (IA_SPEC.md 4.8). Left: the accepted artifacts in route order, then the
// narrative and the provenance index. Centre: the document on paper. Right:
// the filing. Nothing on this section edits the deliverable.
import { FilingLadder } from "./FilingLadder";
import { Paper, type PaperScope } from "./Paper";
import type { ViewProps } from "@/app/views";
import type { ArtifactRow, CommitteeBody } from "@/wire/committee";

const DISPOSITION_TONE: Record<ArtifactRow["disposition"], string> = {
  ACCEPTED: "ok",
  RESTRICTED: "warn",
  SCREENING_ONLY: "",
};

function ArtifactList({ body }: { body: CommitteeBody }) {
  const { artifacts, paper, narrative, provenance, deliverable } = body;
  const sectionOf = new Map(paper.map((section) => [section.module_id, section.n]));
  const narrativeN = paper.length + 1;
  const provenanceN = paper.length + 2;
  return (
    <section className="pnl" aria-labelledby="artifacts-title">
      <header>
        <h2 id="artifacts-title">Accepted artifacts</h2>
        <span className="cp">ROUTE ORDER · {deliverable.snapshot}</span>
      </header>
      <ul className="pb flush" aria-label="Deliverable in route order">
        {artifacts.map((artifact, index) => {
          const n = sectionOf.get(artifact.module_id);
          return (
            <li
              key={artifact.module_id}
              className="secrow"
              data-artifact={artifact.module_id}
              data-route-position={index + 1}
            >
              <span className="n tabular">{n ? `§${n}` : "—"}</span>
              <span>
                <span className="tabular">{artifact.module_id}</span> · {artifact.name}
              </span>
              <span className="src">
                <span className={`tag ${DISPOSITION_TONE[artifact.disposition]}`}>
                  {artifact.disposition}
                </span>
              </span>
            </li>
          );
        })}
        <li className="secrow" data-entry="narrative">
          <span className="n tabular">§{narrativeN}</span>
          <span>{narrative.title}</span>
          <span className="src">{deliverable.revision_id}</span>
        </li>
        <li className="secrow" data-entry="provenance">
          <span className="n tabular">§{provenanceN}</span>
          <span>Provenance index</span>
          <span className="src">{provenance.length} MODULES</span>
        </li>
      </ul>
    </section>
  );
}

const SCOPES: Record<string, PaperScope> = { narrative: "narrative", provenance: "provenance" };

export function CommitteeSection({ document, tab }: ViewProps<"committee">) {
  const { body, chrome } = document;
  const active = tab ?? chrome.tabs[0]?.id ?? "deliverable";
  const scope = SCOPES[active] ?? "all";
  return (
    <div className="cols three" data-committee>
      <div className="col">
        <ArtifactList body={body} />
      </div>
      <div className="col" role="tabpanel" id={`view-${active}`} aria-labelledby={`tab-${active}`}>
        <div className="papergutter">
          <Paper body={body} scope={scope} />
        </div>
      </div>
      <div className="col right">
        <FilingLadder body={body} role={chrome.served_role} />
      </div>
    </div>
  );
}
