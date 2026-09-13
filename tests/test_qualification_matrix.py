"""The qualification set, its answer keys, and the matrix a reviewer reads.

`docs/REBUILD_PLAN.md` Phase 10, the part it named no test for. A **qualification
set** is the immutable cases and answer keys one verdict is measured against
(`CONTEXT.md`); its digest is one of the six bindings `read_verdict` requires.
The matrix is what the host can put in front of a reviewer: per case, what it
could prove on its own, and which of that case's expected citations the run
actually produced.

The line this file exists to hold: **the matrix reports, it does not conclude.**
Comparing a run against an answer key is mechanical and the host may do it.
Deciding that the comparison is good enough is a reviewer's signature, and
`QUALIFIED` is their word -- so nothing here carries a verdict field, a pass
flag, or a score that reads as one. A row states what happened; the reviewer
reads the rows.

Which is also why a row survives its own failure. A matrix that stopped at the
first unprovable case would hand a reviewer less than it knew, and the first
question they would ask is what the other cases did.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from canonical_fixtures import LITE_PROFILE, LITE_SELECTION, CanonicalCompletions
from conftest import approve_run, gate_verdict, priced, route_fault
from test_orchestration_proof import _token_fault

from server import methodology
from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import Execution, run_route
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import MANIFEST_NAME, Bundle
from server.methodology.handoff import Projections
from server.methodology.runner import ModuleProvider
from server.provider import Completion
from server.qualification.matrix import (
    ExpectedCitation,
    Matrix,
    MatrixRow,
    QualificationCase,
    QualificationSet,
    build_matrix,
    qualification_set_digest,
)
from server.qualification.proof import assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.gates import withdraw_source
from server.store.members import Standing, grant
from server.store.routes import resolved_route
from server.store.runs import start_run

REPO = Path(__file__).resolve().parents[1]
VENDORED = REPO / "vendor/deploy-v"
PROFILE = LITE_PROFILE
SELECTION = LITE_SELECTION
# The claims route, kept only where a test reads a claims envelope's shape.
CLAIMS = ("FULL_CREDIT_32", "DEEP_RESEARCH")
ESTIMATE = Decimal("0.50")

QUOTE = "Total debt at 31 December 2026"
REPORT = b"""Acme Holdings plc annual report 2026
Total debt at 31 December 2026 was USD 1,240.0m
"""


@dataclass
class _Completions:
    source_id: UUID
    calls: list[str] = field(default_factory=list)

    # What the host configured; with fallbacks off it is what answers.
    model: str = "a-model/for-the-test"

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        self.calls.append(prompt[:24])
        return Completion(
            content=json.dumps(
                {
                    "claims": [
                        {
                            "statement": "Total debt was USD 1,240.0m.",
                            "citations": [
                                {
                                    "source_id": str(self.source_id),
                                    "page": 1,
                                    "matched_text": QUOTE,
                                }
                            ],
                        }
                    ],
                    # A verdict on the rest of the route, when the prompt is the
                    # gate's: only on the `CLAIMS` route, CP-0 and CP-DR.
                    **gate_verdict(prompt),
                }
            ),
            charge=Decimal("0.0000041"),
            generation_id="gen-matrix-test",
        )


@dataclass(frozen=True, slots=True)
class Ran:
    conn: StoreConnection
    blobs: BlobStore
    run_id: UUID
    case_id: UUID
    document_sha256: str


@pytest.fixture
def catalog_route(request: pytest.FixtureRequest) -> ResolvedRoute:
    catalog = json.loads(
        (
            VENDORED / "skills/cp-os-credit-os/references"
            "/CREDIT_OS_V_MODULE_CATALOG_v2.json"
        ).read_text(encoding="utf-8")
    )
    return resolve_route(catalog, *getattr(request, "param", (PROFILE, SELECTION)))


@pytest.fixture
def ran(
    case: tuple[StoreConnection, UUID], tmp_path: Path, catalog_route: ResolvedRoute
) -> Ran:
    """One case of a qualification set, really run."""
    conn, case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    [source_id] = admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[Document(filename=BoundaryText.of("report.txt"), data=REPORT)],
    )
    run_id = start_run(conn, case_id)
    conn.commit()
    bundle = Bundle(root=VENDORED)
    approve_run(
        conn,
        case_id=case_id,
        run_id=run_id,
        route=catalog_route,
        bundle=bundle,
    )
    conn.rollback()
    provider = ModuleProvider(
        conn=conn,
        bundle=bundle,
        blobs=blobs,
        completions=(
            CanonicalCompletions(source_id)
            if methodology.adapter_for(catalog_route)
            == methodology.CANONICAL_ADAPTER_VERSION
            else _Completions(source_id)
        ),
        route=catalog_route,
        run_id=run_id,
    )
    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=catalog_route,
        execution=Execution(
            provider,
            priced(ESTIMATE),
            bundle,
        ),
    )
    digest = conn.execute(
        "SELECT document_sha256 FROM live_sources WHERE source_id = %s", (source_id,)
    ).fetchone()
    assert digest is not None
    return Ran(conn, blobs, run_id, case_id, str(digest[0]))


def _one_case(
    ran: Ran, *, quote: str = QUOTE, module_id: str = "CP-0"
) -> QualificationCase:
    """One case of a set, carrying the document its expectation names.

    This suite is about the comparison rather than the running, so the case's
    inputs are the same document the `ran` fixture already admitted -- what
    matters here is that the key and the artifact meet.
    """
    return QualificationCase(
        label="acme-2026-refinancing",
        documents=(Document(filename=BoundaryText.of("report.txt"), data=REPORT),),
        profile_id=PROFILE,
        selection_id=SELECTION,
        expects=(
            ExpectedCitation(
                module_id=module_id,
                document_sha256=ran.document_sha256,
                matched_text=quote,
            ),
        ),
    )


def _matrix(ran: Ran, qualification: QualificationSet) -> Matrix:
    return build_matrix(
        ran.conn,
        ran.blobs,
        Bundle(root=VENDORED),
        qualification=qualification,
        runs={"acme-2026-refinancing": ran.run_id},
    )


def test_matrix_refuses_manifest_changed_after_its_last_proof(
    ran: Ran, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from server.qualification import matrix

    root = tmp_path / "bundle"
    shutil.copytree(VENDORED, root)
    bundle = Bundle(root)
    original = matrix._cited

    def mutate(*args: object, **kwargs: bool) -> set[tuple[str, str, str]]:
        cited = original(*args, **kwargs)  # type: ignore[arg-type]
        manifest = root / MANIFEST_NAME
        manifest.write_bytes(manifest.read_bytes() + b" ")
        return cited

    monkeypatch.setattr(matrix, "_cited", mutate)
    with pytest.raises(Refusal) as caught:
        build_matrix(
            ran.conn,
            ran.blobs,
            bundle,
            qualification=QualificationSet(cases=(_one_case(ran),)),
            runs={"acme-2026-refinancing": ran.run_id},
        )
    assert caught.value.code is RefusalCode.AUTHORITY_BYTES_MISMATCH


def test_the_matrix_reports_every_case_and_concludes_nothing(ran: Ran) -> None:
    """The deliverable of this slice, and the line it must not cross.

    A row carries what the host proved on its own and which expected citations
    the run produced. It carries no verdict, no pass flag and no score: the
    reviewer's signature is the reviewer's, and a field here that read as one
    would be the host grading itself.
    """
    qualification = QualificationSet(cases=(_one_case(ran),))
    matrix = _matrix(ran, qualification)

    assert matrix.qualification_set_sha256 == qualification_set_digest(qualification)
    assert matrix.build_id.startswith("a43cb903")
    [row] = matrix.rows
    assert row.case_label == "acme-2026-refinancing"
    assert row.proven is True
    assert row.refusal is None
    assert row.met == _one_case(ran).expects
    assert row.missed == ()

    # The structural half, from this side: no field on the matrix or its rows
    # answers "is it qualified". A reviewer reads the rows.
    # Nor any status a record projects: a SCREENING_ONLY record's committee
    # status must never reach a reviewer through the matrix as clearance.
    forbidden = {"qualified", "verdict", "passed", "score", "assurance"}
    forbidden |= {f.lower() for f in Projections.__dataclass_fields__} | {"status"}
    for holder in (matrix, row):
        named = {name.lower() for name in type(holder).__dataclass_fields__}
        assert not (named & forbidden), f"{type(holder).__name__} concludes: {named}"
    assert not hasattr(matrix, "assurance")
    assert not hasattr(row, "assurance")


def test_a_missed_answer_key_is_reported_not_hidden(ran: Ran) -> None:
    """The row a reviewer most needs to see is the one that did not match.

    A matrix that reported only what matched would be an argument rather than
    evidence, and the case it dropped is the case the reviewer is being asked
    about.
    """
    missing = _one_case(ran, quote="Net leverage at 31 December 2026")
    matrix = _matrix(ran, QualificationSet(cases=(missing,)))

    [row] = matrix.rows
    assert row.proven is True, "the run is sound; it simply did not cite this"
    assert row.met == ()
    assert row.missed == missing.expects


def test_a_key_naming_another_module_is_missed_not_matched(ran: Ran) -> None:
    """The right quote from the wrong module is not the answer to this key."""
    elsewhere = _one_case(ran, module_id="CP-6")
    matrix = _matrix(ran, QualificationSet(cases=(elsewhere,)))

    [row] = matrix.rows
    assert row.met == ()
    assert row.missed == elsewhere.expects


def test_a_row_carries_the_refusal_rather_than_ending_the_matrix(ran: Ran) -> None:
    """An unprovable case is a row, not an exception.

    Stopping here would hand a reviewer less than the host knows, and the first
    thing they would ask is what the other cases did.

    This case also pins where the comparison gets its module from. Losing the
    pin loses the host's only trustworthy attribution of a quote to a module:
    the envelope names its own, and invariant 3 says that is a claim, not a
    fact. So the row misses every key rather than matching on the artifact's
    word for itself -- a match the host cannot stand behind is worse to a
    reviewer than an honest miss beside a refusal that explains it.
    """
    with route_fault(ran.conn):
        ran.conn.execute("ALTER TABLE run_inputs DISABLE TRIGGER input_immutable")
        ran.conn.execute("DELETE FROM run_inputs WHERE run_id = %s", (ran.run_id,))
        ran.conn.execute("ALTER TABLE run_inputs ENABLE TRIGGER input_immutable")
        ran.conn.execute("DELETE FROM run_routes WHERE run_id = %s", (ran.run_id,))
    ran.conn.commit()

    key = _one_case(ran)
    [row] = _matrix(ran, QualificationSet(cases=(key,))).rows
    assert row.proven is False
    assert row.refusal is RefusalCode.ORCHESTRATION_ROUTE_NOT_PINNED
    assert row.met == ()
    assert row.missed == key.expects


_SECONDARY_REFUSALS = (
    RefusalCode.ROUTE_IDENTITY_INVALID,
    RefusalCode.STORE_UNAVAILABLE,
    RefusalCode.RUN_NOT_FOUND,
)


@pytest.mark.parametrize("code", _SECONDARY_REFUSALS)
def test_refusal(ran: Ran, monkeypatch: pytest.MonkeyPatch, code: RefusalCode) -> None:
    from server.qualification import matrix

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise Refusal(code)

    monkeypatch.setattr(matrix, "_cited", refuse)
    key = _one_case(ran)
    if code is not RefusalCode.ROUTE_IDENTITY_INVALID:
        with pytest.raises(Refusal, match=f"^{code}$"):
            _matrix(ran, QualificationSet(cases=(key,)))
        return
    [row] = _matrix(ran, QualificationSet(cases=(key,))).rows
    assert row.refusal is code
    assert not row.proven and not row.met and row.missed == key.expects


def test_the_matrix_refuses_a_key_with_no_run(ran: Ran) -> None:
    """A case silently skipped is the vacuous pass in its purest form."""
    orphan = replace(_one_case(ran), label="not-a-case-that-ran")
    with pytest.raises(Refusal) as refused:
        _matrix(ran, QualificationSet(cases=(_one_case(ran), orphan)))

    assert refused.value.code is RefusalCode.QUALIFICATION_RUN_MISSING


def test_the_matrix_refuses_a_set_with_nothing_in_it(ran: Ran) -> None:
    """An empty qualification set measures nothing and would match everything."""
    with pytest.raises(Refusal) as empty:
        _matrix(ran, QualificationSet(cases=()))
    assert empty.value.code is RefusalCode.QUALIFICATION_SET_EMPTY

    with pytest.raises(Refusal) as expectless:
        _matrix(ran, QualificationSet(cases=(replace(_one_case(ran), expects=()),)))
    assert expectless.value.code is RefusalCode.QUALIFICATION_SET_EMPTY


def test_the_matrix_refuses_two_keys_for_one_case(ran: Ran) -> None:
    """One case, one key. Two would make "the answer" depend on read order."""
    with pytest.raises(Refusal) as refused:
        _matrix(ran, QualificationSet(cases=(_one_case(ran), _one_case(ran))))

    assert refused.value.code is RefusalCode.QUALIFICATION_SET_AMBIGUOUS


def test_a_qualification_set_digest_binds_every_case_and_key(ran: Ran) -> None:
    """The digest a verdict binds has to move when the set does.

    `read_verdict` takes `qualification_set_sha256` on trust -- it checks the
    shape, not the contents. What stops a signature outliving the answer keys it
    was given is that editing any key produces a different digest, so the
    reviewer's binding no longer names the set in front of you.
    """
    base = QualificationSet(cases=(_one_case(ran),))
    digest = qualification_set_digest(base)
    assert len(digest) == 64
    assert digest == qualification_set_digest(
        QualificationSet(cases=(_one_case(ran),))
    ), "the same set digests the same, or nothing can be compared against it"

    moved = [
        QualificationSet(cases=(_one_case(ran, quote="Something else entirely"),)),
        QualificationSet(cases=(_one_case(ran, module_id="CP-6"),)),
        QualificationSet(cases=(replace(_one_case(ran), label="another-case"),)),
        QualificationSet(
            cases=(
                _one_case(ran),
                replace(_one_case(ran), label="a-second-case"),
            )
        ),
    ]
    for changed in moved:
        assert qualification_set_digest(changed) != digest


def test_the_digest_does_not_depend_on_the_order_keys_were_written_in(
    ran: Ran,
) -> None:
    """Two people assembling the same set must bind the same digest.

    A digest that moved when the keys were listed in another order would make
    the set's identity an accident of authorship, and two reviewers signing the
    same body of cases would bind two different things.
    """
    first = replace(_one_case(ran), label="a-case")
    second = replace(_one_case(ran), label="b-case")

    assert qualification_set_digest(
        QualificationSet(cases=(first, second))
    ) == qualification_set_digest(QualificationSet(cases=(second, first)))


def test_a_matrix_row_is_immutable_once_reported(ran: Ran) -> None:
    """Evidence a reader can edit after the fact is not evidence."""
    [row] = _matrix(ran, QualificationSet(cases=(_one_case(ran),))).rows
    assert isinstance(row, MatrixRow)

    with pytest.raises(AttributeError):
        row.proven = False  # type: ignore[misc]
    assert not hasattr(row, "__dict__")


def test_a_case_label_crosses_the_boundary_where_it_is_digested(ran: Ran) -> None:
    """A case label is human-authored and the digest is where it becomes pinned.

    `CLAUDE.md` "Boundary text": a bidi override in a case label would make the
    matrix render one case name while the digest bound another -- the reviewer
    signing a set whose contents read differently to them than to the store.
    """
    deceptive = QualificationSet(
        cases=(replace(_one_case(ran), label="acme\u202e-2026"),)
    )

    with pytest.raises(Refusal) as refused:
        qualification_set_digest(deceptive)
    assert refused.value.code is RefusalCode.BOUNDARY_TEXT_INVALID


# Every shape a stored artifact can take that is not a readable envelope. The
# matrix must survive each: the proof is what judges an artifact, and it has
# already run for the row by the time the comparison reads it.
UNREADABLE: list[bytes] = [
    b"{]not json at all",
    b'"a string, validly encoded"',
    b'{"claims": "not a list"}',
    b'{"claims": [["not a mapping"]]}',
    b'{"claims": [{"citations": "not a list"}]}',
    b'{"claims": [{"citations": ["not a mapping"]}]}',
    b'{"claims": [{"citations": [{"document_sha256": 7, "matched_text": 7}]}]}',
]


@pytest.mark.parametrize("catalog_route", [CLAIMS], indirect=True)
@pytest.mark.parametrize("stored", UNREADABLE)
def test_an_unreadable_artifact_cites_nothing_and_does_not_end_the_matrix(
    ran: Ran, stored: bytes
) -> None:
    """The comparison reads artifacts it did not write, at every depth.

    A reader that raised here would let one corrupt artifact destroy a whole
    matrix, and the reviewer would lose every other case to it. The row instead
    says what is true: the host could not prove this case, and it cites nothing
    this key asked for.
    """
    digest = ran.blobs.put(stored)
    ran.conn.execute(
        "UPDATE artifacts SET artifact_sha256 = %s WHERE run_id = %s",
        (digest, ran.run_id),
    )
    ran.conn.commit()

    key = _one_case(ran)
    [row] = _matrix(ran, QualificationSet(cases=(key,))).rows
    assert row.proven is False
    # Which code fires depends on which of the proof's checks the shape trips
    # first -- a valid JSON object with no `build_id` is a moved build before it
    # is an unreadable claim list. `tests/test_orchestration_proof.py` pins that
    # ordering; what matters here is that the row carries *a* reason and the
    # comparison still ran.
    assert row.refusal is not None
    assert row.met == ()
    assert row.missed == key.expects


def test_a_canonical_run_is_scored_on_its_records_anchored_citations(ran: Ran) -> None:
    """Every node's record cites under the module the pin names (§42.4)."""
    keys = tuple(
        ExpectedCitation(module, ran.document_sha256, QUOTE)
        for module in ("CP-0", "CP-L10", "CP-5")
    )
    case = replace(_one_case(ran), expects=keys)
    [row] = _matrix(ran, QualificationSet(cases=(case,))).rows
    assert (row.proven, row.refusal, row.met, row.missed) == (True, None, keys, ())


