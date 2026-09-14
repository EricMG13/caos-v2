// The source pack (IA_SPEC.md 4.2, card 5c): per source its filename, digest,
// admission time, live withdrawal and the extractor identity that predicts
// its tokens. The v1 wire carries no label, family, grade, disposition,
// pages or per-row check time -- withdrawal is checked live at every use,
// and the envelope's own `observed_at` is when this document's check ran
// (brief 4.1, "Fixture fields dropped rather than faked").
import type { SourceRow } from "@/wire/v1";

/** `2026-09-09T14:30:00Z` reads `2026-09-09 14:30Z`. */
export function stamp(iso: string): string {
  return iso.replace("T", " ").replace(/:\d\d(?:\.\d+)?Z$/, "Z");
}

/** The clock part alone: `14:30Z`. */
export function clock(iso: string): string {
  return `${iso.slice(11, 16)}Z`;
}

function WithdrawalCell({ row, observedAt }: { row: SourceRow; observedAt: string }) {
  const checked = (
    <>
      checked live at <time dateTime={observedAt}>{clock(observedAt)}</time>
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

function SourceLine({ row, observedAt }: { row: SourceRow; observedAt: string }) {
  return (
    <tr data-source={row.source_id} className={row.withdrawn_at ? "wd" : undefined}>
      <td className="wrap">{row.filename}</td>
      <td className="m">
        <code title={row.document_sha256} data-digest={row.document_sha256}>
          {row.document_sha256.slice(0, 12)}
        </code>
      </td>
      <td className="m r">
        <time dateTime={row.admitted_at}>{stamp(row.admitted_at)}</time>
      </td>
      <td className="wrap">{row.extractor_identity ?? <span className="m">—</span>}</td>
      <td>
        {row.set_versions.length ? (
          <ul className="pillrow" aria-label={`Set versions of ${row.source_id}`}>
            {row.set_versions.map((version) => (
              <li key={version} className="pill" data-version={version}>
                {version}
              </li>
            ))}
          </ul>
        ) : (
          <span className="m">—</span>
        )}
      </td>
      <WithdrawalCell row={row} observedAt={observedAt} />
    </tr>
  );
}

export function SourcePack({ rows, observedAt }: { rows: SourceRow[]; observedAt: string }) {
  return (
    <table className="reg" data-source-pack>
      <thead>
        <tr>
          <th scope="col">Filename</th>
          <th scope="col">Digest</th>
          <th scope="col" className="r">
            Admitted
          </th>
          <th scope="col">Extractor identity</th>
          <th scope="col">Set versions</th>
          <th scope="col">Withdrawal</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <SourceLine key={row.source_id} row={row} observedAt={observedAt} />
        ))}
      </tbody>
    </table>
  );
}
