// Directory's one governed write (brief 4.2, decision 12): create a case.
// The control renders from the document's own `chrome.actions` -- present
// and refused, never hidden (decision 10; CLAUDE.md "Persona is not
// authority") -- and the command rechecks authority at commit regardless of
// what this control shows. An action this section's document does not name
// at all is not available either: `RefusedControl`'s own fallback
// (`ACTION_UNPLACED`) is what renders it that way, by this control passing
// no `onClick` when there is no `action` to check. On success this section
// refetches its own document once; 4.4 owns the SSE-driven refresh other
// sections get. A refetch that fails never reads as nothing happened: the
// success stands (the case exists) beside a distinct, visible refresh
// failure.
import { useRef, useState } from "react";
import { createCase, newIntent, type Intent } from "@/app/commands";
import { sectionUrl } from "@/app/transport";
import { RefusedControl } from "@/controls/RefusedControl";
import { TextInput } from "@/ds/TextInput";
import { parseDirectoryDocument, type ActionView, type DirectoryDocument } from "@/wire/v1";

const TITLE_MAX = 256;

function offlineMessage(): string {
  return "The request did not reach the server.";
}

/** Directory's own document, re-read once after a success (brief 4.2,
    decision 12). Reuses `sectionUrl` and the v1 parser rather than the
    section-status classifier in `@/app/transport`, whose union of the four
    v1 documents this control has no reason to narrow. */
async function refetchDirectory(): Promise<DirectoryDocument | null> {
  const url = sectionUrl("directory", {});
  if (!url) return null;
  let response: Response;
  try {
    response = await fetch(url, { headers: { accept: "application/json" } });
  } catch {
    return null;
  }
  if (!response.ok) return null;
  try {
    return parseDirectoryDocument(await response.json());
  } catch {
    return null;
  }
}

/** What was last sent, so the same body can retry an offline attempt on its
    one key while any other outcome -- or a changed body -- draws a fresh
    one (the coordinator's finding: a key is not a session, it is one
    intent). */
interface LastSubmitted {
  bodyKey: string;
  intent: Intent;
  offline: boolean;
}

export function NewCase({
  action,
  onCreated,
}: {
  action: ActionView | undefined;
  onCreated: (document: DirectoryDocument) => void;
}) {
  const [title, setTitle] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [refreshFailed, setRefreshFailed] = useState(false);
  const lastSubmitted = useRef<LastSubmitted | null>(null);
  const refusal = action?.refusal ?? null;

  async function submit() {
    const trimmed = title.trim();
    if (refusal || pending || trimmed.length === 0) return;
    const bodyKey = trimmed;
    const previous = lastSubmitted.current;
    const intent =
      previous && previous.offline && previous.bodyKey === bodyKey ? previous.intent : newIntent();
    setPending(true);
    setError(null);
    setSuccess(null);
    setRefreshFailed(false);
    const result = await createCase(trimmed, intent);
    if (result.kind === "ok") {
      lastSubmitted.current = { bodyKey, intent, offline: false };
      setTitle("");
      setSuccess(`Case ${result.receipt.case_id} created.`);
      const refreshed = await refetchDirectory();
      if (refreshed) onCreated(refreshed);
      else setRefreshFailed(true);
    } else if (result.kind === "refused") {
      lastSubmitted.current = { bodyKey, intent, offline: false };
      setError(`${result.refusal.code} — clears when ${result.refusal.clears}`);
    } else if (result.kind === "error") {
      lastSubmitted.current = { bodyKey, intent, offline: false };
      setError(result.code);
    } else {
      lastSubmitted.current = { bodyKey, intent, offline: true };
      setError(offlineMessage());
    }
    setPending(false);
  }

  return (
    <div className="newcase" data-new-case>
      <label className="sr-only" htmlFor="new-case-title">
        New case title
      </label>
      <TextInput
        id="new-case-title"
        type="text"
        value={title}
        maxLength={TITLE_MAX}
        placeholder="Issuer engagement title"
        onChange={(event) => setTitle(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void submit();
          }
        }}
      />
      <RefusedControl
        refusal={refusal}
        onClick={action ? () => void submit() : undefined}
        className="rb solid"
        reasonDisplay="inline"
        aria-label="Create case"
      >
        {pending ? "Creating…" : "Create case"}
      </RefusedControl>
      {error ? (
        <p className="note crit" role="alert" data-new-case-error>
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="note ok" data-new-case-success>
          {success}
        </p>
      ) : null}
      {refreshFailed ? (
        <p className="note warn" role="alert" data-new-case-refresh-failed>
          The case was created, but the register could not be refreshed. Reload to see it.
        </p>
      ) : null}
    </div>
  );
}