def test_a_canonical_run_that_does_not_prove_scores_nothing(ran: Ran) -> None:
    """A record is read only after the proof holds: an unproven quote is no answer."""
    with _token_fault(ran.conn):
        ran.conn.execute("DELETE FROM source_tokens")
    ran.conn.commit()
    key = _one_case(ran)
    [row] = _matrix(ran, QualificationSet(cases=(key,))).rows
    assert row.refusal is RefusalCode.ORCHESTRATION_CITATION_LOST
    assert (row.proven, row.met, row.missed) == (False, (), key.expects)


def _after_proof(
    monkeypatch: pytest.MonkeyPatch,
    before: Callable[[], object],
    after: Callable[[], object],
) -> None:
    """Run `before`, the real proof, then `after`, inside the matrix's row."""
    from server.qualification import matrix
    from server.qualification.proof import assert_orchestration_proof as proof

    def around(*args: object, **kwargs: object) -> object:
        before()
        proven = proof(*args, **kwargs)  # type: ignore[arg-type]
        after()
        return proven

    monkeypatch.setattr(matrix, "assert_orchestration_proof", around)


def test_a_record_that_moves_after_the_proof_does_not_change_the_score(
    ran: Ran, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The matrix scores what the proof proved; it reads no record again."""
    _after_proof(
        monkeypatch,
        lambda: None,
        lambda: ran.conn.execute("UPDATE run_attempts SET ordinal = ordinal + 1"),
    )
    key = _one_case(ran)
    [row] = _matrix(ran, QualificationSet(cases=(key,))).rows
    assert (row.proven, row.refusal, row.met, row.missed) == (
        True,
        None,
        key.expects,
        (),
    )


def test_a_source_withdrawn_after_the_proof_is_not_scored(
    ran: Ran, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invariant 1: scoring is a use, so withdrawal is checked at it too."""
    actor = uuid4()
    grant(ran.conn, case_id=ran.case_id, user_id=actor, standing=Standing.APPROVER)
    ran.conn.commit()
    [source_id] = [
        UUID(str(r[0]))
        for r in ran.conn.execute(
            "SELECT source_id FROM live_sources WHERE case_id = %s", (ran.case_id,)
        ).fetchall()
    ]
    ran.conn.rollback()
    _after_proof(
        monkeypatch,
        lambda: None,
        lambda: withdraw_source(
            ran.conn, case_id=ran.case_id, actor_id=actor, source_id=source_id
        ),
    )
    key = _one_case(ran)
    [row] = _matrix(ran, QualificationSet(cases=(key,))).rows
    assert row.refusal is RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED
    assert (row.proven, row.met, row.missed) == (False, (), key.expects)


def test_an_artifact_accepted_after_the_proof_is_not_scored(
    ran: Ran, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CP-5 is held out of the store while the proof runs and returns after it:
    a second read would score a record the proof never saw."""
    held = "SELECT * FROM artifacts WHERE run_id = %s AND route_node_id = %s"
    [cp5] = [n.route_node_id for n in _route_of(ran).nodes if n.module_id == "CP-5"]

    def hold() -> None:
        ran.conn.execute("CREATE TEMP TABLE held_cp5 AS " + held, (ran.run_id, cp5))
        ran.conn.execute(
            "DELETE FROM artifacts"
            " WHERE attempt_id IN (SELECT attempt_id FROM held_cp5)"
        )

    def accept() -> None:
        ran.conn.execute("INSERT INTO artifacts SELECT * FROM held_cp5")

    _after_proof(monkeypatch, hold, accept)
    keys = tuple(
        ExpectedCitation(module, ran.document_sha256, QUOTE)
        for module in ("CP-0", "CP-L10", "CP-5")
    )
    case = replace(_one_case(ran), expects=keys)
    [row] = _matrix(ran, QualificationSet(cases=(case,))).rows
    assert (row.proven, row.refusal) == (True, None)
    assert (row.met, row.missed) == (keys[:2], keys[2:])


def _route_of(ran: Ran) -> ResolvedRoute:
    route = resolved_route(ran.conn, ran.run_id)
    ran.conn.rollback()
    assert route is not None
    return route


@pytest.mark.parametrize("catalog_route", [CLAIMS], indirect=True)
def test_a_claims_run_scores_its_envelopes_as_before(ran: Ran) -> None:
    """A claims proof names no quote; the matrix reads its envelopes unchanged."""
    proof = assert_orchestration_proof(
        ran.conn, ran.blobs, Bundle(root=VENDORED), run_id=ran.run_id
    )
    ran.conn.rollback()
    assert proof.anchored == frozenset()
    keys = tuple(
        ExpectedCitation(module, ran.document_sha256, QUOTE)
        for module in ("CP-0", "CP-DR")
    )
    case = replace(_one_case(ran), expects=keys)
    [row] = _matrix(ran, QualificationSet(cases=(case,))).rows
    assert (row.proven, row.refusal, row.met, row.missed) == (True, None, keys, ())


def test_a_canonical_proof_names_exactly_the_quotes_it_anchored(ran: Ran) -> None:
    proof = assert_orchestration_proof(
        ran.conn, ran.blobs, Bundle(root=VENDORED), run_id=ran.run_id
    )
    ran.conn.rollback()
    assert proof.anchored == {
        (module, ran.document_sha256, QUOTE) for module in ("CP-0", "CP-L10", "CP-5")
    }
