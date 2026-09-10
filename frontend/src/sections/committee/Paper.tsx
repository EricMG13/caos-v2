// The deliverable on paper: ink on cream, the only paper in the workspace
// (DESIGN.md "Paper is for filed output only"). A function of frozen bytes —
// the accepted artifacts in route order, every figure with its citation, then
// the narrative and the provenance index (SYSTEM_SPEC.md 7). Watermarked
// until filed; stamped and lined once a receipt exists.
import type { MouseEvent } from "react";
import { ProvenanceIndex } from "./ProvenanceIndex";
import { useEvidence } from "@/evidence/EvidenceContext";
import { segments, shortDigest } from "@/sections/report/text";
import type { CommitteeBody, PaperFigure, PaperSection, PaperTable } from "@/wire/committee";

/** The exact watermark a draft carries until it is filed (IA_SPEC.md 4.8). */
export const WATERMARK = "DRAFT — NOT FILED";
export type PaperScope = "all" | "narrative" | "provenance";

function Cite({ figure }: { figure: PaperFigure }) {
  const { openCitation, activeChip } = useEvidence();
  const { citation } = figure;
  return (
    <>
      <span data-figure>{figure.text}</span>
      <button
        type="button"
        className="rd-cite"
        aria-label={`Evidence ${citation.chip}`}
        aria-haspopup="dialog"
        aria-expanded={activeChip === citation.chip}
        data-chip={citation.chip}
        onClick={(event: MouseEvent<HTMLButtonElement>) =>
          openCitation(citation, event.currentTarget)
        }
      >
        <span>{citation.chip}</span>
      </button>
    </>
  );
}

function Table({ table }: { table: PaperTable }) {
  return (
    <table className="rd-table">
      <thead>
        <tr>
          {table.columns.map((column) => (
            <th key={column} scope="col">
              {column}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {table.rows.map((row, i) => (
          <tr key={i}>
            {row.map((cell, j) => (
              <td key={j}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SectionView({ section }: { section: PaperSection }) {
  return (
    <section className="rd-sec" data-module={section.module_id ?? undefined} data-n={section.n}>
      <h3 className="rd-h">
        {section.n} · {section.module_id ?? "HOST"} · {section.title}
      </h3>
      {section.paragraphs.map((paragraph, i) => (
        <p key={i} className="rd-p">
          {segments(paragraph.text, paragraph.figures).map((segment, j) =>
            segment.figure ? (
              <Cite key={j} figure={segment.figure} />
            ) : (
              <span key={j}>{segment.text}</span>
            ),
          )}
        </p>
      ))}
      {section.table ? <Table table={section.table} /> : null}
    </section>
  );
}

export function Paper({ body, scope }: { body: CommitteeBody; scope: PaperScope }) {
  const { deliverable, paper, narrative, provenance, receipt } = body;
  const narrativeN = paper.length + 1;
  const provenanceN = paper.length + 2;
  const filed = deliverable.filed;
  const watermark = deliverable.watermark ?? WATERMARK;
  return (
    <article
      className="rd-paper"
      data-paper
      data-filed={filed || undefined}
      aria-label={deliverable.title}
    >
      {filed ? (
        <div className="rd-stamp" data-stamp>
          FILED
        </div>
      ) : (
        <div className="rd-wm" data-watermark role="img" aria-label={watermark}>
          <span aria-hidden="true">{watermark}</span>
        </div>
      )}
      <div className="rd-mast" data-mast>
        <span>ORIGIN · HOST-RENDERED</span> · <span>METHOD · FROZEN SNAPSHOT</span> ·{" "}
        <span>APPROVAL · PENDING APPROVAL</span> · <span>{deliverable.snapshot}</span>
      </div>
      <h2 className="rd-title">{deliverable.title}</h2>
      <p className="rd-sub">
        {deliverable.issuer} · {deliverable.snapshot} · {deliverable.revision_id} · accepted
        artifacts in route order, every figure with its citation · no figure originated here
      </p>
      {scope === "all"
        ? paper.map((section) => <SectionView key={section.n} section={section} />)
        : null}
      {scope !== "provenance" ? (
        <section className="rd-sec" data-narrative>
          <h3 className="rd-h">
            {narrativeN} · {narrative.title}
          </h3>
          {narrative.paragraphs.map((text, i) => (
            <p key={i} className="rd-p">
              {text}
            </p>
          ))}
        </section>
      ) : null}
      {scope !== "narrative" ? (
        <section className="rd-sec" data-provenance-section>
          <h3 className="rd-h">{provenanceN} · Provenance index</h3>
          <ProvenanceIndex rows={provenance} />
        </section>
      ) : null}
      {filed && receipt ? (
        <div className="rd-filed-line" data-filed-line>
          Filed by {receipt.filed_by} · filing {receipt.filing_id} ·{" "}
          <time dateTime={receipt.filed_at}>{receipt.filed_at}</time> · sha256{" "}
          {shortDigest(receipt.deliverable_sha256)} · the audit package re-renders this page from
          the frozen payload
        </div>
      ) : null}
    </article>
  );
}
