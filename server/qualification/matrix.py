"""The qualification set, its answer keys, and the matrix a reviewer reads.

`docs/REBUILD_PLAN.md` Phase 10. A **qualification set** is the immutable cases
and answer keys one verdict is measured against (`CONTEXT.md`); its digest is
one of the six bindings `read_verdict` requires, and this module is where that
digest is computed.

**The matrix reports; it does not conclude.** Comparing a run against an answer
key is mechanical, and the host may do it. Deciding that the comparison is good
enough is a reviewer's signature — `QUALIFIED` is their word, not the host's
(`server/qualification/__init__.py`). So nothing here carries a verdict, a pass
flag or a score: a row states what the host could prove on its own and which
expected citations the run produced, and a reviewer reads the rows.

That is also why a row survives its own failure. An unprovable case is a row
carrying its refusal code, not an exception that ends the matrix: stopping at
the first one would hand a reviewer less than the host knows, and what the
remaining cases did is the next thing they would ask.

**What an answer key can express, and what it cannot.** A key names citations —
which quote, from which document, under which module. That is the strongest key
the canonical handoff's record can be checked against today, because a record
carries projections and citations and not typed figures. A key saying "net
leverage is 4.2x" has nothing to compare against until the record carries the
figure as a number, which is the known-gaps entry this module ships with.

Beside the citations a key may also ask what a module *concluded*
(`ExpectedProjection`, over the seven fields the host projects) and what it
*wrote in a named register cell* (`ExpectedRegister`, read through the vendor's
own register reader). None of the three is the conclusion's soundness, and a
reviewer still reads the rows.

**A canonical run is scored on its records** (`docs/DECISIONS.md` §42.4), and
only on what the proof proved: the proof returns the citations it re-anchored
under the pinned modules, and those are the run's -- nothing is read again, so
an artifact accepted after the proof is not scored, and a source withdrawn since
refuses the row. An unproven canonical run cites nothing. The matrix reports no
status a record projects, so a SCREENING_ONLY record can never reach a reviewer
through it as committee clearance.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import MODEL_MODULE, READY, ResolvedRoute, readiness_from
from server.engine.runtime import accepted_artifacts
from server.evidence.ingest import Document
from server.methodology.bundle import Bundle
from server.methodology.canonical import accepted_handoff, accepted_projections
from server.methodology.forecast import forecast_projection
from server.methodology.handoff import Projections
from server.methodology.vendor import load_vendor_contract
from server.methodology.verification import AcceptedRow
from server.qualification.proof import OrchestrationProof, assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection
from server.store.routes import resolved_route
from server.store.run_inputs import RunSubject
from server.store.runs import run_status
from server.store.source_sets import pinned_live_sources

# A run that declared its refusal must have ended on one. RUNNING and
# RUNNABLE are not answers; CANCELLED did not answer the question asked.
_ENDED = frozenset({RunStatus.BLOCKED, RunStatus.FAILED, RunStatus.COMPLETE})

# A case label is authored and reaches a digest; it is a name, not prose.
_LABEL_LIMIT = 128


@dataclass(frozen=True, slots=True)
class ExpectedCitation:
    """One thing a correct run of this case must have cited.

    The document is named by digest rather than by filename, because a
    qualification set outlives any one case's admission of it and a filename is
    not an identity.
    """

    module_id: str
    document_sha256: str
    matched_text: str


@dataclass(frozen=True, slots=True)
class ForecastValue:
    """One host-recomputed CP-CF value an independent key expects."""

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class ExpectedForecast:
    """A closed, mechanical credit-conclusion key for an accepted CP-CF run.

    The result is read through ``accepted_handoff`` and recomputed by the host;
    it is never extracted from model-authored narrative text.
    """

    scenario: str
    period_id: str
    values: tuple[ForecastValue, ...]
    currency: str
    scale: str
    perimeter: str
    qa_status: str
    limitation_flags: tuple[str, ...]
    readiness: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ExpectedProjection:
    """One host-projected field of one module's accepted handoff.

    A citation key asks whether a module's handful of length-selected quotes
    happened to include a particular line. This asks what the module concluded:
    the fields the host re-derives from the accepted Markdown and compares
    against the stored record (`accepted_projections`), so the answer is the
    host's reading and not model narrative.

    `value` is compared as a string against a scalar field, and as membership
    against a list one — one rule for both, because "the screen was Restricted"
    and "it flagged the missing audited statements" are the same kind of
    question asked of differently shaped fields.
    """

    module_id: str
    field: str
    value: str


PROJECTION_FIELDS = frozenset(
    {
        "qa_status",
        "committee_status",
        "confidence_band",
        "decision_scope",
        "limitation_flags",
        "validation_warnings",
        "downstream_consumers",
    }
)


@dataclass(frozen=True, slots=True)
class ExpectedRegister:
    """One cell of one named register of one module's accepted handoff.

    The third question an answer key can ask, and the first that reaches the
    analysis itself. A citation key asks which quotes a module drew; a
    projection key asks what its seven host-projected scalars said; this asks
    what it *wrote in a named register cell* -- a liquidity bridge's figure, a
    covenant term, a topic's materiality. Those live in the appendix registers
    the vendor's own contract declares, and the vendor ships the reader
    (`completeness_check.find_registers`), so the host locates the table by the
    bundle's rules rather than by a parser of its own (invariant 4).

    `row_key` names the row by its own cells -- `(("topic_id",
    "LIQUIDITY_MATURITIES"),)` -- rather than by position, because row order is
    the module's and a key that counted rows would measure the layout. Exactly
    one row may match: zero and two are both misses, never a guess.

    Authored from the documents, never from a run. A key taken from what a run
    wrote measures the model against itself.
    """

    module_id: str
    register_id: str
    row_key: tuple[tuple[str, str], ...]
    column: str
    expected: str


@dataclass(frozen=True, slots=True)
class QualificationCase:
    """One case of the set: its inputs, its route, and its answer key.

    Both halves in one object, because `CONTEXT.md` defines a qualification set
    as "the immutable cases and answer keys" and they are useless apart. The
    first draft of this module carried the keys alone, which is why
    `build_matrix` had to be handed a `runs` mapping it could not produce: there
    was nothing here to run.

    `expects` is this case's answer key — the citations a correct run must
    produce.
    """

    label: str
    documents: tuple[Document, ...]
    profile_id: str
    selection_id: str
    expects: tuple[ExpectedCitation, ...]
    # Who and when the run is about. A canonical-adapter route requires one
    # (`pin_run_input`); a claims route leaves it None, as every case did before.
    subject: RunSubject | None = None
    # Optional while historical citation-only sets remain reviewable.  New
    # credit-conclusion sets use this deterministic CP-CF answer key.
    forecast: ExpectedForecast | None = None
    expected_refusal: RefusalCode | None = None
    # Module ids CP-0 must find ready. A readiness key, not a citation one: the
    # host already projects `(module_id, readiness_status)` off CP-0's record
    # (`server/engine/route.py`), so this is read from what the engine gated on
    # rather than from prose. It exists because a gate that wrongly refuses a
    # module is invisible to a citation key -- the module never runs, so it
    # cites nothing, and every key aimed at it reads as a miss by the model.
    expects_ready: tuple[str, ...] = ()
    # What the modules concluded, read from the host's own projections. See
    # `ExpectedProjection`: this is the key that measures the analysis rather
    # than the draw of quotes that happened to support it.
    expects_projection: tuple[ExpectedProjection, ...] = ()
    # CP-CF is a host extension, so a forecast key must bind whether it was
    # present rather than silently qualifying the base route.
    model_extension: bool = False
    # What the modules wrote in their registers. See `ExpectedRegister`: the key
    # that can ask about a cell the host projects no scalar for.
    expects_register: tuple[ExpectedRegister, ...] = ()


@dataclass(frozen=True, slots=True)
class QualificationSet:
    """The immutable cases and answer keys one verdict is measured against."""

    cases: tuple[QualificationCase, ...]


@dataclass(frozen=True, slots=True)
class MatrixRow:
    """One case: what the host proved, and what the run did or did not cite.

    `proven` and `refusal` are the host's own claim about the run (invariant
    terms). `met` and `missed` are the mechanical comparison. Neither is a
    verdict, and there is deliberately no field that combines them into one.
    """

    case_label: str
    proven: bool
    refusal: RefusalCode | None
    met: tuple[ExpectedCitation, ...]
    missed: tuple[ExpectedCitation, ...]
    forecast_met: bool | None
    expected_refusal_met: bool | None
    ready_met: bool | None = None
    projections_met: bool | None = None
    registers_met: bool | None = None


@dataclass(frozen=True, slots=True)
class Matrix:
    """Every case of the set, and what the set and build were when it was built."""

    qualification_set_sha256: str
    build_id: str
    rows: tuple[MatrixRow, ...]


def qualification_set_digest(qualification: QualificationSet) -> str:
    """The digest a verdict binds. Moves when any case or key moves.

    `read_verdict` takes `qualification_set_sha256` on trust — it checks the
    shape, not the contents. What stops a signature outliving the answer keys it
    was given is this: edit any key and the digest no longer names the set in
    front of the reader.

    Order-independent, because two people assembling the same body of cases must
    bind the same digest; a digest that moved with authorship would make the
    set's identity an accident. Labels cross the boundary here, which is where
    they become pinned state.
    """
    assert_measurable(qualification)
    canonical = sorted(_digested(case) for case in qualification.cases)
    return sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _digested(case: QualificationCase) -> list[object]:
    """One case's digested form. A subject is appended only when declared, so a
    set of subject-free cases binds exactly the digest it bound before cases
    could carry one."""
    entry: list[Any] = [
        BoundaryText.of(case.label.strip(), limit=_LABEL_LIMIT).value,
        [case.profile_id, case.selection_id],
        # The inputs, not only the answers. Two sets with identical keys
        # over different documents are different sets, and a verdict binding
        # one must not read as binding the other.
        sorted(
            [document.filename.value, sha256(document.data).hexdigest()]
            for document in case.documents
        ),
        sorted(
            [expect.module_id, expect.document_sha256, expect.matched_text]
            for expect in case.expects
        ),
    ]
    if case.subject is not None:
        subject = case.subject
        entry.append(
            [
                subject.issuer_id,
                subject.issuer_name,
                subject.reporting_period,
                subject.analysis_date,
            ]
        )
    if case.model_extension:
        entry.append("model_extension")
    if case.forecast is not None:
        entry.append(
            [
                case.forecast.scenario,
                case.forecast.period_id,
                sorted([value.name, value.value] for value in case.forecast.values),
                case.forecast.currency,
                case.forecast.scale,
                case.forecast.perimeter,
                case.forecast.qa_status,
                sorted(case.forecast.limitation_flags),
                sorted(case.forecast.readiness),
            ]
        )
    if case.expected_refusal is not None:
        entry.append(case.expected_refusal.value)
    if case.expects_ready:
        entry.append(sorted(case.expects_ready))
    if case.expects_projection:
        entry.append(
            sorted(
                [expect.module_id, expect.field, expect.value]
                for expect in case.expects_projection
            )
        )
    if case.expects_register:
        entry.append(
            sorted(
                [
                    expect.module_id,
                    expect.register_id,
                    # The row key is a set of cell conditions, not a sequence:
                    # two authors naming the same row in either order name the
                    # same row, and the digest has to agree with them.
                    sorted([column, value] for column, value in expect.row_key),
                    expect.column,
                    expect.expected,
                ]
                for expect in case.expects_register
            )
        )
    return entry


def build_matrix(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    qualification: QualificationSet,
    runs: Mapping[str, UUID],
) -> Matrix:
    """Every case of the set against the run that covered it.

    Refuses before it reports rather than reporting a matrix nobody can rely on:
    an empty set measures nothing, two keys for one case make "the answer"
    depend on read order, and a case with no run is the vacuous pass in its
    purest form — the row that would have failed is simply not there.
    """
    assert_measurable(qualification)
    assert_unambiguous(qualification)
    labels = [case.label for case in qualification.cases]
    for label in labels:
        if label not in runs:
            raise Refusal(RefusalCode.QUALIFICATION_RUN_MISSING)

    return Matrix(
        qualification_set_sha256=qualification_set_digest(qualification),
        rows=tuple(
            _row(conn, blobs, bundle, case=case, run_id=runs[case.label])
            for case in qualification.cases
        ),
        # Validate the same manifest again after all proofs and citation reads.
        build_id=bundle.build_id,
    )


def _row(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case: QualificationCase,
    run_id: UUID,
) -> MatrixRow:
    """One case. The proof may fail; the comparison is made either way.

    What a run cited is knowable whether or not the host can vouch for how it
    was produced, and a reviewer looking at an unprovable case still wants to
    see whether it found the right evidence.
    """
    refusal: RefusalCode | None = None
    proof: OrchestrationProof | None = None
    try:
        proof = assert_orchestration_proof(conn, blobs, bundle, run_id=run_id)
    except Refusal as failed:
        refusal = failed.code

    try:
        cited = _cited(conn, run_id, proof=proof)
    except Refusal as unattributed:
        if unattributed.code not in _ROW_REFUSALS:
            raise
        refusal = unattributed.code
        cited = set()
    met = tuple(expect for expect in case.expects if _matches(expect, cited))
    return MatrixRow(
        case_label=case.label,
        proven=refusal is None,
        refusal=refusal,
        met=met,
        missed=tuple(expect for expect in case.expects if expect not in met),
        forecast_met=_forecast_met(
            conn, blobs, bundle, case=case, run_id=run_id, proof=proof
        ),
        expected_refusal_met=(
            None
            if case.expected_refusal is None
            else _refusal_met(conn, run_id, case.expected_refusal, refusal)
        ),
        ready_met=_ready_met(conn, blobs, bundle, case=case, run_id=run_id),
        projections_met=_projections_met(conn, blobs, bundle, case=case, run_id=run_id),
        registers_met=_registers_met(conn, blobs, bundle, case=case, run_id=run_id),
    )


def _refusal_met(
    conn: StoreConnection,
    run_id: UUID,
    expected: RefusalCode,
    proof_refusal: RefusalCode | None,
) -> bool:
    """Whether the run refused the way its case said it would.

    A case that declares a refusal is declaring how the run ends, and a run
    ends in one of two places: the proof cannot be taken, or execution stopped
    and wrote the reason against an attempt. Reading only the first made this
    key unanswerable by any run the system produces — a deliberately restricted
    case (`docs/REPAIR_PLAN.md` Phase 6) stops with a refusal recorded and a
    sound proof over what it did accept, so the proof says nothing and the
    stored refusal says everything.
    """
    if proof_refusal is expected:
        return True
    # A validated Blocked handoff is the route's own rule applied, so `_settle`
    # writes no `attempt_refusals` row for it -- the run's own status is where
    # that outcome is recorded.
    if (
        expected is RefusalCode.HANDOFF_BLOCKED
        and run_status(conn, run_id) is RunStatus.BLOCKED
    ):
        return True
    # The run has to have *ended*, not merely written the code somewhere. A
    # recorded refusal on a run still RUNNING or RUNNABLE is a node that failed
    # and a run that has more to do, and `complete` waives its COMPLETE check
    # for a met refusal -- so without this, a case could declare a refusal, have
    # one attempt produce it, and be signable over a run that simply stopped
    # being driven.
    if run_status(conn, run_id) not in _ENDED:
        return False
    return bool(
        conn.execute(
            "SELECT 1 FROM attempt_refusals r JOIN run_attempts t"
            " USING (attempt_id) WHERE t.run_id = %s AND r.code = %s",
            (run_id, expected.value),
        ).fetchone()
    )


def _ready_met(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case: QualificationCase,
    run_id: UUID,
) -> bool | None:
    """Whether CP-0 found every module the case names ready to run.

    Read from `readiness_from` — the same projection `node_states` gates on, so
    this asks exactly the question the engine asked and not a re-reading of the
    handoff's prose. `None` when the case names none.

    A gate that refuses a module for the wrong reason is otherwise invisible:
    the module never runs, so it cites nothing, and every citation key aimed at
    it reads as the model failing to find evidence when the truth is that the
    model was never asked.
    """
    if not case.expects_ready:
        return None
    route = resolved_route(conn, run_id)
    if route is None:
        return False
    try:
        accepted = accepted_artifacts(conn, blobs, route, run_id, bundle=bundle)
    except Refusal:
        return False
    readiness = dict(readiness_from(route, accepted))
    return all(readiness.get(module) in READY for module in case.expects_ready)


def _accepted_rows(
    conn: StoreConnection, run_id: UUID
) -> dict[str, tuple[str, str | None]]:
    """Every accepted node of the run, keyed by route node."""
    return {
        str(row[0]): (str(row[1]), None if row[2] is None else str(row[2]))
        for row in conn.execute(
            "SELECT t.route_node_id, a.artifact_sha256, a.record_sha256"
            " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
            " WHERE a.run_id = %s",
            (run_id,),
        ).fetchall()
    }


def _matches_projection(projections: Projections, expect: ExpectedProjection) -> bool:
    """One expectation against the host's re-derived projections."""
    if expect.field not in PROJECTION_FIELDS:
        return False
    found = getattr(projections, expect.field)
    if isinstance(found, tuple):
        return expect.value in found
    return str(found) == expect.value


