"""A qualification set as a declared form on disk, and the loader that reads it.

`CLAUDE.md`'s Phase 10 ledger asked for this: a set that lives only in memory is
enough for a digest to be checkable and not enough for two people to be sure
they hold the same set, and once a case carried its documents as bytes, writing
one in Python stopped being reasonable at any real size.

**A directory, not a file.** A case carries documents, and documents are bytes.
Base64 inside one JSON file would make the set unreadable to the reviewer who is
supposed to check it; a directory lets them open the documents. So the form is a
manifest naming its cases, and the documents beside it:

    acme-q3/
      qualification.json
      documents/acme-2026/report.txt
      documents/borealis-2026/report.txt

**The digest does not move.** `qualification_set_digest` already covers each
document's filename and the hash of its bytes, so a set read from here digests
exactly as the same set built in Python -- which is the property that lets a
verdict's `qualification_set_sha256` name a directory someone is holding. The
loader adds nothing to the digest and takes nothing away; it only produces the
same dataclasses from bytes rather than from a literal.

**A document's filename is its path's last segment.** One field rather than two,
because two would be two things that can disagree and the digest covers the
filename -- a manifest that named a document `report.txt` while reading
`other.txt` would digest as the first and admit the second.

**Read the way a verdict is read.** The manifest is authored, possibly not here
and possibly years from now, so it gets the treatment `server/qualification/
verdict.py` gives a signed document: a closed shape, undeclared keys refused,
nothing coerced. Malformed is one code because it has one remedy -- fix the
file. A path leaving the set's own directory is the exception, and is kept apart
because its remedy is not the same and neither is its seriousness.

**What it does not do.** It does not judge whether the set measures anything:
`assert_measurable` is the one place that rule lives (`matrix.py`), and the
harness applies it before it spends. A loader that re-stated it would be the
second copy that drifts.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from server.boundary_text import BoundaryText
from server.evidence.ingest import Document
from server.qualification.matrix import (
    ExpectedCitation,
    QualificationCase,
    QualificationSet,
)
from server.refusals import Refusal, RefusalCode

# The manifest's name inside the set's directory. Named, because "the JSON file
# in there" is not a declared form.
MANIFEST = "qualification.json"

# The keys each declared object carries, and nothing else. Closed both ways for
# the reason every wire model here is (`CLAUDE.md`, wire strictness): a key this
# loader ignores is a statement the author believed they had made.
_CASE_KEYS = frozenset({"label", "profile_id", "selection_id", "documents", "expects"})
_EXPECT_KEYS = frozenset({"module_id", "document_sha256", "matched_text"})

# The same bound `matrix.py` puts on a label when it digests one. Stated here
# too because this is where an authored label first arrives.
_LABEL_LIMIT = 128


def load_qualification_set(root: Path) -> QualificationSet:
    """Read the set at `root`, or refuse it.

    Returns the same `QualificationSet` a caller would have built in Python, so
    everything downstream -- the digest, `assert_measurable`, the harness --
    cannot tell the two apart, which is the whole point.
    """
    cases = _declared(_manifest(root), "cases")
    return QualificationSet(
        cases=tuple(_case(root, entry) for entry in cases),
    )


def _manifest(root: Path) -> Mapping[str, Any]:
    """The manifest, parsed. Absent or unparseable says nothing about a set."""
    try:
        parsed = json.loads((root / MANIFEST).read_bytes())
    except (OSError, ValueError):
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID) from None
    if not isinstance(parsed, dict):
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID)
    if set(parsed) - {"cases"}:
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID)
    return parsed


def _case(root: Path, entry: object) -> QualificationCase:
    """One declared case, with its documents read from beside the manifest."""
    fields = _closed(entry, _CASE_KEYS)
    documents = _declared(fields, "documents")
    expects = _declared(fields, "expects")
    return QualificationCase(
        label=_text(fields, "label"),
        documents=tuple(_document(root, path) for path in documents),
        profile_id=_text(fields, "profile_id"),
        selection_id=_text(fields, "selection_id"),
        expects=tuple(_expect(item) for item in expects),
    )


def _document(root: Path, declared: object) -> Document:
    """One document, read from a path that cannot leave the set.

    Resolved and compared against the resolved root rather than inspected for
    `..`: a string check answers the spellings someone thought of, and
    `Path.resolve` answers the question actually being asked -- where does this
    end up. An absolute path is the same escape by a shorter route, and
    `joinpath` would quietly discard the root it was given.
    """
    if not isinstance(declared, str) or not declared.strip():
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID)

    base = root.resolve()
    target = (base / declared).resolve()
    if target == base or base not in target.parents:
        raise Refusal(RefusalCode.QUALIFICATION_SET_PATH_ESCAPES)

    try:
        data = target.read_bytes()
    except OSError:
        # Named and not there. A set is its bytes; one document short is not a
        # smaller set, it is a set nobody can measure the same way twice.
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID) from None

    return Document(filename=_boundary(target.name), data=data)


def _expect(item: object) -> ExpectedCitation:
    """One expected citation from the answer key."""
    fields = _closed(item, _EXPECT_KEYS)
    return ExpectedCitation(
        module_id=_text(fields, "module_id"),
        document_sha256=_text(fields, "document_sha256"),
        matched_text=_text(fields, "matched_text"),
    )


def _closed(entry: object, keys: frozenset[str]) -> Mapping[str, Any]:
    """A declared object: a mapping carrying exactly `keys`."""
    if not isinstance(entry, dict) or set(entry) != keys:
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID)
    return entry


def _declared(fields: Mapping[str, Any], key: str) -> Sequence[Any]:
    """A declared list. Empty is left to `assert_measurable`, which owns that
    rule; what is refused here is a list that is not one."""
    value = fields.get(key)
    if not isinstance(value, list):
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID)
    return value


def _text(fields: Mapping[str, Any], key: str) -> str:
    """One declared string, present and not blank."""
    value = fields.get(key)
    if not isinstance(value, str) or not value.strip():
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID)
    return value


def _boundary(name: str) -> BoundaryText:
    """A filename crossing into a set that will be digested and admitted.

    `BoundaryText` refuses what it always refuses; the refusal is retyped so a
    malformed manifest reads as a malformed manifest rather than as a boundary
    failure a caller of this function cannot place.
    """
    try:
        return BoundaryText.of(name, limit=_LABEL_LIMIT)
    except Refusal:
        raise Refusal(RefusalCode.QUALIFICATION_SET_FILE_INVALID) from None
