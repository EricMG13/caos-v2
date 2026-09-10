// One metric cell of the book or the comparison: a button that opens the
// passport with its opener passed. Deviation is a triangle and a stated size;
// stale is a class on the cell and a date in its title.
import type { BookCell } from "@/wire/book";
import type { Passport } from "@/wire";

export function MetricCell({
  cell,
  passport,
  name,
  selected,
  onSelect,
}: {
  cell: BookCell;
  passport: Passport | null;
  /** An accessible name for a cell outside a table; must include the value. */
  name?: string;
  selected: boolean;
  onSelect: (passportId: string, opener: HTMLElement) => void;
}) {
  const notes = [
    cell.deviation ? `Deviates from the house definition by ${cell.deviation}` : null,
    cell.stale ? `Stale evidence · ${passport?.evidence_date ?? "date not served"}` : null,
    passport ? null : "No passport is served for this cell",
  ].filter((note): note is string => note !== null);
  const label = name
    ? `${name}${cell.deviation ? ` · deviates by ${cell.deviation}` : ""}`
    : undefined;
  return (
    <button
      type="button"
      className="cellbtn"
      data-passport-id={cell.passport_id}
      data-deviation={cell.deviation ?? undefined}
      data-stale={cell.stale || undefined}
      aria-pressed={selected}
      aria-label={label}
      title={notes.length ? notes.join(" · ") : undefined}
      onClick={(event) => onSelect(cell.passport_id, event.currentTarget)}
    >
      {cell.value}
      {cell.deviation ? (
        <span className="defmark" role="img" aria-label={`deviates by ${cell.deviation}`} />
      ) : null}
    </button>
  );
}
