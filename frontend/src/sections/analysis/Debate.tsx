// CP-6A, the Bull / Bear / Chair debate: a module output like any other,
// rendered in the centre column with the Chair's weighting matrix as its
// table (docs/design/BRIEF.md).
import { CitationChip } from "@/evidence/CitationChip";
import type { Debate as DebateBody, DebateTurn } from "@/wire/analysis";

const ROLE_TONE: Record<DebateTurn["role"], string> = { BULL: "ok", BEAR: "crit", CHAIR: "acc" };

export function Debate({ debate }: { debate: DebateBody }) {
  return (
    <>
      <section className="pnl" data-debate>
        <header>
          <h2>Bull / Bear / Chair debate</h2>
          <span className="cp">CP-6A</span>
          <span className="right">
            <span className="tag">{debate.turns.length} TURNS</span>
          </span>
        </header>
        <ol className="pb flush plain">
          {debate.turns.map((turn, index) => (
            <li key={index} className="turn" data-turn={turn.role}>
              <span className={`tag ${ROLE_TONE[turn.role]}`}>{turn.role}</span>
              <span>{turn.text}</span>
              {turn.citation ? (
                <span className="chips">
                  <CitationChip citation={turn.citation} />
                </span>
              ) : null}
            </li>
          ))}
        </ol>
      </section>
      <section className="pnl" data-weighting>
        <header>
          <h2>Chair&apos;s weighting matrix</h2>
          <span className="cp">CP-6A</span>
        </header>
        <div className="pb flush">
          <table className="fin">
            <thead>
              <tr>
                <th scope="col">Factor</th>
                <th scope="col">Bull</th>
                <th scope="col">Bear</th>
                <th scope="col">Chair</th>
              </tr>
            </thead>
            <tbody>
              {debate.weighting.map((row) => (
                <tr key={row.factor}>
                  <td>{row.factor}</td>
                  <td>{row.bull}</td>
                  <td>{row.bear}</td>
                  <td>{row.chair}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="pb note" data-memo>
          <b>Chair memo.</b> {debate.memo}
        </div>
      </section>
    </>
  );
}