def _projections_met(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case: QualificationCase,
    run_id: UUID,
) -> bool | None:
    """Whether every module concluded what the case says it should have.

    Read through `accepted_projections`, which rebuilds the identity from the
    store, requires the record to bind this Markdown, and re-parses the
    projections from the Markdown to compare against the record (§42.4). A
    module the case names that produced no accepted artifact is a miss, not a
    skip: the question was asked and the run did not answer it.
    """
    if not case.expects_projection:
        return None
    route = resolved_route(conn, run_id)
    if route is None:
        return False
    accepted = _accepted_rows(conn, run_id)
    wanted: dict[str, list[ExpectedProjection]] = {}
    for expect in case.expects_projection:
        wanted.setdefault(expect.module_id, []).append(expect)
    for module_id, expects in wanted.items():
        node = next((item for item in route.nodes if item.module_id == module_id), None)
        if node is None:
            return False
        rows = conn.execute(
            "SELECT a.artifact_sha256, a.record_sha256, a.attempt_id"
            " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
            " WHERE a.run_id = %s AND t.route_node_id = %s",
            (run_id, node.route_node_id),
        ).fetchall()
        if len(rows) != 1 or rows[0][1] is None:
            return False
        artifact_sha256, record_sha256, attempt_id = rows[0]
        try:
            projections = accepted_projections(
                conn,
                blobs,
                bundle,
                route,
                AcceptedRow(
                    run_id=run_id,
                    route_node_id=node.route_node_id,
                    attempt_id=UUID(str(attempt_id)),
                    artifact_sha256=str(artifact_sha256),
                    record_sha256=str(record_sha256),
                ),
                accepted=accepted,
            )
        except Refusal:
            return False
        if not all(_matches_projection(projections, expect) for expect in expects):
            return False
    return True


