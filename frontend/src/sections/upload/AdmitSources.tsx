// Upload's one governed write (brief 4.2, decision 12): admit a source pack.
// The control renders from the document's own `chrome.actions` -- present
// and refused, never hidden (decision 10; CLAUDE.md "Persona is not
// authority") -- and the command rechecks authority and every §44 limit at
// commit regardless of what this control shows. An action this section's
// document does not name at all is not available either: `RefusedControl`'s
// own fallback (`ACTION_UNPLACED`) is what renders it that way, by this
// control passing no `onClick` when there is no `action` to check. On
// success this section refetches its own document once; 4.4 owns the
// SSE-driven refresh other sections get. A refetch that fails never reads as
// nothing happened: the success stands (the pack was admitted) beside a
// distinct, visible refresh failure.
import { useId, useRef, useState } from "react";
import { admitSources, failureMessage, newIntent, type Intent } from "@/app/commands";
import { sectionUrl } from "@/app/transport";
import { RefusedControl } from "@/controls/RefusedControl";
import { parseUploadDocument, type ActionView, type UploadDocument } from "@/wire/v1";

/** Upload's own document, re-read once after a success (brief 4.2, decision
    12). Reuses `sectionUrl` and the v1 parser rather than the section-status
    classifier in `@/app/transport`, whose union of the four v1 documents this
    control has no reason to narrow. */
async function refetchUpload(caseId: string): Promise<UploadDocument | null> {
  const url = sectionUrl("upload", { case: caseId });
  if (!url) return null;
  let response: Response;
  try {
    response = await fetch(url, { headers: { accept: "application/json" } });
  } catch {
    return null;
  }
  if (!response.ok) return null;
  try {
    return parseUploadDocument(await response.json());
  } catch {
    return null;
  }
}

/** A stable key for the exact file set, order-sensitive, so two different
    selections of the same size never compare equal by accident. */
function fileSetKey(files: readonly File[]): string {
  return files.map((file) => `${file.name}:${file.size}:${file.lastModified}`).join("|");
}

/** What was last sent, so the same file set can retry an offline attempt on
    its one key while any other outcome -- or a changed set -- draws a fresh
    one (the coordinator's finding: a key is not a session, it is one
    intent). */
interface LastSubmitted {
  bodyKey: string;
  intent: Intent;
  offline: boolean;
}

export function AdmitSources({
  action,
  caseId,
  onAdmitted,
}: {
  action: ActionView | undefined;
  caseId: string;
  onAdmitted: (document: UploadDocument) => void;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [refreshFailed, setRefreshFailed] = useState(false);
  const lastSubmitted = useRef<LastSubmitted | null>(null);
  const refusal = action?.refusal ?? null;

  async function submit() {
    if (refusal || pending || files.length === 0) return;
    const bodyKey = fileSetKey(files);
    const previous = lastSubmitted.current;
    const intent =
      previous && previous.offline && previous.bodyKey === bodyKey ? previous.intent : newIntent();
    setPending(true);
    setError(null);
    setSuccess(null);
    setRefreshFailed(false);
    const result = await admitSources(caseId, files, intent);
    if (result.kind === "ok") {
      lastSubmitted.current = { bodyKey, intent, offline: false };
      setFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      setSuccess(`${result.receipt.source_ids.length} source(s) admitted.`);
      const refreshed = await refetchUpload(caseId);
      if (refreshed) onAdmitted(refreshed);
      else setRefreshFailed(true);
    } else {
      // Only an offline attempt keeps its intent for a retry: a refusal and an
      // invalid response both reached the server, so replaying the same key
      // would be a second request rather than the same one.
      lastSubmitted.current = { bodyKey, intent, offline: result.kind === "offline" };
      setError(failureMessage(result));
    }
    setPending(false);
  }

  return (
    <div className="admitsources" data-admit-sources>
      <label className="sr-only" htmlFor={inputId}>
        Documents to admit
      </label>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        multiple
        onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
      />
      <RefusedControl
        refusal={refusal}
        onClick={action ? () => void submit() : undefined}
        className="rb solid"
        reasonDisplay="inline"
        aria-label="Admit sources"
      >
        {pending ? "Admitting…" : `Admit${files.length ? ` ${files.length}` : ""}`}
      </RefusedControl>
      {error ? (
        <p className="note crit" role="alert" data-admit-sources-error>
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="note ok" data-admit-sources-success>
          {success}
        </p>
      ) : null}
      {refreshFailed ? (
        <p className="note warn" role="alert" data-admit-sources-refresh-failed>
          The sources were admitted, but the pack could not be refreshed. Reload to see them.
        </p>
      ) : null}
    </div>
  );
}
