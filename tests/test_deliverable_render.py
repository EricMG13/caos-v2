"""Phase 8 exit: the page renders from frozen bytes and nothing else.

`docs/REBUILD_PLAN.md` Phase 8 names
`test_the_deliverable_renders_from_the_frozen_payload_alone` among its three.
`SYSTEM_SPEC.md` §7 says the render *originates nothing*: it is a function of
frozen bytes, so there is no editorial boundary to police.

A test that rendered with a live connection to hand would pass whether or not
that were true, so this one closes the store first and renders from the payload
alone. The other two exit tests -- the filing chain and the audit package --
arrive with the chain they check.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from server.boundary_text import BoundaryText
from server.deliverable.render import PENDING, render
from server.refusals import Refusal, RefusalCode
from server.store import apply_schema, connect
from server.store.runs import create_case

REVISION = "rev-001"

PAYLOAD_DATA: dict[str, Any] = {
    "case_title": "Acme Holdings plc",
    "revision_id": REVISION,
    "artifacts": [
        {
            "module_id": "CP-1",
            "build_id": "a43cb903ca2751f79e77b6da71f6ea131b8462a3",
            "authority_digest": "0302b789df5d0cae" + "0" * 48,
            "claims": [
                {
                    "statement": "Total debt was USD 1,240.0m at the year end.",
                    "citations": [
                        {
                            "document_sha256": "6fc4a221c5d5" + "0" * 52,
                            "page": 1,
                            "matched_text": "Total debt at 31 December 2026",
                        }
                    ],
                }
            ],
        }
    ],
    "narrative": "Leverage is inside the covenant with limited headroom.",
}


def test_the_deliverable_renders_from_the_frozen_payload_alone(
    empty_database: str,
) -> None:
    """A named exit test. The store is closed before the render runs.

    §7's claim is structural: the render is a function of frozen bytes. If it
    could reach past the payload for anything -- a title, a digest, a fresher
    artifact -- this would raise rather than return a page.
    """
    with connect(empty_database) as conn:
        apply_schema(conn)
        create_case(conn, BoundaryText.of("Acme Holdings plc"))
        conn.commit()
        first = render(PAYLOAD_DATA)
        conn.close()

        second = render(PAYLOAD_DATA)

    assert first == second, "the same payload renders byte-identically"
    assert b"Acme Holdings plc" in first
    assert PENDING.encode() in first, "approved bytes always read PENDING APPROVAL"
    assert b"Total debt at 31 December 2026" in first, "the figure carries its quote"
    assert b"Module provenance" in first


def test_the_render_reaches_no_network_and_no_clock() -> None:
    """It prints to paper and has to render the same in ten years. A page that
    fetched a stylesheet would render differently the day the stylesheet moved."""
    page = render(PAYLOAD_DATA)

    assert b"http://" not in page
    assert b"https://" not in page
    assert b"<link" not in page
    assert b"<script" not in page


def test_an_uncited_figure_is_refused_at_the_render() -> None:
    """§7: every figure carries its citation. An uncited claim inside a frozen
    payload is a freeze that should not have happened, and this is the last
    place it can still be caught."""
    payload = json.loads(json.dumps(PAYLOAD_DATA))
    payload["artifacts"][0]["claims"][0]["citations"] = []

    with pytest.raises(Refusal) as caught:
        render(payload)

    assert caught.value.code is RefusalCode.DELIVERABLE_UNCITED_FIGURE