def _normalised_cell(value: str) -> str:
    """One register cell, column name or expected value, as a key compares them.

    NFC first, because two spellings of the same character are the same cell to
    a reader and a key authored in one must not miss a handoff written in the
    other. Then every run of whitespace collapses to one space and the ends are
    stripped: a Markdown table's cells are padded for alignment and a line may
    be wrapped, neither of which is the module saying anything different.

    **Case is preserved.** `MATERIAL` and `Material` are different values in
    every vendor vocabulary that has one, and a comparison that folded case
    would let a key pass over a cell the bundle's own validators would refuse.
    """
    return " ".join(unicodedata.normalize("NFC", value).split())


def _cell(row: Mapping[str, str], column: str) -> str | None:
    """One row's cell under `column`, normalised, or `None` if it is not there.

    The column name is matched under the same rule as the cell, because a header
    is padded and wrapped like any other cell. A register whose header names the
    same column twice answers `None`: the host does not choose between them.
    """
    wanted = _normalised_cell(column)
    found = [
        value for name, value in row.items() if _normalised_cell(str(name)) == wanted
    ]
    if len(found) != 1:
        return None
    return _normalised_cell(str(found[0]))


def _matches_register(
    registers: Mapping[str, tuple[Sequence[str], Sequence[Mapping[str, str]]]],
    expect: ExpectedRegister,
) -> bool:
    """One register expectation against what the vendor's reader found.

    Exactly one row may meet the whole `row_key`. Zero is the register not
    carrying the row the key asks about; two is the key not naming one row, and
    picking the first would make the answer depend on the order the module wrote
    its table in. Both are misses. An empty `row_key` selects nothing here --
    the loader refuses one, and a Python caller's is not silently read as "any
    row".
    """
    found = registers.get(expect.register_id)
    if not expect.row_key or not isinstance(found, tuple) or len(found) != 2:
        # Anything but the reader's `(header, rows)` is not this key's answer:
        # the host reads the vendor's shape and invents no second one.
        return False
    _header, rows = found
    matched = [
        row
        for row in rows
        if isinstance(row, Mapping)
        if all(
            _cell(row, column) == _normalised_cell(value)
            for column, value in expect.row_key
        )
    ]
    if len(matched) != 1:
        return False
    return _cell(matched[0], expect.column) == _normalised_cell(expect.expected)


