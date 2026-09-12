// Upload (IA_SPEC.md 4.2, card 5c): the source pack and the pinned set.
// Withdrawal is checked live at every use; a restatement is a conflict, never
// a merge. The right column is about the set and the conflict, not a menu.
import { useId } from "react";
import { Restatements } from "./Restatements";
import { SetVersions } from "./SetVersions";
import { SourcePack } from "./SourcePack";
import type { ViewProps } from "@/app/views";
import { READ_ONLY_API, RefusalNote } from "@/controls/RefusedControl";
import type { Refusal } from "@/wire";

/** The store writes; the browser never withdraws, pins or mints a timestamp. */
const STORE_UNPLACED: Refusal = {
  code: "STORE_UNPLACED",
  clears: `the API serves the store's withdrawal and pinning as routes — ${READ_ONLY_API}`,
};

const WITHDRAWN_AT_USE = {
  code: "SOURCE_WITHDRAWN",
  clears:
    "the source is re-admitted as a new source with its own digest — a read of a withdrawn source refuses at the boundary and returns no text",
};

export function UploadSection({ document, tab }: ViewProps<"upload">) {
  const body = document.body;
  const headingId = useId();
  const pinned = body.pinned_set;
  const rows = body.sources;
  const active = tab ?? document.chrome.tabs[0]?.id ?? "pack";
  const withdrawals = active === "withdrawals";
  const shown = withdrawals ? rows.filter((row) => row.withdrawn_at !== null) : rows;
  const inSet = rows.filter((row) => row.set_versions.includes(pinned)).length;
  return (
    <div className="cols two">
      <div className="col">
        <section className="pnl" aria-labelledby={headingId}>
          <header>
            <h2 id={headingId}>{withdrawals ? "Withdrawn sources" : "Source pack"}</h2>
            <span className="cp">ONE USER-PROVIDED DOCUMENT PER ROW</span>
            <span className="right">
              <span className="tag">{rows.length} SOURCES</span>
              <span className="tag ok">
                {inSet} IN {pinned}
              </span>
            </span>
          </header>
          <div className="pb flush">
            {shown.length ? (
              <SourcePack rows={shown} pinned={pinned} withdrawRefused={STORE_UNPLACED} />
            ) : (
              <p className="pb note">
                {withdrawals ? "No source is withdrawn." : "The pack holds no source."}
              </p>
            )}
          </div>
        </section>
        {withdrawals ? <RefusalNote refusal={WITHDRAWN_AT_USE} /> : null}
        <p className="note">
          <b>Withdrawal is checked live at every use, not at pin time.</b> A withdrawn source is
          still a member of the sets that admitted it, because sets are immutable — but a run
          reading it now is refused with a typed code, and every conclusion that cited it is marked.
          Removing it from the analysis means pinning a new set, which is a new set and a new run,
          never an edit to {pinned}.
        </p>
      </div>
      <div className="col right">
        <SetVersions versions={body.set_versions} pinned={pinned} pinRefused={STORE_UNPLACED} />
        <Restatements restatements={body.restatements} />
      </div>
    </div>
  );
}
