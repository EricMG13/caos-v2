// The source pack (IA_SPEC.md 4.2, card 5c): per source a grade, disposition,
// page count, digest and the set versions that include it. Withdrawal is
// checked live at every use and the check time is shown; once a source is
// withdrawn the control to withdraw it is refused, never hidden.
import { RefusedControl } from "@/controls/RefusedControl";
import { Tag } from "@/ds/atoms";
import type { Refusal } from "@/wire";
import type { Disposition, SourceRow } from "@/wire/upload";

const DISPOSITION_SEVERITY: Record<Disposition, string> = {
  ADMITTED: "ok",
  PENDING: "idle",
  EXCLUDED_LOW_VALUE: "warning",
  WITHDRAWN: "critical",
};

/** `2026-09-09T14:30:00Z` reads `2026-09-09 14:30Z`. */
export function stamp(iso: string): string {
  return iso.replace("T", " ").replace(/:\d\d(?:\.\d+)?Z$/, "Z");
}

/** The clock part alone: `14:30Z`. */
export function clock(iso: string): string {
  return `${iso.slice(11, 16)}Z`;
}

export function withdrawRefusal(row: SourceRow): Refusal | null {
  if (row.withdrawn_at !== null || row.disposition === "WITHDRAWN") {
    return {
      code: "SOURCE_ALREADY_WITHDRAWN",
      clears: `${row.source_id} is re-admitted as a new source with its own digest`,
    };
  }
  if (row.disposition !== "ADMITTED") {
    return { code: "SOURCE_NOT_ADMITTED", clears: `${row.source_id} is admitted into a set` };
  }
  return null;
}

function WithdrawalCell({ row }: { row: SourceRow }) {
  const checked = (
    <>
      checked live at{" "}
      <time dateTime={row.withdrawal_checked_at}>{clock(row.withdrawal_checked_at)}</time>
    </>
  );
  return (
    <td className="m wrap" data-withdrawal>
      {row.withdrawn_at ? (
        <>
          <span className="stale">
            Withdrawn <time dateTime={row.withdrawn_at}>{stamp(row.withdrawn_at)}</time>
          </span>
          <span className="sub">{checked}</span>
        </>
      ) : (
        checked
      )}
    </td>
  );
}

function SourceLine({
  row,
  pinned,
  withdrawRefused,
}: {
  row: SourceRow;
  pinned: string;
  withdrawRefused: Refusal;
}) {
  return (
    <tr data-source={row.source_id} className={row.withdrawn_at ? "wd" : undefined}>
      <td>
        <span className={`grade ${row.grade.toLowerCase()}`}>{row.grade}</span>
      </td>
      <td className="wrap">
        {row.label}
        <span className="sub">
          {row.file_name} · {row.family}
        </span>
      </td>
      <td>
        <Tag sev={DISPOSITION_SEVERITY[row.disposition]}>{row.disposition}</Tag>
      </td>
      <td className="m r">{row.pages}</td>
      <td className="m">
        <code title={row.sha256} data-digest={row.sha256}>
          {row.sha256.slice(0, 12)}
        </code>
      </td>
      <td>
        {row.set_versions.length ? (
          <ul className="pillrow" aria-label={`Set versions of ${row.source_id}`}>
            {row.set_versions.map((version) => (
              <li
                key={version}
                className={`pill${version === pinned ? " on" : ""}`}
                data-version={version}
              >
                {version}
              </li>
            ))}
          </ul>
        ) : (
          <span className="m">—</span>
        )}
      </td>
      <WithdrawalCell row={row} />
      <td className="r">
        <RefusedControl
          refusal={withdrawRefusal(row) ?? withdrawRefused}
          className="rowact"
          reasonDisplay="hidden"
        >
          Withdraw
        </RefusedControl>
      </td>
    </tr>
  );
}

export function SourcePack({
  rows,
  pinned,
  withdrawRefused,
}: {
  rows: SourceRow[];
  pinned: string;
  withdrawRefused: Refusal;
}) {
  return (
    <table className="reg" data-source-pack>
      <thead>
        <tr>
          <th scope="col">Grade</th>
          <th scope="col">Source</th>
          <th scope="col">Disposition</th>
          <th scope="col" className="r">
            Pages
          </th>
          <th scope="col">Digest</th>
          <th scope="col">Set versions</th>
          <th scope="col">Withdrawal</th>
          <th scope="col" className="r">
            <span className="sr-only">Action</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <SourceLine
            key={row.source_id}
            row={row}
            pinned={pinned}
            withdrawRefused={withdrawRefused}
          />
        ))}
      </tbody>
    </table>
  );
}