def _registers_met(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case: QualificationCase,
    run_id: UUID,
) -> bool | None:
    """Whether every module wrote what the case says it should have written.

    The Markdown is read through `accepted_handoff`, which binds the record to
    it, and the registers are located by the vendor's own
    `completeness_check.find_registers` from this bundle's verified bytes: the
    host adds no table parser of its own (invariant 4). `None` when the case
    names none; a module the case names that produced no single accepted
    artifact, or an artifact that will not read, is a miss and not an exception
    -- a row survives its own failure.
    """
    if not case.expects_register:
        return None
    route = resolved_route(conn, run_id)
    if route is None:
        return False
    accepted = _accepted_rows(conn, run_id)
    find_registers = load_vendor_contract(bundle).completeness_check.find_registers
    wanted: dict[str, list[ExpectedRegister]] = {}
    for expect in case.expects_register:
        wanted.setdefault(expect.module_id, []).append(expect)
    for module_id, expects in wanted.items():
        node = next((item for item in route.nodes if item.module_id == module_id), None)
        if node is None:
            return False
        rows = conn.execute(
            "SELECT a.artifact_sha256, a.record_sha256, a.attempt_id"
            " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
            " WHERE a.run_id = %s AND t.route_node_id = %s",
            (run_id, node.route_node_id),
        ).fetchall()
        if len(rows) != 1 or rows[0][1] is None:
            return False
        artifact_sha256, record_sha256, attempt_id = rows[0]
        try:
            markdown, _record = accepted_handoff(
                conn,
                blobs,
                bundle,
                route,
                AcceptedRow(
                    run_id=run_id,
                    route_node_id=node.route_node_id,
                    attempt_id=UUID(str(attempt_id)),
                    artifact_sha256=str(artifact_sha256),
                    record_sha256=str(record_sha256),
                ),
                accepted=accepted,
            )
            registers = find_registers(
                markdown.decode("utf-8"),
                [expect.register_id for expect in expects],
            )
            if not isinstance(registers, dict):
                return False
            met = all(_matches_register(registers, expect) for expect in expects)
        except (Refusal, ValueError, TypeError, UnicodeDecodeError):
            # The reader's own faults included: an artifact the host cannot read
            # is a case it cannot score, never a case that concluded correctly.
            return False
        if not met:
            return False
    return True


