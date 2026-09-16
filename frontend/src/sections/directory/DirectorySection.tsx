// Directory (IA_SPEC.md 4.1): the case register, v1 wire. Search, filter and
// intake are commands or fields the v1 Directory document does not carry
// (brief 4.1, decision 1 and 9 -- commands arrive in 4.2); this section draws
// exactly the cases the actor holds live standing on and nothing else.
import { CaseRegister } from "./CaseRegister";
import type { DirectoryDocument } from "@/wire/v1";

export function DirectorySection({
  document,
}: {
  document: DirectoryDocument;
  tab: string | null;
}) {
  const { cases } = document.body;
  return (
    <div className="col">
      <section className="pnl" aria-labelledby="directory-register-heading">
        <header>
          <h2 id="directory-register-heading">Case register</h2>
          <span className="cp">ONE ISSUER ENGAGEMENT PER ROW</span>
          <span className="right">
            <span className="tag">{cases.length} CASES</span>
          </span>
        </header>
        <div className="pb flush">
          <CaseRegister rows={cases} />
          {cases.length === 0 ? <p className="pb note">No case matches.</p> : null}
        </div>
      </section>
      <p className="note">
        <b>One action per row, and it is the same action.</b> A row opens its case; everything else
        a case can do belongs to the section that owns it — pinning a set to Upload, approving a
        plan or accepting a run to Run, filing to Committee. There is no batch state and no second
        selection model, so nothing on this page can act on four cases at once without a person
        having read four cases.
      </p>
    </div>
  );
}
