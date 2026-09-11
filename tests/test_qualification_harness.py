"""The harness: a qualification set performed, not merely compared.

`docs/REBUILD_PLAN.md` Phase 10 names three things — "the qualification-set
harness, the answer keys, the matrix". The keys and the matrix landed first and
`build_matrix` had to be handed a `runs` mapping it could not produce, because
`QualificationSet` modelled only half of what `CONTEXT.md` says a set is: "the
immutable **cases** and answer keys". A case is its inputs. Without them there
is nothing to perform.

So a case now carries its documents and the route it is run under, alongside the
citations a correct run must produce, and `perform` admits each case, runs it,
and hands the matrix the mapping it used. The set's digest covers the inputs
too — two sets with identical answer keys over different documents are different
sets, and a verdict binding one must not read as binding the other.

What the harness must not become: a second execution path. It calls `run_route`
like every other caller, through the same provider seam, under the same
reservations. A qualification run that took a shortcut would be qualifying a
system nobody ships.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.ingest import Document
from server.methodology.bundle import Bundle
from server.provider import Completion
from server.qualification.harness import Harness, perform
from server.qualification.matrix import (
    ExpectedCitation,
    Matrix,
    QualificationCase,
    QualificationSet,
    assert_measurable,
    qualification_set_digest,
)
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection
from server.store.runs import run_status

REPO = Path(__file__).resolve().parents[1]
VENDORED = REPO / "vendor/deploy-v"
CATALOG = json.loads(
    (
        VENDORED / "skills/cp-os-credit-os/references"
        "/CREDIT_OS_V_MODULE_CATALOG_v2.json"
    ).read_text(encoding="utf-8")
)
PROFILE = "FULL_CREDIT_32"
SELECTION = "DEEP_RESEARCH"
ESTIMATE = Decimal("0.50")

QUOTE = "Total debt at 31 December 2026"
REPORT = b"""Acme Holdings plc annual report 2026
Total debt at 31 December 2026 was USD 1,240.0m
"""
OTHER = b"""Borealis Industries plc annual report 2026
Total debt at 31 December 2026 was USD 880.0m
"""


@dataclass
class _Completions:
    """Answers every module with one claim, cited to whatever it was delivered.

    Deliberately not told which source to cite: it reads the prompt the host
    built, which is what makes the run a real one rather than a rehearsal.
    """

    prompts: list[str] = field(default_factory=list)

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        self.prompts.append(prompt)
        source_id = prompt.split("source_id: ")[1].split("\n")[0].strip()
        return Completion(
            content=json.dumps(
                {
                    "claims": [
                        {
                            "statement": "Total debt was reported.",
                            "citations": [
                                {
                                    "source_id": source_id,
                                    "page": 1,
                                    "matched_text": QUOTE,
                                }
                            ],
                        }
                    ]
                }
            ),
            charge=Decimal("0.0000041"),
            generation_id="gen-harness-test",
        )


def _case(label: str, data: bytes, *, quote: str = QUOTE) -> QualificationCase:
    from hashlib import sha256

    return QualificationCase(
        label=label,
        documents=(Document(filename=BoundaryText.of("report.txt"), data=data),),
        profile_id=PROFILE,
        selection_id=SELECTION,
        expects=(
            ExpectedCitation(
                module_id="CP-0",
                document_sha256=sha256(data).hexdigest(),
                matched_text=quote,
            ),
        ),
    )


def _count(conn: StoreConnection, sql: str) -> int:
    """One number from the store. `fetchone` is nullable; a test that indexed it
    blind would crash where it meant to assert."""
    row = conn.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


def _perform(
    conn: StoreConnection, blobs: BlobStore, qualification: QualificationSet
) -> Matrix:
    return perform(
        conn,
        blobs,
        Harness(
            bundle=Bundle(root=VENDORED),
            catalog=CATALOG,
            completions=_Completions(),
            estimate=ESTIMATE,
        ),
        qualification=qualification,
    )


def test_the_harness_performs_every_case_and_reports_one_row_each(
    empty_database: str, tmp_path: Path
) -> None:
    """The deliverable: a set goes in, a matrix comes out, nothing in between is
    the caller's to wire.

    Two cases over different documents, so a harness that ran one and reported
    two, or admitted both into one case, fails rather than passing on a set too
    small to tell the difference.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()
        blobs = BlobStore(tmp_path / "blobs")
        qualification = QualificationSet(
            cases=(_case("acme-2026", REPORT), _case("borealis-2026", OTHER))
        )

        matrix = _perform(conn, blobs, qualification)

        assert matrix.qualification_set_sha256 == qualification_set_digest(
            qualification
        )
        assert [row.case_label for row in matrix.rows] == [
            "acme-2026",
            "borealis-2026",
        ]
        for row in matrix.rows:
            assert row.proven is True, row.refusal
            assert row.missed == ()
            assert len(row.met) == 1
        # Each case is its own case row and its own run: a harness that reused
        # one would let one case's evidence answer another's key.
        assert _count(conn, "SELECT count(*) FROM cases") == 2
        runs = conn.execute("SELECT run_id FROM runs").fetchall()
        assert len(runs) == 2
        for [run_id] in runs:
            assert run_status(conn, UUID(str(run_id))) is RunStatus.COMPLETE


