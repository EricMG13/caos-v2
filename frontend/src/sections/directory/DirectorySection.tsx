// Directory (IA_SPEC.md 4.1): the case register on one tab, document-first
// intake on the other. Search plus one filter, applied here to the rows the
// server sent; nothing on this page acts on more than one case.
import { useId, useState } from "react";
import { CaseRegister } from "./CaseRegister";
import { IntakeDrop, IntakeSuggestions } from "./IntakeSuggestions";
import type { ViewProps } from "@/app/views";
import { TextInput } from "@/ds/TextInput";
import type { CaseRow, DirectoryBody, Intake } from "@/wire/directory";

function matches(row: CaseRow, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return [row.case_id, row.issuer, row.sector, row.pathway, row.snapshot].some((field) =>
    field.toLowerCase().includes(needle),
  );
}

function RegisterTab({ body }: { body: DirectoryBody }) {
  const [search, setSearch] = useState(body.search);
  const [active, setActive] = useState(body.filter.active ?? "");
  const filterId = useId();
  const headingId = useId();
  const rows = body.cases.filter(
    (row) => matches(row, search) && (active === "" || row.state === active),
  );
  return (
    <div className="col">
      <div className="formulabar" role="search">
        <span className="coord">SEARCH</span>
        <TextInput
          className="tin"
          aria-label="Search cases"
          placeholder="issuer, sector, snapshot or case id"
          value={search}
          onChange={(event) => setSearch(event.currentTarget.value)}
        />
        <label htmlFor={filterId} className="lbl">
          {body.filter.label}
        </label>
        <select
          id={filterId}
          className="tin"
          value={active}
          onChange={(event) => setActive(event.currentTarget.value)}
        >
          <option value="">All</option>
          {body.filter.options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <span className="spacer" />
        <span className="tag">
          {rows.length} OF {body.cases.length} SHOWN
        </span>
      </div>
      <section className="pnl" aria-labelledby={headingId}>
        <header>
          <h2 id={headingId}>Case register</h2>
          <span className="cp">ONE ISSUER ENGAGEMENT PER ROW</span>
          <span className="right">
            <span className="tag">{body.cases.length} CASES</span>
          </span>
        </header>
        <div className="pb flush">
          <CaseRegister rows={rows} />
          {rows.length === 0 ? <p className="pb note">No case matches.</p> : null}
        </div>
      </section>
      <IntakeLine intake={body.intake} />
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

function IntakeLine({ intake }: { intake: Intake | null }) {
  if (!intake) return <p className="note">No intake is open.</p>;
  const open = intake.suggestions.filter((s) => !s.committed).length;
  return (
    <p className="note" data-intake-open>
      <b>One intake is open for review.</b> {intake.files.length}{" "}
      {intake.files.length === 1 ? "file" : "files"} admitted as one pack · {open} of{" "}
      {intake.suggestions.length} suggestions uncommitted
      {intake.run_id ? (
        <>
          {" "}
          · run <code>{intake.run_id}</code> opened for review, not accepted
        </>
      ) : null}{" "}
      · the Intake tab shows what the server proposes.
    </p>
  );
}

function Committing({ intake, caseId }: { intake: Intake; caseId: string | null }) {
  const headingId = useId();
  const route = intake.suggestions.find((s) => s.key === "route");
  return (
    <section className="pnl" aria-labelledby={headingId}>
      <header>
        <h2 id={headingId}>Committing</h2>
        <span className="cp">WHAT IT WRITES</span>
      </header>
      <div className="pb">
        <dl className="kv">
          <dt>Case</dt>
          <dd>{caseId ?? "—"}</dd>
          <dt>Files</dt>
          <dd>{intake.files.length} · one pack</dd>
          <dt>Route selection</dt>
          <dd>{route?.value ?? "—"}</dd>
          <dt>Analysis</dt>
          <dd>none</dd>
        </dl>
        <p className="note">
          The intake run already parsed and read for readiness. Committing does not accept its
          output: the case opens at <b>Run</b>, at the plan gate, with the route resolved and
          nothing pinned.
        </p>
      </div>
    </section>
  );
}

/** Bytes under a kilobyte read as bytes, and megabytes as megabytes: a 512-byte
    file is not "1 KB", nor "0 KB", and a 5 MB report is not "5120 KB". */
function sizeOf(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

function AdmittedPack({ intake }: { intake: Intake }) {
  const headingId = useId();
  return (
    <section className="pnl" aria-labelledby={headingId}>
      <header>
        <h2 id={headingId}>Admitted as one pack</h2>
        <span className="cp">ALL OR NONE</span>
        <span className="right">
          <span className="tag ok">
            {intake.files.length} OF {intake.files.length}
          </span>
        </span>
      </header>
      <div className="pb flush">
        <ul className="attlist">
          {intake.files.map((file) => (
            <li key={file.sha256} className="att">
              <span className="a">{file.name}</span>
              <span>{sizeOf(file.bytes)}</span>
              <code title={file.sha256}>{file.sha256.slice(0, 12)}</code>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function IntakeTab({ body }: { body: DirectoryBody }) {
  const caseId = body.intake?.case_id ?? null;
  return (
    <div className="cols two" data-intake>
      <div className="col">
        {body.intake ? (
          <IntakeSuggestions intake={body.intake} caseId={caseId} />
        ) : (
          <p className="note">No intake is open. Drop documents to start one.</p>
        )}
        <IntakeDrop />
      </div>
      <div className="col right">
        {body.intake ? (
          <>
            <Committing intake={body.intake} caseId={caseId} />
            <AdmittedPack intake={body.intake} />
          </>
        ) : null}
      </div>
    </div>
  );
}

export function DirectorySection({ document, tab }: ViewProps<"directory">) {
  const active = tab ?? document.chrome.tabs[0]?.id ?? "register";
  return active === "intake" ? (
    <IntakeTab body={document.body} />
  ) : (
    <RegisterTab body={document.body} />
  );
}