def _forecast_met(  # noqa: PLR0913 -- one qualification case's bound readers
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    *,
    case: QualificationCase,
    run_id: UUID,
    proof: OrchestrationProof | None,
) -> bool | None:
    """Compare a CP-CF answer key only after the complete run proof exists."""
    expected = case.forecast
    if expected is None:
        return None
    if proof is None:
        return False
    route = resolved_route(conn, run_id)
    if route is None:
        return False
    node = next((item for item in route.nodes if item.module_id == MODEL_MODULE), None)
    if node is None:
        return False
    rows = conn.execute(
        "SELECT a.artifact_sha256, a.record_sha256, a.attempt_id"
        " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
        " WHERE a.run_id = %s AND t.route_node_id = %s",
        (run_id, node.route_node_id),
    ).fetchall()
    if len(rows) != 1 or rows[0][1] is None:
        return False
    accepted = {
        str(row[0]): (str(row[1]), None if row[2] is None else str(row[2]))
        for row in conn.execute(
            "SELECT t.route_node_id, a.artifact_sha256, a.record_sha256"
            " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
            " WHERE a.run_id = %s",
            (run_id,),
        ).fetchall()
    }
    artifact_sha256, record_sha256, attempt_id = rows[0]
    try:
        markdown, record = accepted_handoff(
            conn,
            blobs,
            bundle,
            route,
            AcceptedRow(
                run_id=run_id,
                route_node_id=node.route_node_id,
                attempt_id=UUID(str(attempt_id)),
                artifact_sha256=str(artifact_sha256),
                record_sha256=str(record_sha256),
            ),
            accepted=accepted,
        )
        result = forecast_projection(markdown)
    except (Refusal, ValueError, TypeError):
        return False
    row = next(
        (
            item
            for item in result["rows"]
            if item["case"] == expected.scenario
            and item["period_id"] == expected.period_id
        ),
        None,
    )
    return (
        row is not None
        and all(
            _forecast_values(row).get(value.name) == value.value
            for value in expected.values
        )
        and result["units"] == {"currency": expected.currency, "scale": expected.scale}
        and result["perimeter"] == expected.perimeter
        and record.projections.qa_status == expected.qa_status
        and record.projections.limitation_flags == expected.limitation_flags
        and _readiness(conn, blobs, bundle, route, run_id) == expected.readiness
    )


