// The filing chain's four governed writes (Task 12.1's routes, placed here by
// Task 12.2): save a revision from the run's accepted artifacts and this
// draft, sign the exact bytes on screen, freeze them, file them.
//
// Sign and freeze sit on Report rather than Committee because `read_committee`
// refuses a revision that is not frozen, so the Committee section can never
// offer the two acts that would make it one. Save is there for the same
// reason. Filing acts on an already-frozen revision, which is exactly what
// Committee serves; it sits here to keep the chain on one surface, not
// because Committee could not offer it.
//
// Every control renders from the document's own `chrome.actions` -- present
// and refused, never hidden -- and grants nothing: the three-actor rule, the
// digest each act binds and the head a draft was composed against are all
// checked at commit, under the case lock. A signer whose browser still offers
// "Freeze" is refused there, and that refusal is what this surface shows.
import { useState } from "react";
import { useSearchParams } from "react-router";
import {
  fileDeliverable,
  freezeDeliverable,
  saveRevision,
  signOpinion,
  type CommandResult,
  type Intent,
} from "@/app/commands";
import { sectionUrl } from "@/app/transport";
import { RefusedControl } from "@/controls/RefusedControl";
import { CommandOutcome, useCommand } from "@/sections/run/controls";
import {
  parseReportDocument,
  type ActionView,
  type NarrativeDraft,
  type ReportDocument,
} from "@/wire/v1";

/** One paragraph per non-empty line, one prose span per paragraph. A figure
    span names a citation of a verified record, which needs a picker this
    surface does not have yet, so a draft written here carries prose only --
    and a revision saved from it says so by carrying no figure, rather than by
    this file guessing at one. */
function paragraphs(draft: string): NarrativeDraft[][] {
  return draft
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => [{ text: line, figure: null }]);
}

/** The Report document as it is now, re-read once after an act that changed
    it. Same `sectionUrl` and v1 parser every load uses; a value this file
    invents is never put on screen in its place. */
async function refetchReport(
  caseId: string,
  runId: string,
  revisionId: string,
): Promise<ReportDocument | null> {
  const url = sectionUrl("report", { case: caseId, run: runId, revision: revisionId });
  if (!url) return null;
  let response: Response;
  try {
    response = await fetch(url, { headers: { accept: "application/json" } });
  } catch {
    return null;
  }
  if (!response.ok) return null;
  try {
    return parseReportDocument(await response.json());
  } catch {
    return null;
  }
}

function FilingAct({
  name,
  action,
  label,
  request,
  send,
  onDone,
}: {
  /** The command this control is for, named whether or not the document
      judges it: a control drawn for an action `chrome.actions` omits is
      `ACTION_UNPLACED`, which a reader can only see if it is on screen. */
  name: string;
  action: ActionView | undefined;
  label: string;
  /** What this press asks for, which is what the idempotency key is derived
      from. The label would key two presses of the same button alike even when
      the revision or the digest beneath them had moved; `_replay` refuses the
      mismatch, so keying on the label fails closed rather than wrongly -- but
      it fails where this asks the right question instead. */
  request: unknown;
  send: (intent: Intent) => Promise<CommandResult<{ payload_sha256: string }>>;
  onDone: () => void;
}) {
  const { pending, result, run } = useCommand<{ payload_sha256: string }>();
  const refusal = action?.refusal ?? null;
  const verb = label.split(" ")[0]!;
  return (
    <div className="fld">
      <RefusedControl
        refusal={refusal}
        onClick={
          action
            ? () => {
                if (refusal || pending) return;
                void run(request, send).then((outcome) => {
                  if (outcome.kind === "ok") onDone();
                });
              }
            : undefined
        }
        className="rb"
        reasonDisplay="inline"
        data-action={name}
        aria-label={label}
      >
        {pending ? `${verb}…` : label}
      </RefusedControl>
      <CommandOutcome result={result} success={`${label}: done. Re-reading the report.`} />
    </div>
  );
}

