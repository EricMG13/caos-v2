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

And what only the harness can report. `assert_orchestration_proof` proves the
artifacts a run **accepted** -- true, and narrower than "the route ran". The
harness resolved and pinned the route, so it holds the node list the proof is
silent about: a `Performed` carries the run's own status and the pinned nodes
that produced nothing. That is only observable on a run that stopped short,
which is why a case whose execution refuses is recorded rather than raised --
recorded, not swallowed, in a typed field beside the proof.
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
from server.engine.route import NodeState
from server.evidence.ingest import Document
from server.methodology.bundle import Bundle
from server.provider import Completion
from server.qualification.harness import (
    Harness,
    Performed,
    PerformedSet,
    Unrun,
    perform,
)
from server.qualification.matrix import (
    ExpectedCitation,
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
    # How a case stops part-way. One numbered call rather than "everything
    # after n", because a `Harness` holds one provider for the whole set: a
    # refusal that latched would refuse every later case too, and a set that
    # carried on would be indistinguishable from one that stopped at the first.
    refuses_call: int | None = None

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        self.prompts.append(prompt)
        if len(self.prompts) == self.refuses_call:
            raise Refusal(RefusalCode.PROVIDER_UNAVAILABLE)
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


@dataclass
class _DamagesWhatWasAccepted:
    """Corrupts the artifact the run already accepted, then stops.

    A blob damaged between two nodes rather than after the run, so the bytes
    `perform` itself reads are the damaged ones. `path_of` is public for
    exactly this: proving a mismatch refusal means damaging a blob through the
    real filesystem.
    """

    conn: StoreConnection
    blobs: BlobStore
    inner: _Completions

    # What to damage on the second call. Two shapes of a store that moved
    # under a running set, and `perform` must survive both.
    loses_the_pin: bool = False

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        if not self.inner.prompts:
            return self.inner.complete(prompt, json_object=json_object)
        if self.loses_the_pin:
            # Committed, because this stands for another process moving the
            # store: `perform` rolls back the transaction the refusal leaves
            # open, and an uncommitted delete would simply come back.
            self.conn.execute("DELETE FROM run_routes")
            self.conn.commit()
        else:
            for [digest] in self.conn.execute("SELECT artifact_sha256 FROM artifacts"):
                self.blobs.path_of(str(digest)).write_bytes(b"not an envelope")
        raise Refusal(RefusalCode.PROVIDER_UNAVAILABLE)


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
    conn: StoreConnection,
    blobs: BlobStore,
    qualification: QualificationSet,
    *,
    refuses_call: int | None = None,
) -> PerformedSet:
    return perform(
        conn,
        blobs,
        Harness(
            bundle=Bundle(root=VENDORED),
            catalog=CATALOG,
            completions=_Completions(refuses_call=refuses_call),
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

        matrix = _perform(conn, blobs, qualification).matrix
        assert matrix is not None, "a set that finished has a matrix"

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


def test_a_run_that_stopped_short_is_reported_as_more_than_its_proof(
    empty_database: str, tmp_path: Path
) -> None:
    """The narrow proof, and the fact it does not carry.

    CP-0 is accepted and CP-DR never runs. `assert_orchestration_proof` proves
    the artifact that exists, because that is the true claim it makes from a run
    id alone -- and the matrix row it feeds reads `proven`. A reader could take
    that for "the route ran".

    The harness resolved and pinned the route, so it holds what the proof is
    silent about: the run's own status, and the pinned node that produced
    nothing with the state the route left it in. Those sit beside the proof and
    are not summed into it -- a run that stopped with a sound proof and a run
    that finished with an unprovable one are different things to a reviewer.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()

        performed = _perform(
            conn,
            BlobStore(tmp_path / "blobs"),
            QualificationSet(cases=(_case("acme-2026", REPORT),)),
            refuses_call=2,
        )

        [record] = performed.performed
        assert isinstance(record, Performed)
        assert record.stopped is RefusalCode.PROVIDER_UNAVAILABLE
        assert record.status is RunStatus.RUNNING, "a run that stopped never completed"
        # The proof holds, over the one artifact there was to prove.
        assert record.refusal is None
        assert record.proof is not None
        assert record.proof.run_id == record.run_id
        assert record.proof.artifacts == 1
        # And this is what the proof could not say.
        assert record.unrun == (
            Unrun(
                route_node_id=f"RN-{PROFILE}-{SELECTION}-02-CP-DR",
                state=NodeState.RUNNABLE,
            ),
        )

        # A set that stopped is not a measurement: the records are kept, the
        # matrix is withheld rather than built over the cases that happened to
        # run first.
        assert performed.matrix is None


def test_a_case_that_stops_ends_the_set_without_discarding_it(
    empty_database: str, tmp_path: Path
) -> None:
    """A refusal stops the set and keeps what it already bought.

    Two failure modes sit either side of this. Raising discards every
    `Performed` and every provider call behind it — the objection to letting
    `run_route` propagate. Carrying on bets that the refusal was this case's,
    and the ones that end a run are mostly not: a missing credential, a ceiling
    reached, a moved bundle recur on the next case and cost another run, another
    reservation nothing releases, and sometimes another charge.

    So: record it, stop, return the records. Recorded, not swallowed —
    `stopped` carries the typed code.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()

        performed = _perform(
            conn,
            BlobStore(tmp_path / "blobs"),
            QualificationSet(
                cases=(_case("acme-2026", REPORT), _case("borealis-2026", OTHER))
            ),
            refuses_call=1,
        )

        [record] = performed.performed
        assert record.case_label == "acme-2026", "the second case was never run"
        assert record.stopped is RefusalCode.PROVIDER_UNAVAILABLE
        assert record.status is RunStatus.RUNNING
        # Nothing was accepted, so there is nothing to prove -- the honest
        # refusal, not a proof over an empty run.
        assert record.proof is None
        assert record.refusal is RefusalCode.ORCHESTRATION_NOTHING_TO_PROVE
        assert [entry.route_node_id for entry in record.unrun] == [
            f"RN-{PROFILE}-{SELECTION}-01-CP-0",
            f"RN-{PROFILE}-{SELECTION}-02-CP-DR",
        ]
        assert performed.matrix is None

        # The second case cost nothing: no case row, no run, no reservation.
        assert _count(conn, "SELECT count(*) FROM cases") == 1
        assert _count(conn, "SELECT count(*) FROM runs") == 1
        assert _count(conn, "SELECT count(*) FROM budget_reservations") == 1


def test_two_cases_under_one_label_are_refused_before_either_runs(
    empty_database: str, tmp_path: Path
) -> None:
    """`build_matrix` refuses this, once every case has been paid for.

    The module's own contract is that a set is checked whole before the first
    provider call, and label distinctness is knowable from the set alone. Every
    run the old order bought was spent to learn something the labels already
    said.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()

        with pytest.raises(Refusal) as refused:
            _perform(
                conn,
                BlobStore(tmp_path / "blobs"),
                QualificationSet(cases=(_case("same", REPORT), _case("same", OTHER))),
            )

        assert refused.value.code is RefusalCode.QUALIFICATION_SET_AMBIGUOUS
        assert _count(conn, "SELECT count(*) FROM runs") == 0


def test_an_unknown_pathway_refuses_without_leaving_a_run_behind(
    empty_database: str, tmp_path: Path
) -> None:
    """Route resolution is pure, so it happens before the run exists.

    Taken after `start_run` it would leave a RUNNING run with no pin, no
    attempts and no terminal event: nothing can complete it, nothing can fail
    it, and `assert_orchestration_proof` refuses it forever.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()

        with pytest.raises(Refusal) as refused:
            _perform(
                conn,
                BlobStore(tmp_path / "blobs"),
                QualificationSet(
                    cases=(
                        replace(
                            _case("acme-2026", REPORT),
                            selection_id="NO_SUCH_PATHWAY",
                        ),
                    )
                ),
            )

        assert refused.value.code is RefusalCode.ROUTE_SELECTION_UNKNOWN
        assert _count(conn, "SELECT count(*) FROM runs") == 0


def test_an_unreadable_artifact_does_not_take_the_set_down_with_it(
    empty_database: str, tmp_path: Path
) -> None:
    """The guard on the guard.

    `_unrun` reads CP-0's body out of the blob store to recover the readiness a
    soft edge turns on. Bytes that will not load raise -- and left unguarded,
    that refusal would escape from inside the very function added to stop one
    bad case from ending the set.

    Damaged between the two nodes rather than after the run, so the read that
    meets the damage is the one `perform` itself makes. Which nodes are
    COMPLETE stays exact; what is given up is the readiness that separates a
    BLOCKED node from a RESTRICTED one.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()
        blobs = BlobStore(tmp_path / "blobs")

        performed = perform(
            conn,
            blobs,
            Harness(
                bundle=Bundle(root=VENDORED),
                catalog=CATALOG,
                completions=_DamagesWhatWasAccepted(conn, blobs, _Completions()),
                estimate=ESTIMATE,
            ),
            qualification=QualificationSet(cases=(_case("acme-2026", REPORT),)),
        )

        # It returned at all, which is the assertion.
        [record] = performed.performed
        assert record.stopped is RefusalCode.PROVIDER_UNAVAILABLE
        assert record.proof is None
        assert record.refusal is RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE
        # CP-0 has its artifact row and stays COMPLETE; CP-DR never ran.
        assert [entry.route_node_id for entry in record.unrun] == [
            f"RN-{PROFILE}-{SELECTION}-02-CP-DR"
        ]


def test_a_run_whose_pin_is_gone_reports_no_pinned_nodes(
    empty_database: str, tmp_path: Path
) -> None:
    """No pin, no pinned nodes -- the literal reading, and the only honest one.

    `_unrun` re-reads the pin rather than trusting the object this module
    resolved, for the reason `proof.py` and `matrix.py` both do: the host owns
    identity (invariant 3). What that costs is a run whose pin has gone, and
    the answer is to name nothing rather than to invent a node list. The signal
    is not lost -- the proof refuses the same run for the same reason, and
    `refusal` carries it.
    """
    from server.store import apply_schema, connect

    with connect(empty_database) as conn:
        apply_schema(conn)
        conn.commit()
        blobs = BlobStore(tmp_path / "blobs")

        performed = perform(
            conn,
            blobs,
            Harness(
                bundle=Bundle(root=VENDORED),
                catalog=CATALOG,
                completions=_DamagesWhatWasAccepted(
                    conn, blobs, _Completions(), loses_the_pin=True
                ),
                estimate=ESTIMATE,
            ),
            qualification=QualificationSet(cases=(_case("acme-2026", REPORT),)),
        )

        [record] = performed.performed
        assert record.stopped is RefusalCode.PROVIDER_UNAVAILABLE
        assert record.refusal is RefusalCode.ORCHESTRATION_ROUTE_NOT_PINNED
        assert record.unrun == ()


def test_a_performed_set_concludes_nothing() -> None:
    """The line this package holds, from the harness's side.

    `QUALIFIED` is the reviewer's word (`server/qualification/__init__.py`). The
    matrix already refuses to carry a field that reads as one; a record of what
    a run did must not smuggle one back in under a different name.

    A property of the classes, so it provisions nothing: a database and a
    provider call would only give it ways to fail that are not its subject.
    """
    forbidden = {"qualified", "verdict", "passed", "score", "assurance"}
    for holder in (PerformedSet, Performed):
        named = {name.lower() for name in holder.__dataclass_fields__}
        assert not (named & forbidden), f"{holder.__name__} concludes: {named}"
        assert not hasattr(holder, "assurance")
