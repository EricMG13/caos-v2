"""Phase 5 exit test: CP-1 end to end, against a provider that really answers.

`docs/REBUILD_PLAN.md` Phase 5 exits on `test_authority_bytes_mismatch_refuses`
(in `test_methodology_bundle.py`) and this file's
`test_cp1_produces_canonical_envelope_with_anchored_citations`.

The envelope tests below run offline against a stub, because the shape rules are
the host's and must hold whatever the provider says. The last test is the live
one: it calls a real model, and what comes back has to survive the same rules
plus citation anchoring against the real token index. It skips with its reason
without a credential and fails instead of skipping under
`CAOS_REQUIRE_PROVIDER=1`.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from conftest import approve_run

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.engine.route import ResolvedRoute, resolve_route
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import Bundle
from server.methodology.envelope import (
    Claim,
    Envelope,
    Readiness,
    parse_claims,
    parse_qa,
    parse_readiness,
)
from server.methodology.executor import (
    Assignment,
    Delivery,
    Upstream,
    UpstreamClaim,
    build_prompt,
    execute_module,
)
from server.provider import OpenRouter
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.budget import reserve
from server.store.runs import start_attempt, start_run

VENDORED = Path(__file__).resolve().parents[1] / "vendor/deploy-v"

LIVE_KEY = os.environ.get("OPENROUTER_API_KEY")
LIVE_MODEL = os.environ.get("OPENROUTER_MODEL")
PROVIDER_REQUIRED = os.environ.get("CAOS_REQUIRE_PROVIDER") == "1"
_NO_CREDENTIAL = "OPENROUTER_API_KEY is unset: there is no live provider to call"

# One line per block, so a quote is a phrase on one line of one block.
REPORT = b"""Acme Holdings plc annual report 2026
Total debt at 31 December 2026 was USD 1,240.0m
Cash and equivalents stood at USD 310.5m
"""


@pytest.fixture
def bundle() -> Bundle:
    return Bundle(root=VENDORED)


@pytest.fixture
def admitted(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> tuple[StoreConnection, UUID, BlobStore]:
    """A case with one source admitted; a run pinned after it delivers its blocks."""
    conn, case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    [source_id] = admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[Document(filename=BoundaryText.of("report.txt"), data=REPORT)],
    )
    return conn, source_id, blobs


def _body(
    source_id: UUID,
    quote: str = "Total debt at 31 December 2026",
    page: int = 1,
) -> str:
    return json.dumps(
        {
            "claims": [
                {
                    "statement": "Total debt was USD 1,240.0m at the year end.",
                    "citations": [
                        {
                            "source_id": str(source_id),
                            "page": page,
                            "matched_text": quote,
                        }
                    ],
                }
            ]
        }
    )


def _attempt(
    conn: StoreConnection, blobs: BlobStore, module_id: str = "CP-1"
) -> dict[str, Any]:
    """Commit this test's setup, then reserve one explicitly named execution."""
    row = conn.execute("SELECT case_id FROM cases").fetchone()
    assert row is not None
    route = _catalog_route()
    node = next(node for node in route.nodes if node.module_id == module_id)
    run = start_run(conn, row[0])
    conn.commit()
    approve_run(
        conn,
        case_id=row[0],
        run_id=run,
        route=route,
        bundle=Bundle(VENDORED),
    )
    attempt = start_attempt(conn, run, node.route_node_id)
    reserve(conn, attempt, Decimal("0.5"))
    return {
        "blobs": blobs,
        "assignment": Assignment(module_id, run, node, route, attempt),
    }


def test_the_retired_envelope_still_serialises_canonically() -> None:
    """Pure: the claims `Envelope` (unreachable since f-1c, deleted in f-2b)
    serialises to one byte string whatever order it was built in."""
    from server.methodology.runner import canonical

    claim = Claim(statement=BoundaryText.of("Debt was stated."), citations=())
    envelope = Envelope("CP-1", "b" * 64, "a" * 64, (claim,), 0, (), "Passed")
    rebuilt = Envelope("CP-1", "b" * 64, "a" * 64, (claim,), 0, (), "Passed")
    assert canonical(envelope) == canonical(rebuilt)
    assert json.loads(canonical(envelope))["qa_status"] == "Passed"


@pytest.mark.parametrize(
    ("body", "expected", "result"),
    [
        ('{"qa_status": "Passed"}', True, "Passed"),
        ("{}", False, None),
        ('{"qa_status": "Not Reviewed"}', True, RefusalCode.ENVELOPE_INVALID),
        ('{"qa_status": "Passed"}', False, RefusalCode.ENVELOPE_UNDECLARED_FIELD),
    ],
)
def test_parse_qa_bounds_the_qa_verdict(
    body: str, expected: bool, result: object
) -> None:
    if isinstance(result, RefusalCode):
        with pytest.raises(Refusal) as refused:
            parse_qa(body, expected=expected)
        assert refused.value.code is result
    else:
        assert parse_qa(body, expected=expected) == result