def _forecast_values(row: Mapping[str, object]) -> dict[str, str]:
    values: dict[str, str] = {}
    for group, item in row.items():
        if group in {"case", "period_id", "fiscal_year", "days", "unavailable_reason"}:
            continue
        if isinstance(item, dict):
            for name, value in item.items():
                if isinstance(value, dict) and isinstance(value.get("value"), str):
                    values[f"{group}.{name}"] = value["value"]
                elif isinstance(value, str):
                    values[f"{group}.{name}"] = value
        elif isinstance(item, str):
            values[group] = item
    return values


def _readiness(
    conn: StoreConnection,
    blobs: BlobStore,
    bundle: Bundle,
    route: ResolvedRoute,
    run_id: UUID,
) -> tuple[tuple[str, str], ...]:
    """The gate's revalidated readiness projection, or an empty non-match."""
    gate = next((item for item in route.nodes if item.module_id == "CP-0"), None)
    if gate is None:
        return ()
    row = conn.execute(
        "SELECT a.artifact_sha256, a.record_sha256, a.attempt_id"
        " FROM artifacts a JOIN run_attempts t ON t.attempt_id = a.attempt_id"
        " WHERE a.run_id = %s AND t.route_node_id = %s",
        (run_id, gate.route_node_id),
    ).fetchone()
    if row is None or row[1] is None:
        return ()
    try:
        _markdown, record = accepted_handoff(
            conn,
            blobs,
            bundle,
            route,
            AcceptedRow(
                run_id=run_id,
                route_node_id=gate.route_node_id,
                attempt_id=UUID(str(row[2])),
                artifact_sha256=str(row[0]),
                record_sha256=str(row[1]),
            ),
        )
    except (Refusal, ValueError, TypeError):
        return ()
    return record.projections.readiness


