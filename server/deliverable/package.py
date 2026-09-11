"""The audit package: verifiable with the standard library alone.

`SYSTEM_SPEC.md` §7. The package re-renders the export from the frozen payload
and is verifiable with nothing but the standard library.

"With the standard library alone" is a promise about *who can check it*, not
about how it is built. Someone handed this package in five years must be able to
verify it with a Python that has never installed a dependency -- no psycopg, no
pdfminer, no access to the store it came from, no version of this repository.
`verify_package` therefore imports `hashlib`, `json` and `zipfile`, reads only
what the archive holds, and re-renders through the one function that was already
pure for the same reason.

What it proves, and what it does not: it proves the payload hashes to what the
receipt says, that the page re-renders byte-identically from that payload, and
that the receipt fills all three roles with three different people. It cannot
prove the chain was never rewritten wholesale -- that is what comparing the
retained `audit_head` against a live one is for (`server/store/audit.py`).
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

# The three roles `SYSTEM_SPEC.md` section 7 keeps apart: the analyst who signed
# the opinion, whoever froze it, and the independent filer. Named here because a
# check that counted them without naming them is what let one go missing.
ROLES = ("signed_by", "frozen_by", "filed_by")

PAYLOAD = "payload.json"
RECEIPT = "receipt.json"
EXPORT = "deliverable.html"


@dataclass(frozen=True, slots=True)
class Verification:
    """What a reader learns from the archive, and why it failed if it did."""

    verified: bool
    reason: str | None = None


def build_package(payload: bytes, receipt: bytes, export: bytes) -> bytes:
    """The three files a reader needs, and nothing that would date.

    Fixed timestamps and no compression metadata, so the same inputs build the
    same archive: an audit package whose bytes moved with the clock could not be
    compared against a retained copy.
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in ((PAYLOAD, payload), (RECEIPT, receipt), (EXPORT, export)):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return buffer.getvalue()


def verify_package(archive_bytes: bytes) -> Verification:
    """Check a package using the standard library and nothing else.

    Deliberately importing nothing from this repository except the render, which
    is pure. A verifier that needed the store would only work where the store is,
    which is the one place a package does not need verifying.
    """
    try:
        with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
            payload = archive.read(PAYLOAD)
            receipt = json.loads(archive.read(RECEIPT))
            export = archive.read(EXPORT)
    except (zipfile.BadZipFile, KeyError, ValueError):
        return Verification(False, "the archive is not a readable package")

    digest = hashlib.sha256(payload).hexdigest()
    if digest != receipt.get("payload_sha256"):
        return Verification(False, "the payload does not hash to what the receipt says")

    # Filled before distinct, and in that order. Counting a set of three reads
    # meant "three people", but an absent role arrived as `None` and counted as
    # one of them -- so a receipt naming two signatories and omitting the third
    # made a set of three and verified, which is the one shape this check is
    # here to refuse. A role that names nobody is refused before the roles are
    # compared, because "fewer than three people" is the wrong thing to tell a
    # reader holding a receipt that is simply incomplete.
    named = [receipt.get(role) for role in ROLES]
    if any(not isinstance(actor, str) or not actor.strip() for actor in named):
        return Verification(False, "the receipt does not name all three roles")
    if len({str(actor).strip() for actor in named}) != 3:
        return Verification(False, "the receipt names fewer than three people")

    from server.deliverable.render import render

    if render(json.loads(payload)) != export:
        return Verification(False, "the export does not re-render from the payload")

    return Verification(True)


def write_package(path: Path, archive_bytes: bytes) -> None:
    """Write a package out. Never overwriting: a filed deliverable that could be
    replaced in place is not one anybody can rely on having read."""
    if path.exists():
        raise FileExistsError(str(path))
    path.write_bytes(archive_bytes)