def test_the_harness_runs_through_the_same_loop_as_everything_else(
    empty_database: str, tmp_path: Path
) -> None:
    """Not a second execution path.

    A qualification run that skipped the reservation, the attempt ledger or the
    route pin would be qualifying a system nobody ships. Each is checked by its
    own record rather than by reading the harness.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()
        blobs = BlobStore(tmp_path / "blobs")

        _perform(conn, blobs, QualificationSet(cases=(_case("acme-2026", REPORT),)))

        assert _count(conn, "SELECT count(*) FROM run_routes") == 1
        # Two nodes of the pathway: an attempt, a reservation and a charge each.
        for table in ("run_attempts", "budget_reservations", "budget_ledger"):
            assert _count(conn, f"SELECT count(*) FROM {table}") == 2, table
        reserved = conn.execute("SELECT DISTINCT amount FROM budget_reservations")
        assert [row[0] for row in reserved.fetchall()] == [ESTIMATE]


def test_a_key_naming_a_document_the_case_does_not_carry_is_refused(
    empty_database: str, tmp_path: Path
) -> None:
    """An unanswerable key is a set defect, not a row that always misses.

    Before the cases were in the set there was no way to notice: a key could
    name any digest at all. Now the set holds both halves, so the question "can
    this case's key ever be met" has an answer, and a set that cannot be
    satisfied by any correct run is refused before a single provider call.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()
        unanswerable = replace(
            _case("acme-2026", REPORT),
            expects=(
                ExpectedCitation(
                    module_id="CP-0",
                    document_sha256="c" * 64,
                    matched_text=QUOTE,
                ),
            ),
        )

        with pytest.raises(Refusal) as refused:
            _perform(
                conn,
                BlobStore(tmp_path / "blobs"),
                QualificationSet(cases=(unanswerable,)),
            )
        assert refused.value.code is RefusalCode.QUALIFICATION_KEY_UNANSWERABLE
        # Refused before anything ran, not after paying for it.
        assert _count(conn, "SELECT count(*) FROM runs") == 0


def test_a_case_with_no_documents_is_refused(
    empty_database: str, tmp_path: Path
) -> None:
    """A case with no inputs cannot be run and cannot be cited."""
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()
        with pytest.raises(Refusal) as refused:
            _perform(
                conn,
                BlobStore(tmp_path / "blobs"),
                QualificationSet(cases=(replace(_case("a", REPORT), documents=()),)),
            )
        assert refused.value.code is RefusalCode.QUALIFICATION_SET_EMPTY


def test_the_digest_covers_the_inputs_not_only_the_answers() -> None:
    """Two sets with identical keys over different documents are different sets.

    This is the hole folding the cases in closes. A verdict binds a
    qualification-set digest; if that digest ignored the documents, a signature
    given over one body of evidence would read as binding another.
    """
    base = QualificationSet(cases=(_case("acme-2026", REPORT),))
    digest = qualification_set_digest(base)

    moved = [
        QualificationSet(cases=(_case("acme-2026", OTHER),)),
        QualificationSet(
            cases=(replace(_case("acme-2026", REPORT), profile_id="OTHER_PROFILE"),)
        ),
        QualificationSet(
            cases=(replace(_case("acme-2026", REPORT), selection_id="BASELINE"),)
        ),
        QualificationSet(
            cases=(
                replace(
                    _case("acme-2026", REPORT),
                    documents=(
                        Document(filename=BoundaryText.of("renamed.txt"), data=REPORT),
                    ),
                ),
            )
        ),
    ]
    for changed in moved:
        assert qualification_set_digest(changed) != digest, changed.cases[0]


def test_the_digest_still_does_not_depend_on_the_order_of_cases() -> None:
    """Folding the inputs in must not make the set's identity an accident."""
    first, second = _case("a-case", REPORT), _case("b-case", OTHER)

    assert qualification_set_digest(
        QualificationSet(cases=(first, second))
    ) == qualification_set_digest(QualificationSet(cases=(second, first)))


def test_assert_measurable_is_the_one_place_the_rule_lives() -> None:
    """The guard is public so the harness can apply it before it spends.

    `build_matrix` refuses an unmeasurable set too, but by then a harness would
    have paid for every run in it. One exported check rather than a copy in each
    caller: two copies of a rule are two rules, and the second one drifts.
    """
    for unmeasurable in (
        QualificationSet(cases=()),
        QualificationSet(cases=(replace(_case("a", REPORT), expects=()),)),
        QualificationSet(cases=(replace(_case("a", REPORT), documents=()),)),
    ):
        with pytest.raises(Refusal) as refused:
            assert_measurable(unmeasurable)
        assert refused.value.code is RefusalCode.QUALIFICATION_SET_EMPTY

    # And says nothing about a set it can measure.
    assert_measurable(QualificationSet(cases=(_case("a", REPORT),)))
