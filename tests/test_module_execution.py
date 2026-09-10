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
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from server.blobs import BlobStore
from server.boundary_text import BoundaryText
from server.evidence.ingest import Document, admit_pack
from server.methodology.bundle import Bundle
from server.methodology.envelope import Claim, Envelope, parse_claims
from server.methodology.executor import (
    Delivery,
    build_prompt,
    deliver,
    execute_module,
)
from server.provider import Completion, OpenRouter
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection

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


@dataclass
class _Stub:
    """Answers with whatever body the test wants to put through the host."""

    body: str

    def complete(self, prompt: str, *, json_object: bool = False) -> Completion:
        self.prompt = prompt
        return Completion(
            content=self.body, charge=Decimal("0.001"), generation_id="gen-stub"
        )


@pytest.fixture
def bundle() -> Bundle:
    return Bundle(root=VENDORED)


@pytest.fixture
def admitted(
    case: tuple[StoreConnection, UUID], tmp_path: Path
) -> tuple[StoreConnection, UUID, list[Delivery]]:
    """A case with one source admitted and its blocks delivered to a node."""
    conn, case_id = case
    blobs = BlobStore(tmp_path / "blobs")
    [source_id] = admit_pack(
        conn,
        blobs,
        case_id=case_id,
        documents=[Document(filename=BoundaryText.of("report.txt"), data=REPORT)],
    )
    blocks = conn.execute(
        "SELECT block_id FROM source_blocks WHERE source_id = %s ORDER BY block_id",
        (source_id,),
    ).fetchall()
    delivered = deliver(conn, [(source_id, str(b[0])) for b in blocks])
    return conn, source_id, delivered


def _body(source_id: UUID, quote: str = "Total debt at 31 December 2026") -> str:
    return json.dumps(
        {
            "claims": [
                {
                    "statement": "Total debt was USD 1,240.0m at the year end.",
                    "citations": [
                        {
                            "source_id": str(source_id),
                            "page": 1,
                            "matched_text": quote,
                        }
                    ],
                }
            ]
        }
    )


def test_the_envelope_carries_the_hosts_identity_not_the_modules(
    admitted: tuple[StoreConnection, UUID, list[Delivery]], bundle: Bundle
) -> None:
    """Invariant 3. The module is asked for CP-1 and the envelope says CP-1,
    whatever the module put in its own body."""
    conn, source_id, delivered = admitted

    envelope = execute_module(
        conn,
        bundle,
        module_id="CP-1",
        delivered=delivered,
        provider=_Stub(_body(source_id)),
    )

    assert isinstance(envelope, Envelope)
    assert envelope.module_id == "CP-1"
    assert envelope.build_id.startswith("a43cb903")
    assert len(envelope.authority_digest) == 64


def test_a_claim_carries_the_hosts_anchored_citations_not_the_modules(
    admitted: tuple[StoreConnection, UUID, list[Delivery]], bundle: Bundle
) -> None:
    """A `Claim` pairs the statement with what the *host* derived. The module
    sent a page and a phrase; what the claim holds is a document digest and a
    rectangle it never saw (invariant 11)."""
    conn, source_id, delivered = admitted

    envelope = execute_module(
        conn,
        bundle,
        module_id="CP-1",
        delivered=delivered,
        provider=_Stub(_body(source_id)),
    )

    [claim] = envelope.claims
    assert isinstance(claim, Claim)
    assert claim.statement.value.startswith("Total debt")
    [citation] = claim.citations
    assert citation.document_sha256
    assert citation.bboxes


def test_a_quote_the_host_cannot_locate_refuses_the_envelope(
    admitted: tuple[StoreConnection, UUID, list[Delivery]], bundle: Bundle
) -> None:
    """Invariant 11, before the artifact. The module quoted something plausible
    that is not in the evidence, and no envelope exists as a result."""
    conn, source_id, delivered = admitted

    with pytest.raises(Refusal) as caught:
        execute_module(
            conn,
            bundle,
            module_id="CP-1",
            delivered=delivered,
            provider=_Stub(_body(source_id, quote="Total debt was USD 2,000.0m")),
        )

    assert caught.value.code is RefusalCode.CITATION_NOT_LOCATED


def test_a_citation_naming_undelivered_evidence_is_refused(
    admitted: tuple[StoreConnection, UUID, list[Delivery]], bundle: Bundle
) -> None:
    conn, _source_id, delivered = admitted

    with pytest.raises(Refusal) as caught:
        execute_module(
            conn,
            bundle,
            module_id="CP-1",
            delivered=delivered,
            provider=_Stub(_body(uuid4())),
        )

    assert caught.value.code is RefusalCode.CITATION_NOT_DELIVERED


def test_an_undeclared_field_refuses_the_envelope(
    admitted: tuple[StoreConnection, UUID, list[Delivery]], bundle: Bundle
) -> None:
    """`extra="forbid"`. Dropping the key instead is how a module carries state
    past a reviewer reading the declared shape."""
    conn, source_id, delivered = admitted
    body = json.loads(_body(source_id))
    body["claims"][0]["confidence"] = 0.9

    with pytest.raises(Refusal) as caught:
        execute_module(
            conn,
            bundle,
            module_id="CP-1",
            delivered=delivered,
            provider=_Stub(json.dumps(body)),
        )

    assert caught.value.code is RefusalCode.ENVELOPE_UNDECLARED_FIELD


def test_an_uncited_claim_is_refused(
    admitted: tuple[StoreConnection, UUID, list[Delivery]], bundle: Bundle
) -> None:
    """This system does not store assertions."""
    conn, _source_id, delivered = admitted
    body = {"claims": [{"statement": "Leverage looks fine.", "citations": []}]}

    with pytest.raises(Refusal) as caught:
        execute_module(
            conn,
            bundle,
            module_id="CP-1",
            delivered=delivered,
            provider=_Stub(json.dumps(body)),
        )

    assert caught.value.code is RefusalCode.ENVELOPE_UNCITED_CLAIM


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


def test_the_prompt_carries_the_authority_and_the_evidence(
    admitted: tuple[StoreConnection, UUID, list[Delivery]], bundle: Bundle
) -> None:
    conn, source_id, delivered = admitted
    stub = _Stub(_body(source_id))

    execute_module(conn, bundle, module_id="CP-1", delivered=delivered, provider=stub)

    assert "cp-1-canonical-data-foundation" in stub.prompt, "the skill is the authority"
    assert str(source_id) in stub.prompt
    assert "Total debt at 31 December 2026" in stub.prompt


def test_build_prompt_names_every_delivered_source() -> None:
    source_id = uuid4()
    delivered = [
        Delivery(source_id=source_id, block_id="b000000", text=BoundaryText.of("x")),
    ]

    prompt = build_prompt("CP-1", b"AUTHORITY BYTES", delivered)

    assert "AUTHORITY BYTES" in prompt
    assert str(source_id) in prompt


def test_cp1_produces_canonical_envelope_with_anchored_citations(
    admitted: tuple[StoreConnection, UUID, list[Delivery]], bundle: Bundle
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
    conn, _source_id, delivered = admitted

    envelope = execute_module(
        conn,
        bundle,
        module_id="CP-1",
        delivered=delivered,
        provider=OpenRouter(api_key=LIVE_KEY, model=LIVE_MODEL),
    )

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
