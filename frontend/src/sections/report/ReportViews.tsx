// The two other views of the same revision: the revision register (every
// saved revision, immutable, with the opinion it carries) and the figure
// register (every figure the draft asserts and what anchors it).
import { isUncited, kindLabel } from "./RevisionEditor";
import { shortDigest } from "./text";
import { CitationChip } from "@/evidence/CitationChip";
import type { Opinion, Paragraph, Revision } from "@/wire/report";

export function RevisionTable({
  revisions,
  current,
  opinions,
}: {
  revisions: Revision[];
  current: string;
  opinions: Opinion[];
}) {
  return (
    <section className="pnl" aria-labelledby="revisions-title">
      <header>
        <h2 id="revisions-title">Revisions</h2>
        <span className="cp">{revisions.length} SAVED · IMMUTABLE ONCE SAVED</span>
      </header>
      <div className="pb flush">
        <table className="prov">
          <thead>
            <tr>
              <th scope="col">Revision</th>
              <th scope="col">Saved</th>
              <th scope="col">Author</th>
              <th scope="col">Digest</th>
              <th scope="col">Opinion</th>
            </tr>
          </thead>
          <tbody>
            {revisions.map((revision) => {
              const opinion = opinions.find((o) => o.revision_id === revision.id) ?? null;
              const on = revision.id === current;
              return (
                <tr
                  key={revision.id}
                  data-revision-row={revision.id}
                  aria-current={on ? "true" : undefined}
                >
                  <td className="tabular">
                    {revision.id}
                    {on ? (
                      <>
                        {" "}
                        <span className="tag warn">DRAFT</span>
                      </>
                    ) : null}
                  </td>
                  <td>
                    <time dateTime={revision.saved_at}>{revision.saved_at}</time>
                  </td>
                  <td>{revision.author}</td>
                  <td title={revision.digest}>sha256:{shortDigest(revision.digest)}</td>
                  <td>
                    {opinion ? <span className="tag ok">SIGNED · {opinion.signed_by}</span> : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function FigureRegister({ paragraphs }: { paragraphs: Paragraph[] }) {
  const rows = paragraphs.flatMap((paragraph, index) =>
    paragraph.figures.map((figure) => ({ paragraph, index, figure })),
  );
  return (
    <section className="pnl" aria-labelledby="figures-title">
      <header>
        <h2 id="figures-title">Figures in this revision</h2>
        <span className="cp">{rows.length}</span>
      </header>
      <ul className="pb flush" aria-label="Figures">
        {rows.map(({ paragraph, index, figure }, i) => (
          <li key={i} className="ev" data-figure-row={figure.text}>
            <span className="h tabular">{figure.text}</span>
            {isUncited(paragraph, figure) ? (
              <span className="tag crit">UNCITED</span>
            ) : figure.citation ? (
              <span className="tag ok">CITED</span>
            ) : (
              <span className="tag">CARRIED</span>
            )}
            <span className="m">
              ¶{index + 1} · {kindLabel(paragraph)}
              {figure.citation ? (
                <>
                  {" "}
                  · <CitationChip citation={figure.citation} />
                </>
              ) : (
                " · no source, no artifact"
              )}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
