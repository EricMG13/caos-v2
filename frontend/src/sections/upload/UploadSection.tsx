// Upload (IA_SPEC.md 4.2, card 5c): the admitted sources and their set
// versions, v1 wire. Withdrawal is checked live at every use, not at pin
// time; pinning and withdrawing are governed commands the v1 document does
// not carry (brief 4.1, decision 5). Admit sources is the one governed write
// this section owns (brief 4.2, slice 4.2i).
import { useState } from "react";
import { AdmitSources } from "./AdmitSources";
import { SetVersions } from "./SetVersions";
import { SourcePack } from "./SourcePack";
import type { UploadDocument } from "@/wire/v1";

export function UploadSection({ document }: { document: UploadDocument; tab: string | null }) {
  // 4.2 owns only this control's own refetch (decision 12); the SSE-driven
  // refresh every other section gets is 4.4's. A new document from the
  // parent (navigation, a future poll) always wins over a stale local one --
  // adjusted during render (React's documented pattern for this), never in
  // an effect, so there is no cascading extra render.
  const [live, setLive] = useState(document);
  const [seen, setSeen] = useState(document);
  if (document !== seen) {
    setSeen(document);
    setLive(document);
  }
  const { body } = live;
  const rows = body.sources;
  const withdrawn = rows.filter((row) => row.withdrawn_at !== null).length;
  const admitAction = live.chrome.actions.find((a) => a.action === "ADMIT_SOURCES");
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
            <AdmitSources action={admitAction} caseId={body.case_id} onAdmitted={setLive} />
            {rows.length ? (
              <SourcePack rows={rows} observedAt={live.observed_at} />
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