def _matches(expect: ExpectedCitation, cited: set[tuple[str, str, str]]) -> bool:
    """An expectation is met by the same quote, from the same document, under the
    same module. The right quote under the wrong module answers a different
    question and is not this key's answer."""
    return (expect.module_id, expect.document_sha256, expect.matched_text) in cited


# A row's own uncertainty, not a reason to end the matrix: a pin that no longer
# reads, or a proven source withdrawn before its quotes were scored.
_ROW_REFUSALS = frozenset(
    {RefusalCode.ROUTE_IDENTITY_INVALID, RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED}
)


def _cited(
    conn: StoreConnection, run_id: UUID, *, proof: OrchestrationProof | None
) -> set[tuple[str, str, str]]:
    """Every (module, document, quote) this run's proof re-anchored.

    The module is taken from the route pin, as `proof.py` takes it (invariant
    3: the host owns identity). A run with no pin cites nothing, which is a row
    that misses every key; an invalid pin refuses so `_row` records uncertainty.
    A run cites exactly what its `proof` re-anchored, and nothing without one:
    no artifact is read as a claims envelope (§42.1).
    """
    if resolved_route(conn, run_id) is None:
        return set()
    return _proven(conn, run_id, proof)


def _proven(
    conn: StoreConnection, run_id: UUID, proof: OrchestrationProof | None
) -> set[tuple[str, str, str]]:
    """A proven canonical run's anchored quotes, each document still live now.

    Scoring is a use, so a source withdrawn since the proof refuses the row
    `ORCHESTRATION_SOURCE_NOT_PINNED`, as the proof itself would (invariant 1).
    """
    if proof is None:
        return set()
    live = pinned_live_sources(conn, run_id)
    if any(document not in live for _module, document, _quote in proof.anchored):
        raise Refusal(RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED)
    return set(proof.anchored)


