// The Run section's governed controls (brief 4.2, decisions 1, 7, 10 and 12):
// select and pin a route, and pin the subject. Every control renders from
// `chrome.actions`, present or refused, never hidden (`RefusedControl`,
// shared with the ribbon); the command re-checks at commit, so an advisory
// `null` refusal here is never trusted as the last word. A success is shown,
// and the caller is handed one refetch to run (`onRefetch`); the control
// never claims a write took effect on its own say.
import { useCallback, useRef, useState, type ChangeEvent } from "react";
import { createRun, newIntent, pinRunInput, type CommandResult, type Intent } from "@/app/commands";
import { fetchSection } from "@/app/transport";
import { RefusalNote, RefusedControl } from "@/controls/RefusedControl";
import type {
  ActionView,
  Infer,
  RouteChoice,
  RunCreated,
  RunInputPinned,
  RunSectionDocument,
} from "@/wire/v1";
import type { V1_SHAPES } from "@/wire/v1/documents";

// Not exported as a named type from `documents.ts` (only `types.ts`, owned by
// an earlier slice, derives it for the read side); derived here the same way
// rather than duplicated by hand.
type RunSubjectView = Infer<typeof V1_SHAPES.RunSubjectView>;

export type ActionName = ActionView["action"];

/** A `RunBody` is the only enabled-section body carrying `route_choices`;
    narrows the transport's section-generic document without casting a value
    nothing has checked. */
function isRunSectionDocument(document: { body: object }): document is RunSectionDocument {
  return "route_choices" in document.body;
}

/** A POST never returns the document it changed, so the caller's view is
    kept live by one plain GET through the same transport and parser every
    load uses (brief 4.2, decision 12) — never a value this file invents. A
    refetch that itself fails to answer is shown, not silently dropped: the
    alternative is a control the analyst might press again believing the
    first press did nothing.

    Exercised end-to-end by `frontend/tests/unit/run.test.tsx`: every command
    test below drives `useRunRefetch`'s GET-after-success (and its
    `[data-refetch-failed]` note on a failed one) through the mounted
    section, never by importing the hook directly. */
export function useRunRefetch(initial: RunSectionDocument, caseId: string) {
  const [live, setLive] = useState(initial);
  const [failed, setFailed] = useState(false);
  // Adjusted during render, not in an effect (React's own pattern for
  // syncing state from a prop): a fresh `initial` — a navigation, or the
  // workspace's own SSE-triggered load — always supersedes a local refetch.
  const [seenInitial, setSeenInitial] = useState(initial);
  if (initial !== seenInitial) {
    setSeenInitial(initial);
    setLive(initial);
  }
  const refetch = useCallback(
    (runId: string | null) => {
      void fetchSection("run", { case: caseId, run: runId }).then((status) => {
        if ("document" in status && isRunSectionDocument(status.document)) {
          setLive(status.document);
          setFailed(false);
        } else {
          setFailed(true);
        }
      });
    },
    [caseId],
  );
  return { live, failed, refetch };
}

/** The one entry for a served action, if the document carries it. An action
    absent from the list is not the same as one served with a null refusal:
    callers below never fire a click for an absent entry, so `RefusedControl`
    falls to its own default (`ACTION_UNPLACED`) rather than being told
    "available" by a coerced `null`.

    `actionOf`'s selection from `chrome.actions` is what
    `test_an_action_absent_from_served_actions_is_action_unplaced_not_available`
    and `test_a_refused_action_renders_its_code_and_clearance_and_is_not_hidden`
    exercise, through the mounted section rather than by calling it directly. */
export function actionOf(
  actions: readonly ActionView[],
  action: ActionName,
): ActionView | undefined {
  return actions.find((entry) => entry.action === action);
}

export interface CommandState<R> {
  pending: boolean;
  result: CommandResult<R> | null;
}

/** One `crypto.randomUUID()` key per user intent (brief 4.2, decision 12).
    `run` takes the request body alongside the sender: the key is reused only
    when the immediately preceding call carried the identical body and
    answered `{ kind: "offline" }` (a network retry of the same intent, never
    reaching the server); any other answer, or a body that has changed since
    (the analyst edited the subject, picked a different route, re-read a
    preview), draws a fresh one.

    `useCommand`'s intent lifecycle is what
    `test_the_idempotency_key_is_reused_for_a_retry_of_the_same_body` and
    `test_the_idempotency_key_is_replaced_when_the_body_changes_even_after_an_offline_answer`
    exercise, by driving the mounted section's own controls. */
export function useCommand<R>() {
  const intentRef = useRef<Intent>(newIntent());
  const lastBodyRef = useRef<string | null>(null);
  const lastKindRef = useRef<CommandResult<R>["kind"] | null>(null);
  const [state, setState] = useState<CommandState<R>>({ pending: false, result: null });
  const run = useCallback(
    async (body: unknown, send: (intent: Intent) => Promise<CommandResult<R>>) => {
      const bodyKey = JSON.stringify(body);
      const retrySameBody = lastKindRef.current === "offline" && lastBodyRef.current === bodyKey;
      if (!retrySameBody) intentRef.current = newIntent();
      lastBodyRef.current = bodyKey;
      setState({ pending: true, result: null });
      const result = await send(intentRef.current);
      lastKindRef.current = result.kind;
      setState({ pending: false, result });
      return result;
    },
    [],
  );
  return { pending: state.pending, result: state.result, run };
}