def _catalog_route() -> ResolvedRoute:
    catalog = json.loads(
        (
            VENDORED
            / "skills/cp-os-credit-os/references"
            / "CREDIT_OS_V_MODULE_CATALOG_v2.json"
        ).read_text(encoding="utf-8")
    )
    return resolve_route(catalog, "FULL_CREDIT_32", "FULL_CREDIT_ASSESSMENT")


@pytest.mark.parametrize(
    "body",
    ["not json at all", "[]", '{"claims": []}', '{"claims": "one"}', "{}"],
)
def test_a_body_that_is_not_the_envelope_is_refused(body: str) -> None:
    with pytest.raises(Refusal) as caught:
        parse_claims(body, delivered={uuid4()})

    assert caught.value.code is RefusalCode.ENVELOPE_INVALID


def test_the_refusal_carries_none_of_the_module_output() -> None:
    """The body is a completion, and a completion echoes the prompt."""
    with pytest.raises(Refusal) as caught:
        parse_claims('{"claims": "Total debt at 31 December 2026"}', delivered=set())

    leaked = str(caught.value) + repr(caught.value) + repr(caught.value.__cause__)
    assert "Total debt" not in leaked


def test_build_prompt_names_every_delivered_source() -> None:
    source_id = uuid4()
    delivered = [
        Delivery(
            source_id=source_id,
            block_id="b000000",
            page=1,
            text=BoundaryText.of("x"),
        ),
    ]

    prompt = build_prompt("CP-1", b"AUTHORITY BYTES", delivered)

    assert "AUTHORITY BYTES" in prompt
    assert str(source_id) in prompt


@pytest.mark.live_provider
def test_cp1_produces_canonical_envelope_with_anchored_citations(
    admitted: tuple[StoreConnection, UUID, BlobStore], bundle: Bundle
) -> None:
    """The Phase 5 exit test. A real model, a real answer, and a host that
    refuses everything it cannot re-derive.

    What is asserted is not the model's wording -- that is its job and it varies.
    It is that whatever came back survived the closed schema, named only
    delivered evidence, and had every quote re-located in the token index with
    a rectangle the host derived rather than the module supplied.
    """
    if LIVE_KEY is None or LIVE_MODEL is None:
        if PROVIDER_REQUIRED:
            pytest.fail(_NO_CREDENTIAL)
        pytest.skip(_NO_CREDENTIAL)
    conn, _source_id, blobs = admitted

    outcome = execute_module(
        conn,
        bundle,
        **_attempt(conn, blobs),
        provider=OpenRouter(api_key=LIVE_KEY, model=LIVE_MODEL),
    )

    envelope = outcome.envelope
    assert envelope.module_id == "CP-1"
    assert envelope.claims, "a module that cited nothing produced no envelope"
    for claim in envelope.claims:
        assert claim.statement.value.strip()
        assert claim.citations, "every claim carries evidence"
        for citation in claim.citations:
            assert citation.document_sha256
            assert citation.bboxes, "the host derived a rectangle for the quote"
            for box in citation.bboxes:
                assert box.x0 < box.x1 and box.y0 < box.y1


ROUTE = frozenset({"CP-0", "CP-1", "CP-2"})
EXPECTED = frozenset({"CP-1", "CP-2"})


def _answer(rows: object) -> str:
    """A gate answer whose map is `rows`, whatever shape the case gives it."""
    return json.dumps({"claims": [], "content_to_module_map": rows})


_ROW = {"module_id": "CP-1", "readiness_status": "READY", "readiness_effect": "e"}


def _row(**fields: object) -> dict[str, object]:
    """`_ROW` with whatever the case replaces. Typed `object`, because half the
    cases below are about a row whose values are not strings."""
    return {**_ROW, **fields}


def _map(**statuses: str) -> str:
    """The gate's whole answer for the modules named, every row valid."""
    rows = [
        _row(module_id=name, readiness_status=status, readiness_effect=f"{name} effect")
        for name, status in statuses.items()
    ]
    return _answer(rows)


def test_the_gate_returns_a_readiness_row_for_every_module_it_was_asked_about() -> None:
    rows = parse_readiness(
        _map(**{"CP-1": "READY", "CP-2": "BLOCKED"}), expected=EXPECTED
    )

    assert [row.module_id for row in rows] == ["CP-1", "CP-2"]
    assert isinstance(rows[0], Readiness)
    assert rows[1].readiness_status == "BLOCKED"
    assert rows[1].readiness_effect.value == "CP-2 effect"


