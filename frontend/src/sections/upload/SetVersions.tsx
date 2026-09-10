// Set versions are immutable; the pinned one is marked and pinning it again
// is refused with its code. Pinning another is a new set and a new run.
import { useId } from "react";
import { stamp } from "./SourcePack";
import { RefusedControl } from "@/controls/RefusedControl";
import type { Refusal } from "@/wire";
import type { SetVersion } from "@/wire/upload";

export function SetVersions({
  versions,
  pinned,
  pinRefused,
}: {
  versions: SetVersion[];
  pinned: string;
  pinRefused: Refusal;
}) {
  const headingId = useId();
  return (
    <section className="pnl" aria-labelledby={headingId} data-set-versions>
      <header>
        <h2 id={headingId}>Set versions</h2>
        <span className="cp">IMMUTABLE · A NEW SET IS A NEW RUN</span>
        <span className="right">
          <span className="tag ok">{pinned} · PINNED</span>
        </span>
      </header>
      <div className="pb flush">
        {versions.map((version) => {
          const on = version.version === pinned;
          const refusal = on
            ? {
                code: "SET_ALREADY_PINNED",
                clears: `a set other than ${version.version} is chosen`,
              }
            : pinRefused;
          return (
            <div
              key={version.version}
              className={`setrow${on ? " on" : ""}`}
              data-set-version={version.version}
              data-pinned={on ? "true" : "false"}
            >
              <span className="nm">
                {version.version}
                {on ? " · pinned" : ""}
              </span>
              <RefusedControl refusal={refusal} className="rowact" reasonDisplay="hidden">
                Pin set
              </RefusedControl>
              <span className="mt">
                {version.sources} sources · pinned {stamp(version.pinned_at)}
                {on ? ` · ${refusal.code}` : ""}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