/** What the last attempt of a command answered, beside the advisory refusal
    already shown on the control itself: a visible success, a typed refusal,
    an unreadable answer, or a request that never reached the server. */
export function CommandOutcome({
  result,
  success,
}: {
  result: CommandResult<unknown> | null;
  success: string;
}) {
  if (result === null) return null;
  if (result.kind === "ok") {
    return (
      <div className="note" data-command-success>
        {success}
      </div>
    );
  }
  if (result.kind === "refused") return <RefusalNote refusal={result.refusal} />;
  if (result.kind === "offline") {
    return (
      <div className="note" data-command-offline>
        The request never reached the server. Retrying sends the same key.
      </div>
    );
  }
  return (
    <div className="note" data-command-error>
      RESPONSE_INVALID — the server&apos;s answer did not match the wire.
    </div>
  );
}

/** A run with no route is useless (brief 4.2, decision 1): select and pin one
    in the same command that creates the run. Available with no displayed
    run, and again afterwards to start a fresh one. A success refetches the
    section by the new run id, so the view moves off this form at once and a
    second press is a plainly new run, never a silent duplicate. */
export function CreateRunControl({
  caseId,
  action,
  choices,
  onRefetch,
}: {
  caseId: string;
  action: ActionView | undefined;
  choices: readonly RouteChoice[];
  onRefetch: (runId: string | null) => void;
}) {
  const [pick, setPick] = useState(0);
  const { pending, result, run } = useCommand<RunCreated>();
  const chosen = choices[pick] ?? null;
  return (
    <section className="pnl" data-create-run>
      <header>
        <h2>Create run</h2>
      </header>
      <div className="pb">
        {choices.length ? (
          <>
            <label className="fld">
              Route
              <select
                data-route-select
                value={pick}
                onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                  setPick(Number(event.target.value))
                }
              >
                {choices.map((choice, index) => (
                  <option key={`${choice.profile_id}:${choice.selection_id}`} value={index}>
                    {choice.profile_id} · {choice.selection_id}
                  </option>
                ))}
              </select>
            </label>
            <RefusedControl
              refusal={action ? action.refusal : null}
              className="rb acc"
              data-action="CREATE_RUN"
              onClick={
                action && chosen
                  ? () => {
                      void run(chosen, (intent) => createRun(caseId, chosen, intent)).then(
                        (outcome) => {
                          if (outcome.kind === "ok") onRefetch(outcome.receipt.run_id);
                        },
                      );
                    }
                  : undefined
              }
            >
              {pending ? "Creating…" : "Create run"}
            </RefusedControl>
          </>
        ) : (
          <div className="note" data-no-route-choices>
            No route choices are offered for this case.
          </div>
        )}
        <CommandOutcome result={result} success="Run created. Reading the new run back." />
      </div>
    </section>
  );
}

const EMPTY_SUBJECT: RunSubjectView = {
  issuer_id: "",
  issuer_name: "",
  reporting_period: "",
  analysis_date: "",
};

/** Pins the subject the run executes against. The subject reuses
    `RunSubjectView`; the receipt's `input_fingerprint` is what a gate
    approval and start/retry must carry (slice 4.2j part 2), and the document
    never re-serves it, so the caller is handed it here to hold for the
    session. */
export function PinInputControl({
  caseId,
  runId,
  action,
  initial,
  onPinned,
  onRefetch,
}: {
  caseId: string;
  runId: string;
  action: ActionView | undefined;
  initial: RunSubjectView | null;
  onPinned: (fingerprint: string) => void;
  onRefetch: (runId: string | null) => void;
}) {
  const [subject, setSubject] = useState<RunSubjectView>(initial ?? EMPTY_SUBJECT);
  const { pending, result, run } = useCommand<RunInputPinned>();
  const field = (key: keyof RunSubjectView) => ({
    value: subject[key],
    onChange: (event: ChangeEvent<HTMLInputElement>) =>
      setSubject((current: RunSubjectView) => ({ ...current, [key]: event.target.value })),
  });
  return (
    <section className="pnl" data-pin-input>
      <header>
        <h2>Subject</h2>
      </header>
      <div className="pb">
        <label className="fld">
          Issuer id
          <input data-field="issuer_id" {...field("issuer_id")} />
        </label>
        <label className="fld">
          Issuer name
          <input data-field="issuer_name" {...field("issuer_name")} />
        </label>
        <label className="fld">
          Reporting period
          <input data-field="reporting_period" {...field("reporting_period")} />
        </label>
        <label className="fld">
          Analysis date
          <input data-field="analysis_date" placeholder="YYYY-MM-DD" {...field("analysis_date")} />
        </label>
        <RefusedControl
          refusal={action ? action.refusal : null}
          className="rb acc"
          data-action="PIN_RUN_INPUT"
          onClick={
            action
              ? () => {
                  void run(subject, (intent) => pinRunInput(caseId, runId, subject, intent)).then(
                    (outcome) => {
                      if (outcome.kind === "ok") {
                        onPinned(outcome.receipt.input_fingerprint);
                        onRefetch(runId);
                      }
                    },
                  );
                }
              : undefined
          }
        >
          {pending ? "Pinning…" : "Pin input"}
        </RefusedControl>
        <CommandOutcome result={result} success="Subject pinned. Reading it back." />
      </div>
    </section>
  );
}