export function FilingControls({
  document,
  onRefreshed,
}: {
  document: ReportDocument;
  onRefreshed: (next: ReportDocument) => void;
}) {
  const { body } = document;
  const [draft, setDraft] = useState("");
  const [, setParams] = useSearchParams();
  const [refreshFailed, setRefreshFailed] = useState(false);
  const save = useCommand<{ revision_id: string }>();
  const actionOf = (name: string) => document.chrome.actions.find((a) => a.action === name);
  const digest = body.payload_sha256;

  async function reread() {
    setRefreshFailed(false);
    const next = await refetchReport(body.case_id, body.displayed_run_id, body.revision_id);
    if (next) onRefreshed(next);
    else setRefreshFailed(true);
  }

  const saveAction = actionOf("SAVE_REVISION");
  const narrative = paragraphs(draft);
  const request = { expected_revision_id: body.revision_id, narrative };

  return (
    <section className="pnl" data-filing-controls>
      <header>
        <h2>Filing</h2>
        <span className="cp">SAVE · SIGN · FREEZE · FILE</span>
      </header>
      <div className="pb">
        <label className="fld" htmlFor="narrative-draft">
          Narrative draft
        </label>
        <textarea
          id="narrative-draft"
          value={draft}
          rows={4}
          placeholder="One paragraph per line. A figure needs a citation picker this surface does not have."
          onChange={(event) => setDraft(event.target.value)}
        />
        <div className="fld">
          <RefusedControl
            refusal={saveAction?.refusal ?? null}
            onClick={
              saveAction
                ? () => {
                    if (saveAction.refusal || save.pending) return;
                    void save
                      .run(request, (intent) =>
                        saveRevision(body.case_id, body.displayed_run_id, request, intent),
                      )
                      .then((outcome) => {
                        if (outcome.kind !== "ok") return;
                        setDraft("");
                        // The address is corrected, not navigated: the reader
                        // did not move, the run gained a newer revision, and a
                        // reload shows the one they are looking at.
                        setParams(
                          (current) => {
                            const next = new URLSearchParams(current);
                            next.set("revision", outcome.receipt.revision_id);
                            return next;
                          },
                          { replace: true },
                        );
                      });
                  }
                : undefined
            }
            className="rb solid"
            reasonDisplay="inline"
            data-action="SAVE_REVISION"
            aria-label="Save revision"
          >
            {save.pending ? "Saving…" : "Save revision"}
          </RefusedControl>
          {save.result?.kind === "ok" ? (
            <p className="note ok" data-revision-saved>
              Revision {save.result.receipt.revision_id} saved.
            </p>
          ) : (
            <CommandOutcome result={save.result} success="" />
          )}
        </div>
        <FilingAct
          name="SIGN_OPINION"
          request={{
            action: "SIGN_OPINION",
            revision_id: body.revision_id,
            payload_sha256: digest,
          }}
          action={actionOf("SIGN_OPINION")}
          label="Sign opinion"
          send={(intent) => signOpinion(body.case_id, body.revision_id, digest, intent)}
          onDone={() => void reread()}
        />
        <FilingAct
          name="FREEZE_DELIVERABLE"
          request={{
            action: "FREEZE_DELIVERABLE",
            revision_id: body.revision_id,
            payload_sha256: digest,
          }}
          action={actionOf("FREEZE_DELIVERABLE")}
          label="Freeze deliverable"
          send={(intent) => freezeDeliverable(body.case_id, body.revision_id, digest, intent)}
          onDone={() => void reread()}
        />
        <FilingAct
          name="FILE_DELIVERABLE"
          request={{
            action: "FILE_DELIVERABLE",
            revision_id: body.revision_id,
            payload_sha256: digest,
          }}
          action={actionOf("FILE_DELIVERABLE")}
          label="File deliverable"
          send={(intent) => fileDeliverable(body.case_id, body.revision_id, digest, intent)}
          onDone={() => void reread()}
        />
        {refreshFailed ? (
          <p className="note warn" role="alert" data-filing-refresh-failed>
            The act landed, but the report could not be re-read. Reload to see it.
          </p>
        ) : null}
      </div>
    </section>
  );
}
