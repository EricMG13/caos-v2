// An explicit unavailable capability (IA_SPEC.md 4.9, card 6b). It renders
// the unavailable state and names what is missing. It does not pretend: no
// settings form, no toggles, no controls that do nothing.
import { SeverityMark } from "@/chrome/SeverityMark";
import type { AdminBody } from "@/wire/admin";

function split(name: string): { head: string; rest: string | null } {
  const at = name.indexOf(" · ");
  return at < 0 ? { head: name, rest: null } : { head: name.slice(0, at), rest: name.slice(at) };
}

export function UnavailableCapability({
  body,
  observedAt,
}: {
  body: AdminBody;
  observedAt: string;
}) {
  return (
    <div className="unavail" data-unavailable-capability={body.capability}>
      <SeverityMark severity="WARNING" label="Unavailable" />
      <h3 className="h">Admin is unavailable in this deployment</h3>
      <p className="s">
        This deployment serves no administration route. The section is in the rail because hiding it
        would teach the wrong model of the system — you would not know whether administration
        exists, is forbidden to you, or was never built. It is the third: observed at{" "}
        <time dateTime={observedAt}>{observedAt}</time>, a 404 from the deployment, not a guess.
      </p>
      <div className="missing" role="list" aria-label="What is missing">
        {body.missing.map((item) => {
          const { head, rest } = split(item.name);
          return (
            <div key={`${item.name}:${item.code}`} role="listitem">
              <span>
                <b>{head}</b>
                {rest}
              </span>
              <span className="c">{item.code}</span>
            </div>
          );
        })}
      </div>
      <p className="s">
        Each is real and each is set outside this workspace. When a deployment does serve an
        administration route, this section renders it — until then this state is what a reader sees,
        never a settings page over controls that do nothing.
      </p>
    </div>
  );
}
