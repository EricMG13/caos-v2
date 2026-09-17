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

import hashlib
import json
from collections.abc import Mapping, Sequence
from html import escape
from typing import Any

# Every approved copy says so on its face. The bytes that carry an opinion are
# not the bytes that carry a filing (`SYSTEM_SPEC.md` §7).
PENDING = "PENDING APPROVAL"
# A pathway scope that is a screen, never committee clearance (`handoff.py`).
SCREENING_ONLY = "SCREENING_ONLY"


class RenderRefused(ValueError):
    """A portable render refusal; the host maps its code at its boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


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
        raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")

    # A canonical artifact's page facts come from its record (§41).
    views = [_canonical(artifact) for artifact in artifacts]
    body = "\n".join(_handoff(view) for view in views)
    narrative = _narrative(payload.get("narrative"))
    provenance = _provenance([view.provenance for view in views])

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
        "pre{white-space:pre-wrap;font:9pt/1.35 Menlo,monospace}\n"
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


class _Handoff:
    """One canonical artifact as the page shows it, read from its record."""

    __slots__ = ("citations", "markdown", "projections", "provenance")

    def __init__(self, markdown: str, record: Mapping[str, Any]) -> None:
        self.markdown = markdown
        projections = record.get("projections")
        citations = record.get("citations")
        if not isinstance(projections, Mapping) or not isinstance(citations, list):
            raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")
        self.projections = projections
        self.citations = citations
        self.provenance = {
            "module_id": _text(projections, "module_id"),
            "build_id": _text(record, "build_id"),
            "authority_digest": _text(record, "authority_digest"),
        }


def canonical_bound(artifact: Mapping[str, Any]) -> bool:
    """Whether the Markdown and record text hash to the pair the payload binds,
    and the record names that Markdown. Standard library only, like the package.
    """
    if not isinstance(artifact, Mapping):
        return False
    markdown, record = artifact.get("markdown"), artifact.get("record")
    if not isinstance(markdown, str) or not isinstance(record, str):
        return False
    try:
        document = json.loads(record)
    except ValueError:
        return False
    digest = artifact.get("artifact_sha256")
    return (
        hashlib.sha256(markdown.encode("utf-8")).hexdigest() == digest
        and hashlib.sha256(record.encode("utf-8")).hexdigest()
        == artifact.get("record_sha256")
        and isinstance(document, dict)
        and document.get("artifact_sha256") == digest
    )


def _canonical(artifact: Mapping[str, Any]) -> _Handoff:
    if not canonical_bound(artifact):
        raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")
    return _Handoff(str(artifact["markdown"]), json.loads(str(artifact["record"])))


def _handoff(view: _Handoff) -> str:
    """The Markdown as text, never markup, beside what qualifies it.

    A `Restricted` handoff keeps its limitations on the page, and a
    `SCREENING_ONLY` scope is labelled a screen whatever committee status the
    module wrote: the vendor maps no status to that scope, so the page must.
    """
    facts = view.projections
    qa = escape(_text(facts, "qa_status"))
    committee = escape(_text(facts, "committee_status"))
    scope = _text(facts, "decision_scope")
    flags = facts.get("limitation_flags")
    if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
        raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")
    if not view.citations:
        raise RenderRefused("DELIVERABLE_UNCITED_FIGURE")
    screen = (
        '<p class="status">SCREENING ONLY: a screen, not committee clearance</p>\n'
        if scope == SCREENING_ONLY
        else ""
    )
    limitations = (
        "<h3>Limitations</h3>\n<ul>\n"
        + "\n".join(f"<li>{escape(flag)}</li>" for flag in flags)
        + "\n</ul>\n"
        if flags
        else ""
    )
    return (
        f"<h2>{escape(view.provenance['module_id'])}</h2>\n"
        f'<p class="status">QA status: {qa}</p>\n'
        f"<p>Committee status as written: {committee} · "
        f"decision scope {escape(scope)}</p>\n"
        f"{screen}{limitations}"
        # §45.6: what the host verified, what the model wrote, what the host
        # computed -- in that order, never mixed.
        "<h3>Source facts (host-verified citations)</h3>\n"
        + "\n".join(_citation(citation) for citation in view.citations)
        + "\n<h3>Analysis (model-authored, not host-verified)</h3>\n"
        f"<pre>{escape(view.markdown)}</pre>\n"
        "<h3>Deterministic calculations</h3>\n"
        + (
            "<p>CP-CF forecast projection performed by the host.</p>\n"
            if _text(facts, "module_id") == "CP-CF"
            else "<p>None performed by the host on this route.</p>\n"
        )
    )


def _citation(citation: object) -> str:
    if not isinstance(citation, Mapping):
        raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")
    quote = escape(_text(citation, "matched_text"))
    document = escape(_text(citation, "document_sha256"))
    page = escape(str(citation.get("page", "")))
    return (
        f"<blockquote>{quote}</blockquote>\n"
        f'<p class="cite">{document[:12]} · page {page}</p>'
    )


def _narrative(narrative: object) -> str:
    if narrative is None or narrative == []:
        return ""
    # Historical payloads remain renderable; the save boundary accepts only spans.
    if isinstance(narrative, str):
        return f"<h2>Analyst narrative</h2>\n<p>{escape(narrative)}</p>\n"
    if not isinstance(narrative, list) or len(narrative) > 64:
        raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")
    paragraphs = []
    for paragraph in narrative:
        if not isinstance(paragraph, list) or not 1 <= len(paragraph) <= 64:
            raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")
        paragraphs.append(
            "<div>" + "".join(_span(span) for span in paragraph) + "</div>\n"
        )
    return "<h2>Analyst narrative</h2>\n" + "".join(paragraphs)


def _span(span: object) -> str:
    if isinstance(span, Mapping):
        if set(span) == {"text"} and isinstance(span["text"], str):
            return escape(span["text"])
        if set(span) == {"figure"}:
            return _citation(span["figure"])
    raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")


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
        raise RenderRefused("DELIVERABLE_PAYLOAD_INVALID")
    return value