def assert_measurable(qualification: QualificationSet) -> None:
    """A set with no cases, a case expecting nothing, or a case with no
    documents: each measures nothing.

    Public because the harness has to apply it *before* it performs a single
    case, and a copy of the rule there would be a second place to keep in step
    with this one.

    It would also match everything, which is the shape of a qualification that
    reads as a pass because it asked no question.
    """
    if not qualification.cases:
        raise Refusal(RefusalCode.QUALIFICATION_SET_EMPTY)
    if any(
        not case.documents
        or (
            not case.expects
            and case.forecast is None
            and case.expected_refusal is None
            and not case.expects_ready
            and not case.expects_projection
            and not case.expects_register
        )
        or (case.forecast is not None and not case.forecast.values)
        for case in qualification.cases
    ):
        # A case with no declared comparison, or an empty forecast key, measures
        # nothing; a case with no documents cannot be run.  All are the same
        # pre-spend hole.
        raise Refusal(RefusalCode.QUALIFICATION_SET_EMPTY)


def assert_unambiguous(qualification: QualificationSet) -> None:
    """Refuse duplicate case labels or answer keys before either can be scored."""
    labels = [case.label for case in qualification.cases]
    if len(set(labels)) != len(labels) or any(
        len(set(case.expects)) != len(case.expects)
        or len(set(case.expects_register)) != len(case.expects_register)
        or (
            case.forecast is not None
            and len({value.name for value in case.forecast.values})
            != len(case.forecast.values)
        )
        for case in qualification.cases
    ):
        raise Refusal(RefusalCode.QUALIFICATION_SET_AMBIGUOUS)
