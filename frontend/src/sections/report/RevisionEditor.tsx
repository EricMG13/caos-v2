// The draft revision as a read view on the workspace's own surface — dark, not
// paper (DESIGN.md "Paper is for filed output only"). A revision is immutable
// once saved: the next edit is the next revision, never an amendment
// (IA_SPEC.md 4.7).
import { segments, shortDigest } from "./text";
import { CitationChip } from "@/evidence/CitationChip";
import type { Figure, Paragraph, Revision } from "@/wire/report";

export function kindLabel(paragraph: Paragraph): string {
  return paragraph.kind === "MODULE"
    ? `MODULE · ${paragraph.module_id ?? "—"}`
    : "ANALYST_JUDGMENT";
}

/** A figure a judgment paragraph asserts with no citation: what freeze
    refuses, by name (IA_SPEC.md 4.7). */
export function isUncited(paragraph: Paragraph, figure: Figure): boolean {
  return paragraph.kind === "ANALYST_JUDGMENT" && figure.citation === null;
}

export function figureCounts(paragraphs: Paragraph[]): { total: number; uncited: number } {
  let total = 0;
  let uncited = 0;
  for (const paragraph of paragraphs) {
    for (const figure of paragraph.figures) {
      total += 1;
      if (isUncited(paragraph, figure)) uncited += 1;
    }
  }
  return { total, uncited };
}

function FigureMark({ paragraph, figure }: { paragraph: Paragraph; figure: Figure }) {
  if (figure.citation) {
    return (
      <>
        {figure.text} <CitationChip citation={figure.citation} />
      </>
    );
  }
  if (isUncited(paragraph, figure)) {
    return (
      <span className="figure" data-uncited-figure={figure.text} title="Asserted with no citation">
        {figure.text}
      </span>
    );
  }
  return <>{figure.text}</>;
}

export function RevisionEditor({
  revision,
  paragraphs,
  next,
}: {
  revision: Revision;
  paragraphs: Paragraph[];
  /** The id the next edit saves as. */
  next: string;
}) {
  const counts = figureCounts(paragraphs);
  return (
    <section className="pnl" aria-labelledby="draft-title">
      <header>
        <h2 id="draft-title">Draft revision</h2>
        <span className="cp">{revision.id} · ANALYST NARRATIVE</span>
        <span className="right">
          {counts.uncited > 0 ? (
            <span className="tag warn">
              {counts.uncited} UNCITED FIGURE{counts.uncited === 1 ? "" : "S"}
            </span>
          ) : (
            <span className="tag ok">EVERY FIGURE CITED</span>
          )}
          <span className="tag">{counts.total - counts.uncited} ANCHORED</span>
        </span>
      </header>
      <div className="pb">
        <article
          className="ed"
          data-revision={revision.id}
          contentEditable={false}
          aria-labelledby="draft-title"
        >
          {paragraphs.map((paragraph, index) => (
            <p key={paragraph.id} data-paragraph={paragraph.id} data-kind={paragraph.kind}>
              <span className={`tag${paragraph.kind === "ANALYST_JUDGMENT" ? " acc" : ""}`}>
                ¶{index + 1} · {kindLabel(paragraph)}
              </span>{" "}
              {segments(paragraph.text, paragraph.figures).map((segment, i) =>
                segment.figure ? (
                  <FigureMark key={i} paragraph={paragraph} figure={segment.figure} />
                ) : (
                  <span key={i}>{segment.text}</span>
                ),
              )}
            </p>
          ))}
        </article>
        <p className="note mt-2" data-next-revision={next}>
          <b>A revision is immutable once saved.</b> This is the read view of <b>{revision.id}</b>,
          saved{" "}
          <time className="tabular" dateTime={revision.saved_at}>
            {revision.saved_at}
          </time>{" "}
          by {revision.author} · digest{" "}
          <code className="tabular" title={revision.digest}>
            sha256:{shortDigest(revision.digest)}
          </code>
          . The next edit saves <b>{next}</b> — never an amendment to {revision.id}.
        </p>
      </div>
    </section>
  );
}
