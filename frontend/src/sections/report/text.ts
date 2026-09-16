// Where a figure sits in its sentence, so the chip that carries its citation
// renders beside the figure and not at the end of the paragraph; and the short
// form of a digest, whose full value always travels in the element's title.

export interface Segment<F> {
  text: string;
  figure: F | null;
  /** False when this figure's own text was not found anywhere in `text`
      (in order, after earlier matches). A caller must never render such a
      figure inline — doing so would insert a value the source text never
      stated (REPAIR_PLAN F12). It is still returned, so a caller that keeps
      a register of every figure (cited or not) can still list it. */
  placed: boolean;
}

/** Splits `text` around each figure's occurrence, in text order. Figures are
    matched in the order given, so a figure that repeats is matched to its
    next occurrence; a figure the text does not contain is appended with
    `placed: false` and no text of its own — a caller renders it, if at all,
    outside the prose (e.g. a figure register), never inline. */
export function segments<F extends { text: string }>(text: string, figures: F[]): Segment<F>[] {
  const searched = new Map<string, number>();
  const hits: { figure: F; at: number }[] = [];
  const unplaced: F[] = [];
  for (const figure of figures) {
    const at = text.indexOf(figure.text, searched.get(figure.text) ?? 0);
    if (at < 0) {
      unplaced.push(figure);
      continue;
    }
    searched.set(figure.text, at + figure.text.length);
    hits.push({ figure, at });
  }
  hits.sort((a, b) => a.at - b.at);
  const out: Segment<F>[] = [];
  let cursor = 0;
  for (const { figure, at } of hits) {
    if (at < cursor) {
      unplaced.push(figure);
      continue;
    }
    if (at > cursor) out.push({ text: text.slice(cursor, at), figure: null, placed: true });
    out.push({ text: figure.text, figure, placed: true });
    cursor = at + figure.text.length;
  }
  if (cursor < text.length) out.push({ text: text.slice(cursor), figure: null, placed: true });
  for (const figure of unplaced) out.push({ text: "", figure, placed: false });
  return out;
}

/** `0b582ff0…30df` — the full digest travels in the element's title. */
export function shortDigest(digest: string): string {
  return digest.length > 16 ? `${digest.slice(0, 8)}…${digest.slice(-4)}` : digest;
}
