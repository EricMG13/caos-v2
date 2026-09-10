"""The deliverable: one HTML file, and a render that originates nothing.

`SYSTEM_SPEC.md` §7. The host renders from the frozen snapshot -- the accepted
artifacts in route order, every figure carrying its citation, then the analyst's
narrative and the module provenance index.

The structural claim is the one worth protecting: *the render is a function of
frozen bytes*. It takes a payload and returns a page. It has no store, no
connection and no clock, so there is no editorial boundary to police -- nothing
here can reach past the payload to fetch something newer, prettier or different.
That is what `test_the_deliverable_renders_from_the_frozen_payload_alone`
enforces by rendering with the store closed.

The consequence is deliberate: both sides of an unresolved conflict, `Restricted`
and `SCREENING_ONLY` qualifications reach the page exactly as the artifacts carry
them. A render that tidied them would be originating an opinion.

It prints to paper. No PDF, deck, dashboard or workbook, and no network: a page
that fetched a stylesheet would render differently the day the stylesheet moved,
and this file has to render the same in ten years.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from html import escape
from typing import Any

from server.refusals import Refusal, RefusalCode

# Every approved copy says so on its face. The bytes that carry an opinion are
# not the bytes that carry a filing (`SYSTEM_SPEC.md` §7).
PENDING = "PENDING APPROVAL"


def render(payload: Mapping[str, Any]) -> bytes:
    """The frozen payload as one self-contained HTML file.

    Pure: no I/O, no clock, no randomness. The same payload renders
    byte-identically, which is what makes the audit package's re-render a check
    rather than a second opinion.
    """
    case = _text(payload, "case_title")
    revision = _text(payload, "revision_id")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)

    body = "\n".join(_artifact(artifact) for artifact in artifacts)
    narrative = _narrative(payload.get("narrative"))
    provenance = _provenance(artifacts)

    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{escape(case)} — {escape(revision)}</title>\n"
        # Inline, and print-first. A page that fetched a stylesheet would render
        # differently the day that stylesheet moved.
        "<style>\n"
        "body{font:11pt/1.45 Georgia,serif;max-width:44em;margin:2em auto;color:#111}\n"
        "h1,h2{font-weight:600;line-height:1.2}\n"
        ".status{border:1px solid #111;padding:.4em .8em;display:inline-block}\n"
        "blockquote{border-left:3px solid #999;margin:.6em 0;\n"
        "padding:.2em 1em;color:#333}\n"
        ".cite{font-size:9pt;color:#555}\n"
        "@media print{body{margin:0;max-width:none}}\n"
        "</style>\n</head>\n<body>\n"
        f"<h1>{escape(case)}</h1>\n"
        f'<p class="status">{escape(PENDING)}</p>\n'
        f"<p>Revision {escape(revision)}</p>\n"
        f"{body}\n"
        f"{narrative}"
        f"{provenance}"
        "</body>\n</html>\n"
    ).encode()


def _artifact(artifact: object) -> str:
    """One module's accepted output, with every figure carrying its citation."""
    if not isinstance(artifact, Mapping):
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
    module_id = _text(artifact, "module_id")
    claims = artifact.get("claims")
    if not isinstance(claims, list):
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)

    rows = []
    for claim in claims:
        if not isinstance(claim, Mapping):
            raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
        statement = escape(_text(claim, "statement"))
        citations = claim.get("citations")
        if not isinstance(citations, list) or not citations:
            # §7 says every figure carries its citation. An uncited claim in a
            # frozen payload is a freeze that should not have happened, and the
            # render is the last place it can still be caught.
            raise Refusal(RefusalCode.DELIVERABLE_UNCITED_FIGURE)
        rows.append(
            f"<p>{statement}</p>\n"
            + "\n".join(_citation(citation) for citation in citations)
        )

    return f"<h2>{escape(module_id)}</h2>\n" + "\n".join(rows)


def _citation(citation: object) -> str:
    if not isinstance(citation, Mapping):
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
    quote = escape(_text(citation, "matched_text"))
    document = escape(_text(citation, "document_sha256"))
    page = escape(str(citation.get("page", "")))
    return (
        f"<blockquote>{quote}</blockquote>\n"
        f'<p class="cite">{document[:12]} · page {page}</p>'
    )


def _narrative(narrative: object) -> str:
    if narrative is None:
        return ""
    if not isinstance(narrative, str):
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
    return f"<h2>Analyst narrative</h2>\n<p>{escape(narrative)}</p>\n"


def _provenance(artifacts: Sequence[object]) -> str:
    """Which module produced what, under which build and authority.

    Not decoration: it is how a reader checks that the page in front of them came
    from the methodology the run was pinned to.
    """
    rows = "\n".join(
        f"<li>{escape(_text(artifact, 'module_id'))} · "
        f"build {escape(_text(artifact, 'build_id'))[:12]} · "
        f"authority {escape(_text(artifact, 'authority_digest'))[:12]}</li>"
        for artifact in artifacts
        if isinstance(artifact, Mapping)
    )
    return f"<h2>Module provenance</h2>\n<ul>\n{rows}\n</ul>\n"


def _text(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise Refusal(RefusalCode.DELIVERABLE_PAYLOAD_INVALID)
    return value
