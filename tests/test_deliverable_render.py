"""Phase 8 exit: the page renders from frozen bytes and nothing else.

`docs/REBUILD_PLAN.md` Phase 8 names
`test_the_deliverable_renders_from_the_frozen_payload_alone` among its three.
`SYSTEM_SPEC.md` §7 says the render *originates nothing*: it is a function of
frozen bytes, so there is no editorial boundary to police.

A test that rendered with a live connection to hand would pass whether or not
that were true, so this one closes the store first and renders from the payload
alone. The other two exit tests -- the filing chain and the audit package --
arrive with the chain they check.

The payload below is the canonical shape `render()` understands since the
claims render path was deleted (f-2a; `docs/DECISIONS.md` §42.1): one artifact
carries a Markdown handoff and its host record, each addressed by digest, in
place of the retired `module_id`/`claims` shape. `_artifact` builds one with
correct digests by hand -- standard library only, like the render itself.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from server.boundary_text import BoundaryText
from server.deliverable.render import PENDING, RenderRefused, render
from server.refusals import RefusalCode
from server.store import apply_schema, connect
from server.store.runs import create_case

RENDER_SOURCE = (
    Path(__file__).resolve().parents[1] / "server/deliverable/render.py"
).read_text(encoding="utf-8")

REVISION = "rev-001"

MARKDOWN = "Total debt at 31 December 2026 was USD 1,240.0m.\n"
BUILD_ID = "a43cb903ca2751f79e77b6da71f6ea131b8462a3"
AUTHORITY_DIGEST = "0302b789df5d0cae" + "0" * 48
QUOTE = "Total debt at 31 December 2026"
DOCUMENT_SHA256 = "6fc4a221c5d5" + "0" * 52


def _artifact(
    markdown: str = MARKDOWN, *, projections: object = None, citations: object = None
) -> dict[str, Any]:
    """One canonical artifact, bound: the record's own digests match its bytes."""
    digest = hashlib.sha256(markdown.encode()).hexdigest()
    record = {
        "artifact_sha256": digest,
        "build_id": BUILD_ID,
        "authority_digest": AUTHORITY_DIGEST,
        "projections": (
            {
                "module_id": "CP-1",
                "qa_status": "Passed",
                "committee_status": "Committee Ready",
                "decision_scope": "COMMITTEE",
                "limitation_flags": [],
            }
            if projections is None
            else projections
        ),
        "citations": (
            [{"document_sha256": DOCUMENT_SHA256, "page": 1, "matched_text": QUOTE}]
            if citations is None
            else citations
        ),
    }
    record_json = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return {
        "markdown": markdown,
        "record": record_json,
        "artifact_sha256": digest,
        "record_sha256": hashlib.sha256(record_json.encode()).hexdigest(),
    }


PAYLOAD_DATA: dict[str, Any] = {
    "case_title": "Acme Holdings plc",
    "revision_id": REVISION,
    "artifacts": [_artifact()],
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


def test_cp_cf_render_discloses_its_host_performed_projection() -> None:
    payload = {
        **PAYLOAD_DATA,
        "artifacts": [
            _artifact(
                projections={
                    "module_id": "CP-CF",
                    "qa_status": "Passed",
                    "committee_status": "Committee Ready",
                    "decision_scope": "COMMITTEE",
                    "limitation_flags": [],
                }
            )
        ],
    }
    assert b"CP-CF forecast projection performed by the host" in render(payload)


def test_the_render_reaches_no_network_and_no_clock() -> None:
    """It prints to paper and has to render the same in ten years. A page that
    fetched a stylesheet would render differently the day the stylesheet moved."""
    page = render(PAYLOAD_DATA)

    assert b"http://" not in page
    assert b"https://" not in page
    assert b"<link" not in page
    assert b"<script" not in page


def test_an_uncited_figure_is_refused_at_the_render() -> None:
    """§7: every figure carries its citation. An uncited handoff inside a frozen
    payload is a freeze that should not have happened, and this is the last
    place it can still be caught."""
    payload = json.loads(json.dumps(PAYLOAD_DATA))
    payload["artifacts"][0] = _artifact(citations=[])

    with pytest.raises(RenderRefused) as caught:
        render(payload)

    assert caught.value.code == "DELIVERABLE_UNCITED_FIGURE"


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda p: p.update(artifacts=[]), id="no artifacts"),
        pytest.param(
            lambda p: p.update(artifacts="not-a-list"), id="artifacts not a list"
        ),
        pytest.param(
            lambda p: p["artifacts"].__setitem__(0, "not-a-mapping"),
            id="artifact not a mapping",
        ),
        pytest.param(
            lambda p: p["artifacts"][0].__setitem__("record", "not json"),
            id="record not valid json",
        ),
        pytest.param(
            lambda p: p["artifacts"].__setitem__(
                0, _artifact(projections="not-a-mapping")
            ),
            id="projections not a mapping",
        ),
        pytest.param(
            lambda p: p["artifacts"].__setitem__(0, _artifact(citations="not-a-list")),
            id="citations not a list",
        ),
        pytest.param(
            lambda p: p["artifacts"].__setitem__(
                0, _artifact(citations=["not-a-mapping"])
            ),
            id="citation not a mapping",
        ),
        pytest.param(lambda p: p.update(case_title=""), id="case_title empty"),
    ],
)
def test_a_malformed_payload_is_refused_not_crashed(mutate: object) -> None:
    """Every shape a frozen payload can be wrong in reaches the same closed
    code, `DELIVERABLE_PAYLOAD_INVALID` -- never an unhandled `TypeError` or
    `KeyError` from treating a stranger's JSON as trusted structure."""
    payload = json.loads(json.dumps(PAYLOAD_DATA))
    mutate(payload)  # type: ignore[operator]

    with pytest.raises(RenderRefused) as caught:
        render(payload)

    assert caught.value.code == "DELIVERABLE_PAYLOAD_INVALID"


def test_no_narrative_omits_the_section_rather_than_refusing() -> None:
    """The narrative is optional; its absence is not malformed."""
    payload = json.loads(json.dumps(PAYLOAD_DATA))
    del payload["narrative"]

    page = render(payload)

    assert b"Analyst narrative" not in page


def test_a_narrative_that_is_not_a_string_is_refused() -> None:
    payload = json.loads(json.dumps(PAYLOAD_DATA))
    payload["narrative"] = 123

    with pytest.raises(RenderRefused) as caught:
        render(payload)

    assert caught.value.code == "DELIVERABLE_PAYLOAD_INVALID"


def test_every_portable_render_refusal_names_a_closed_host_code() -> None:
    """The render is portable -- it ships inside an audit package and runs with
    no host beside it -- so it refuses with its own `RenderRefused` and a string
    code. The wrapper that turned that string into a `Refusal` had no caller:
    the host never renders here, and every name the render can raise is one the
    host's closed set already carries, which is what this holds."""
    with pytest.raises(RenderRefused, match="DELIVERABLE_PAYLOAD_INVALID") as portable:
        render({})

    assert portable.value.code == "DELIVERABLE_PAYLOAD_INVALID"
    raised = {
        name.strip('"')
        for name in re.findall(r"RenderRefused\((\"[A-Z_]+\")\)", RENDER_SOURCE)
    }
    assert raised == {"DELIVERABLE_PAYLOAD_INVALID", "DELIVERABLE_UNCITED_FIGURE"}
    assert raised <= {code.value for code in RefusalCode}
