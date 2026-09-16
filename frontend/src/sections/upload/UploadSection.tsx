// Upload (IA_SPEC.md 4.2, card 5c): the admitted sources and their set
// versions, v1 wire. Withdrawal is checked live at every use, not at pin
// time; pinning and withdrawing are governed commands the v1 document does
// not carry (brief 4.1, decision 5 -- commands arrive in 4.2).
import { SetVersions } from "./SetVersions";
import { SourcePack } from "./SourcePack";
import type { UploadDocument } from "@/wire/v1";

export function UploadSection({ document }: { document: UploadDocument; tab: string | null }) {
  const { body } = document;
  const rows = body.sources;
  const withdrawn = rows.filter((row) => row.withdrawn_at !== null).length;
  return (
    <div className="cols two">
      <div className="col">
        <section className="pnl" aria-labelledby="source-pack-heading">
          <header>
            <h2 id="source-pack-heading">Source pack</h2>
            <span className="cp">ONE USER-PROVIDED DOCUMENT PER ROW</span>
            <span className="right">
              <span className="tag">{rows.length} SOURCES</span>
              {withdrawn > 0 ? <span className="tag warn">{withdrawn} WITHDRAWN</span> : null}
            </span>
          </header>
          <div className="pb flush">
            {rows.length ? (
              <SourcePack rows={rows} observedAt={document.observed_at} />
            ) : (
              <p className="pb note">The pack holds no source.</p>
            )}
          </div>
        </section>
        <p className="note">
          <b>Withdrawal is checked live at every use, not at pin time.</b> A withdrawn source is
          still a member of the sets that admitted it, because sets are immutable — but a run
          reading it now is refused with a typed code, and every conclusion that cited it is marked.
        </p>
      </div>
      <div className="col right">
        <SetVersions versions={body.set_versions} />
      </div>
    </div>
  );
}
