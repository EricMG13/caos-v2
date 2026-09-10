// The module provenance index that closes the deliverable: every module whose
// accepted artifact reached the page, with the build it ran under, the
// artifact's digest and when it was accepted (SYSTEM_SPEC.md 7).
import { shortDigest } from "@/sections/report/text";
import type { ProvenanceRow } from "@/wire/committee";

export function ProvenanceIndex({ rows }: { rows: ProvenanceRow[] }) {
  return (
    <table className="prov" data-provenance>
      <caption className="sr-only">
        Provenance index: every module whose accepted artifact reached this deliverable
      </caption>
      <thead>
        <tr>
          <th scope="col">Module</th>
          <th scope="col">Build</th>
          <th scope="col">Artifact</th>
          <th scope="col">Accepted</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.module_id} data-provenance-row={row.module_id}>
            <td>{row.module_id}</td>
            <td>{row.build_id}</td>
            <td title={row.artifact_sha256}>sha256:{shortDigest(row.artifact_sha256)}</td>
            <td>
              <time dateTime={row.accepted_at}>{row.accepted_at}</time>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
