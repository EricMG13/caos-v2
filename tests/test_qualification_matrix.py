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
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from conftest import gate_verdict

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import Execution, run_route
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import Bundle
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
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.routes import pin_route
from server.store.runs import start_run

REPO = Path(__file__).resolve().parents[1]
VENDORED = REPO / "vendor/deploy-v"
PROFILE = "FULL_CREDIT_32"
SELECTION = "DEEP_RESEARCH"
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
                    # gate's. `catalog_route` below is CP-0 and CP-DR alone.
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
def catalog_route() -> ResolvedRoute:
    catalog = json.loads(
        (
            VENDORED / "skills/cp-os-credit-os/references"
            "/CREDIT_OS_V_MODULE_CATALOG_v2.json"
        ).read_text(encoding="utf-8")
    )
    return resolve_route(catalog, PROFILE, SELECTION)


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
    pin_route(conn, run_id, catalog_route)
    blocks = conn.execute(
        "SELECT block_id FROM source_blocks WHERE source_id = %s ORDER BY block_id",
        (source_id,),
    ).fetchall()
    run_route(
        conn,
        blobs,
        run_id=run_id,
        route=catalog_route,
        execution=Execution(
            ModuleProvider(
                conn=conn,
                bundle=Bundle(root=VENDORED),
                blobs=blobs,
                completions=_Completions(source_id),
                delivered=[(source_id, str(row[0])) for row in blocks],
                route=catalog_route,
                run_id=run_id,
            ),
            ESTIMATE,
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
    forbidden = {"qualified", "verdict", "passed", "score", "assurance"}
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
    ran.conn.execute("DELETE FROM run_routes WHERE run_id = %s", (ran.run_id,))
    ran.conn.commit()

    key = _one_case(ran)
    [row] = _matrix(ran, QualificationSet(cases=(key,))).rows
    assert row.proven is False
    assert row.refusal is RefusalCode.ORCHESTRATION_ROUTE_NOT_PINNED
    assert row.met == ()
    assert row.missed == key.expects


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
