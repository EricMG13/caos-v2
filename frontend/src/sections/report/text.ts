// Where a figure sits in its sentence, so the chip that carries its citation
// renders beside the figure and not at the end of the paragraph; and the short
// form of a digest, whose full value always travels in the element's title.

export interface Segment<F> {
  text: string;
  figure: F | null;
}

/** Splits `text` around each figure's occurrence, in text order. Figures are
    matched in the order given, so a figure that repeats is matched to its
    next occurrence; a figure the text does not contain is appended with no
    text of its own and still renders its chip. */
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
    if (at > cursor) out.push({ text: text.slice(cursor, at), figure: null });
    out.push({ text: figure.text, figure });
    cursor = at + figure.text.length;
  }
  if (cursor < text.length) out.push({ text: text.slice(cursor), figure: null });
  for (const figure of unplaced) out.push({ text: "", figure });
  return out;
}

/** `0b582ff0…30df` — the full digest travels in the element's title. */
export function shortDigest(digest: string): string {
  return digest.length > 16 ? `${digest.slice(0, 8)}…${digest.slice(-4)}` : digest;
}
