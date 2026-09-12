"""Phase 10's second exit: the one word the host may say about itself.

`docs/REBUILD_PLAN.md` Phase 10 defines two. `ORCHESTRATION_PROOF` is what the
host can assert on its own -- the pinned methodology ran as pinned, against the
pinned sources, and every citation re-located. `QUALIFIED` is a reviewer's
signature, and "no code path in this repository can mint" it.

Both halves are tested here. The behavioural half runs a real route against a
real source and asks the control what it can prove, then breaks each of the
three claims in turn and watches it refuse. The structural half reads the
source: a control that returned the right word today but sat beside a second
path to the other one would be one refactor from certifying itself.

The proof is deliberately re-derived rather than read back. Every fact it
checks was already checked once, when the artifact was written -- the point is
that it is checked *again*, now, against a store that may have moved since. A
proof that trusted the recorded answer would prove only that something was
recorded.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from conftest import gate_verdict
from tracked import tracked_python

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import ResolvedRoute, resolve_route
from server.engine.runtime import Execution, run_route
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import Bundle
from server.methodology.runner import ModuleProvider
from server.provider import Completion
from server.qualification import Assurance
from server.qualification.proof import OrchestrationProof, assert_orchestration_proof
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.gates import withdraw_source
from server.store.members import Standing, grant
from server.store.routes import pin_route
from server.store.runs import start_run

REPO = Path(__file__).resolve().parents[1]
VENDORED = REPO / "vendor/deploy-v"
PROFILE = "FULL_CREDIT_32"
# Two nodes, CP-0 and CP-DR: the smallest real pathway the catalog carries.
SELECTION = "DEEP_RESEARCH"
ESTIMATE = Decimal("0.50")

QUOTE = "Total debt at 31 December 2026"
REPORT = b"""Acme Holdings plc annual report 2026
Total debt at 31 December 2026 was USD 1,240.0m
"""


@dataclass
class _Completions:
    """One valid claim, cited to the one source this case holds."""

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
            generation_id="gen-proof-test",
        )


@dataclass(frozen=True, slots=True)
class Ran:
    """A completed run, and everything the proof needs to be asked about it."""

    conn: StoreConnection
    blobs: BlobStore
    run_id: UUID
    case_id: UUID
    source_id: UUID
    route: ResolvedRoute


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
    """A real route, really run, against a really ingested source.

    Nothing here is a fixture standing in for the thing it describes: the
    citations in the artifact were anchored by the host against the tokens this
    document actually produced, which is what makes re-deriving them a check
    rather than a comparison of two copies of one guess.
    """
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
    delivered = [(source_id, block) for block in _blocks(conn, source_id)]
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
                delivered=delivered,
                route=catalog_route,
            ),
            ESTIMATE,
        ),
    )
    return Ran(conn, blobs, run_id, case_id, source_id, catalog_route)


def _blocks(conn: StoreConnection, source_id: UUID) -> list[str]:
    rows = conn.execute(
        "SELECT block_id FROM source_blocks WHERE source_id = %s ORDER BY block_id",
        (source_id,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _prove(ran: Ran) -> OrchestrationProof:
    return assert_orchestration_proof(
        ran.conn, ran.blobs, Bundle(root=VENDORED), run_id=ran.run_id
    )


def _refusal(ran: Ran) -> RefusalCode:
    with pytest.raises(Refusal) as caught:
        _prove(ran)
    return caught.value.code


def names_qualified() -> set[str]:
    """Every tracked module this repository ships whose source names QUALIFIED.

    Read from the AST rather than by grep, so a mention inside a comment or a
    docstring -- which mints nothing -- does not read as a code path.

    Scope is every tracked `.py` outside `tests/`, not just `server/`: the plan
    says "no code path in this repository", and a gate script is a code path.
    The suite is excluded because asserting on the word is what these tests are
    for. TypeScript is not scanned and does not need to be -- the workspace has
    no `Assurance` to construct and no authority to construct one with
    (`CLAUDE.md`, "persona is not authority"); it can only render what the host
    serves, and the host cannot serve this.
    """
    naming: set[str] = set()
    for path in tracked_python(REPO):
        if path.is_relative_to(REPO / "tests"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            spoken = (isinstance(node, ast.Attribute) and node.attr == "QUALIFIED") or (
                isinstance(node, ast.Name) and node.id == "QUALIFIED"
            )
            declared = isinstance(node, ast.Constant) and node.value == "QUALIFIED"
            if spoken or declared:
                naming.add(str(path.relative_to(REPO)))
    return naming


def test_a_host_control_reads_orchestration_proof_never_qualified(ran: Ran) -> None:
    """Phase 10's second exit test, in two halves.

    *Behavioural.* The control asserts the three claims and returns the host's
    word. There is no argument and no store state that makes it return the
    other one -- it has no branch that could.

    *Structural.* Across every module this repository ships, `QUALIFIED` is
    named in exactly two files: the enum that declares the word, and the reader
    that relays a reviewer's signed verdict. Nothing that derives anything from
    the host's own records mentions it, so there is no second path to audit.
    That is what "no code path in this repository can mint `QUALIFIED`" has to
    mean to be checkable.
    """
    proof = _prove(ran)

    assert proof.assurance is Assurance.ORCHESTRATION_PROOF
    assert proof.run_id == ran.run_id
    assert proof.build_id.startswith("a43cb903")
    assert len(proof.route_digest) == 64
    # Both nodes of the pathway, and the citation each one carried. A proof over
    # nothing is the vacuous pass `CLAUDE.md` warns a green suite can hide.
    assert proof.artifacts == 2
    assert proof.citations == 2

    assert names_qualified() == {
        "server/qualification/__init__.py",
        "server/qualification/verdict.py",
    }


def test_the_proof_refuses_a_run_that_orchestrated_nothing(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> None:
    """Three claims about no artifacts are three claims that pass vacuously.

    The strongest proof this control could accidentally give is one about a run
    that never ran, so that case is the refusal rather than the trivial pass.
    """
    conn, case_id = case
    run_id = start_run(conn, case_id)
    conn.commit()
    empty = Ran(conn, BlobStore(tmp_path / "b"), run_id, case_id, uuid4(), None)  # type: ignore[arg-type]

    assert _refusal(empty) is RefusalCode.ORCHESTRATION_NOTHING_TO_PROVE


def test_the_proof_refuses_a_run_whose_route_was_never_pinned(
    ran: Ran,
) -> None:
    """ "Ran as pinned" is unanswerable without a pin (invariant 10)."""
    ran.conn.execute("DELETE FROM run_routes WHERE run_id = %s", (ran.run_id,))
    ran.conn.commit()

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_ROUTE_NOT_PINNED


def test_the_proof_refuses_a_node_the_pin_does_not_carry(ran: Ran) -> None:
    """An accepted artifact for a node outside the pinned route is the exact
    failure invariant 10 exists to prevent: execution that did not read the pin.
    """
    truncated = replace(ran.route, nodes=ran.route.nodes[:1])
    ran.conn.execute("DELETE FROM run_routes WHERE run_id = %s", (ran.run_id,))
    ran.conn.commit()
    pin_route(ran.conn, ran.run_id, truncated)

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_NODE_NOT_IN_ROUTE


def test_the_proof_refuses_an_artifact_from_another_build(ran: Ran) -> None:
    """Invariant 4: a run pinned to one build never executes under another.

    Checked on the bytes at use, here meaning *at proof time*: the authority the
    bundle hashes to now, not the digest the artifact remembers.
    """
    _doctor(ran, {"authority_digest": "f" * 64})

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_BUILD_MOVED


def test_the_proof_refuses_an_artifact_naming_another_build_id(ran: Ran) -> None:
    """The same claim from the other side: the build itself, not its authority."""
    _doctor(ran, {"build_id": "b0000000"})

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_BUILD_MOVED


def test_the_module_checked_is_the_pinned_one_not_the_one_claimed(ran: Ran) -> None:
    """Invariant 3: the host owns identity, here too.

    The artifact is made to claim it came from the *other* node of this route,
    leaving the authority digest of the node that actually produced it. A proof
    that read `module_id` out of the envelope would assemble the wrong module's
    authority and refuse; one that reads the route pin computes the right one
    and proves it. So passing is the assertion.
    """
    _doctor(ran, {"module_id": "CP-DR"})

    assert _prove(ran).assurance is Assurance.ORCHESTRATION_PROOF


def test_a_withdrawn_source_takes_the_proof_with_it(ran: Ran) -> None:
    """Invariant 1's second half reaches all the way here.

    Withdrawal is checked live at every use, and a proof is a use. A conclusion
    resting on evidence that has since been withdrawn is exactly what must stop
    being provable the moment it is withdrawn -- not at the next run.
    """
    actor = uuid4()
    grant(ran.conn, case_id=ran.case_id, user_id=actor, standing=Standing.APPROVER)
    ran.conn.commit()
    withdraw_source(
        ran.conn, case_id=ran.case_id, actor_id=actor, source_id=ran.source_id
    )

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_SOURCE_NOT_PINNED


def test_the_proof_refuses_a_quote_it_can_no_longer_locate(ran: Ran) -> None:
    """Invariant 11 re-checked. The source is still live and still cited; its
    coordinate index no longer holds the quote, so the citation is not one."""
    ran.conn.execute("DELETE FROM source_tokens WHERE source_id = %s", (ran.source_id,))
    ran.conn.commit()

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_CITATION_LOST


def test_the_proof_refuses_a_rectangle_that_moved_under_it(ran: Ran) -> None:
    """Re-located is not the same as re-located *where it said*.

    A proof that only asked "does this quote appear on this page" would accept a
    rectangle drawn over different text, which is invariant 11 with the
    coordinates taken out.
    """
    ran.conn.execute(
        "UPDATE source_tokens SET x0 = x0 + 17.0, x1 = x1 + 17.0 WHERE source_id = %s",
        (ran.source_id,),
    )
    ran.conn.commit()

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_CITATION_LOST


def test_the_proof_refuses_an_artifact_it_cannot_read(ran: Ran) -> None:
    """Bytes that are not an envelope prove nothing, and are not narrated."""
    digest = ran.blobs.put(b"{]not an envelope")
    ran.conn.execute(
        "UPDATE artifacts SET artifact_sha256 = %s WHERE run_id = %s",
        (digest, ran.run_id),
    )
    ran.conn.commit()

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE


def _doctor(ran: Ran, changes: dict[str, object]) -> None:
    """Rewrite the first stored artifact, as a run under another build would."""
    row = ran.conn.execute(
        "SELECT attempt_id, artifact_sha256 FROM artifacts WHERE run_id = %s"
        " ORDER BY created_at LIMIT 1",
        (ran.run_id,),
    ).fetchone()
    assert row is not None
    envelope = json.loads(ran.blobs.get(str(row[1])))
    envelope.update(changes)
    digest = ran.blobs.put(json.dumps(envelope, sort_keys=True).encode())
    ran.conn.execute(
        "UPDATE artifacts SET artifact_sha256 = %s WHERE attempt_id = %s",
        (digest, row[0]),
    )
    ran.conn.commit()


# Every shape of stored artifact that is not an envelope. Each is a separate
# branch of the reader, and each refuses with the same code: what the bytes
# actually were never travels (`CLAUDE.md`: never log document-derived text).
UNREADABLE: list[object] = [
    {"claims": "not a list"},
    {"claims": []},
    {"claims": [["not a mapping"]]},
    {"claims": [{"statement": "s", "citations": "not a list"}]},
    {"claims": [{"statement": "s", "citations": []}]},
    {"claims": [{"statement": "s", "citations": ["not a mapping"]}]},
    {"claims": [{"statement": "s", "citations": [{"document_sha256": 7}]}]},
    {
        "claims": [
            {
                "statement": "s",
                "citations": [
                    {"document_sha256": "a", "matched_text": "q", "page": "one"}
                ],
            }
        ]
    },
]


@pytest.mark.parametrize("shape", UNREADABLE)
def test_the_proof_refuses_every_shape_that_is_not_an_envelope(
    ran: Ran, shape: dict[str, object]
) -> None:
    """The whole reader surface, not one representative of it.

    A reader validated at one depth and trusted at the next is how a malformed
    artifact reaches a claim; each of these is a different depth.
    """
    _doctor(ran, shape)

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE


def test_the_proof_refuses_an_artifact_that_is_not_a_mapping(ran: Ran) -> None:
    """Valid JSON is not the same as an envelope."""
    digest = ran.blobs.put(b"[1, 2, 3]")
    ran.conn.execute(
        "UPDATE artifacts SET artifact_sha256 = %s WHERE run_id = %s",
        (digest, ran.run_id),
    )
    ran.conn.commit()

    assert _refusal(ran) is RefusalCode.ORCHESTRATION_ARTIFACT_UNREADABLE