def test_a_gate_answer_missing_a_pinned_module_is_refused() -> None:
    """Identifying the runnable modules is CP-0's own job (`REBUILD_PLAN.md`
    Phase 11), so a map that skips one is incomplete rather than permissive."""
    with pytest.raises(Refusal) as caught:
        parse_readiness(_map(**{"CP-1": "READY"}), expected=EXPECTED)

    assert caught.value.code is RefusalCode.READINESS_INCOMPLETE


# The other module `EXPECTED` names, answered properly: each case below is about
# one row, and a map covering only that row would refuse READINESS_INCOMPLETE
# before the check under test was reached.
_OK = _row(module_id="CP-2")


@pytest.mark.parametrize(
    "rows",
    [
        pytest.param("READY", id="not a list"),
        pytest.param([{"module_id": "CP-1"}], id="row missing keys"),
        pytest.param([_row(confidence=90), _OK], id="undeclared key"),
        pytest.param([_row(readiness_status="PROBABLY"), _OK], id="unknown status"),
        pytest.param([_row(module_id="CP-9"), _OK], id="unknown module"),
        pytest.param([_row(), _row(readiness_status="BLOCKED")], id="duplicate module"),
        pytest.param([_row(module_id=["CP-1"]), _OK], id="non-string module id"),
        pytest.param(
            [_row(readiness_effect=90), _OK], id="non-string readiness effect"
        ),
    ],
)
def test_a_readiness_map_the_host_cannot_bound_is_refused(rows: object) -> None:
    with pytest.raises(Refusal) as caught:
        parse_readiness(_answer(rows), expected=EXPECTED)

    assert caught.value.code is RefusalCode.READINESS_INVALID


def test_only_the_gate_module_may_return_a_readiness_map() -> None:
    """A module the host did not ask for a verdict is asked for none: the key is
    undeclared for it, and an undeclared key refuses the envelope."""
    with pytest.raises(Refusal) as caught:
        parse_readiness(_map(**{"CP-1": "READY"}), expected=frozenset())

    assert caught.value.code is RefusalCode.ENVELOPE_UNDECLARED_FIELD


def test_a_module_asked_for_no_verdict_and_giving_none_is_accepted() -> None:
    assert parse_readiness(_body(uuid4()), expected=frozenset()) == []


def test_the_gate_is_asked_for_a_verdict_on_every_other_pinned_module() -> None:
    prompt = build_prompt(
        "CP-0", b"AUTHORITY BYTES", [], gate_expects=frozenset({"CP-1", "CP-2"})
    )

    assert "content_to_module_map" in prompt
    assert "CP-1" in prompt and "CP-2" in prompt
    assert "READY_WITH_LIMITATIONS" in prompt


def test_a_module_that_is_not_the_gate_is_asked_for_no_verdict() -> None:
    prompt = build_prompt("CP-1", b"AUTHORITY BYTES", [])

    assert "content_to_module_map" not in prompt


def test_a_node_receives_its_direct_predecessors_accepted_claims() -> None:
    """The chain: what CP-1 established reaches CP-2's prompt as context, ahead
    of the evidence and marked as not being any.

    The assembly is what this asserts, over an `Upstream` the test hands in.
    That those values are read from the host's own stored artifact rather than
    from a caller's summary is `test_the_loop_hands_each_node_its_predecessors_results`
    in `tests/test_loop_charges.py`, which takes them back out of a real run.
    """
    upstream = [
        Upstream(
            module_id="CP-1",
            claims=(
                UpstreamClaim(
                    statement="Total debt was USD 1,240.0m at the year end.",
                    quotes=("Total debt at 31 December 2026",),
                ),
            ),
        )
    ]

    prompt = build_prompt("CP-2", b"AUTHORITY BYTES", [], upstream=upstream)

    assert "--- UPSTREAM" in prompt
    assert "CP-1" in prompt
    assert "Total debt was USD 1,240.0m at the year end." in prompt
    assert "Total debt at 31 December 2026" in prompt
    assert prompt.index("--- UPSTREAM") < prompt.index("--- EVIDENCE ---")


def test_a_node_with_no_accepted_predecessor_gets_no_upstream_section() -> None:
    assert "--- UPSTREAM" not in build_prompt("CP-0", b"AUTHORITY BYTES", [])


def test_the_upstream_section_says_it_is_not_evidence() -> None:
    """A module may not cite it, and the prompt is where it is told so; the
    refusal if it tries is `CITATION_NOT_LOCATED`, tested below."""
    prompt = build_prompt(
        "CP-2",
        b"AUTHORITY BYTES",
        [],
        upstream=[Upstream(module_id="CP-1", claims=())],
    )

    assert "not evidence" in prompt
