"""Phase 8 exit: nobody files their own work, and the package checks itself.

`docs/REBUILD_PLAN.md` Phase 8's remaining two named tests:
`test_filing_refuses_the_opinion_signer` and
`test_audit_package_verifies_with_stdlib_alone`. The third, the render, shipped
with the pure function it is about.

`APPROVER_NOT_INDEPENDENT` is the one worth reading twice. It is not a permission
check -- the signer holds APPROVER standing and could file anything else. It is a
check that the chain has more than one person in it, because a chain where one
actor occupied every role records a decision nobody independently reviewed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from server.deliverable.filing import (
    Opinion,
    Receipt,
    file_deliverable,
    freeze,
    receipt_bytes,
    sign_opinion,
)
from server.deliverable.package import (
    EXPORT,
    PAYLOAD,
    build_package,
    verify_package,
    write_package,
)
from server.deliverable.render import render
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.members import Standing, grant

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
PAYLOAD_BYTES = json.dumps(PAYLOAD_DATA, sort_keys=True).encode("utf-8")


@pytest.fixture
def signed(case: tuple[StoreConnection, UUID]) -> tuple[StoreConnection, UUID, UUID]:
    """A case with an opinion signed on the exact payload, and its signer."""
    conn, case_id = case
    signer = uuid4()
    grant(conn, case_id=case_id, user_id=signer, standing=Standing.APPROVER)
    conn.commit()
    sign_opinion(
        conn,
        case_id=case_id,
        actor_id=signer,
        revision_id=REVISION,
        payload_sha256=_digest(PAYLOAD_BYTES),
    )
    return conn, case_id, signer


def _digest(data: bytes) -> str:
    from hashlib import sha256

    return sha256(data).hexdigest()


def _approver(conn: StoreConnection, case_id: UUID) -> UUID:
    actor = uuid4()
    grant(conn, case_id=case_id, user_id=actor, standing=Standing.APPROVER)
    conn.commit()
    return actor


def test_freezing_bytes_that_were_not_the_signed_bytes_is_refused(
    signed: tuple[StoreConnection, UUID, UUID],
) -> None:
    """A freeze of different bytes than the ones reviewed is the signature
    applied to something nobody read."""
    conn, case_id, signer = signed

    with pytest.raises(Refusal) as caught:
        freeze(
            conn,
            case_id=case_id,
            actor_id=signer,
            revision_id=REVISION,
            payload=PAYLOAD_BYTES + b" amended",
        )

    assert caught.value.code is RefusalCode.DELIVERABLE_MOVED_SINCE_SIGNING


def test_freezing_without_a_signature_is_refused(
    case: tuple[StoreConnection, UUID],
) -> None:
    conn, case_id = case
    actor = _approver(conn, case_id)

    with pytest.raises(Refusal) as caught:
        freeze(
            conn,
            case_id=case_id,
            actor_id=actor,
            revision_id="rev-unsigned",
            payload=PAYLOAD_BYTES,
        )

    assert caught.value.code is RefusalCode.DELIVERABLE_NOT_SIGNED


def test_filing_refuses_the_opinion_signer(
    signed: tuple[StoreConnection, UUID, UUID],
) -> None:
    """A named exit test.

    Not a permission check -- the signer holds APPROVER standing and could file
    anything else. It is a check that the chain has more than one person in it.
    """
    conn, case_id, signer = signed
    freezer = _approver(conn, case_id)
    freeze(
        conn,
        case_id=case_id,
        actor_id=freezer,
        revision_id=REVISION,
        payload=PAYLOAD_BYTES,
    )

    with pytest.raises(Refusal) as caught:
        file_deliverable(conn, case_id=case_id, actor_id=signer, revision_id=REVISION)

    assert caught.value.code is RefusalCode.APPROVER_NOT_INDEPENDENT


def test_filing_refuses_the_freeze_actor_too(
    signed: tuple[StoreConnection, UUID, UUID],
) -> None:
    """Both roles, not just the signer. One actor occupying every role records a
    decision nobody independently reviewed."""
    conn, case_id, _signer = signed
    freezer = _approver(conn, case_id)
    freeze(
        conn,
        case_id=case_id,
        actor_id=freezer,
        revision_id=REVISION,
        payload=PAYLOAD_BYTES,
    )

    with pytest.raises(Refusal) as caught:
        file_deliverable(conn, case_id=case_id, actor_id=freezer, revision_id=REVISION)

    assert caught.value.code is RefusalCode.APPROVER_NOT_INDEPENDENT


def test_a_third_person_can_file_it(
    signed: tuple[StoreConnection, UUID, UUID],
) -> None:
    conn, case_id, signer = signed
    freezer = _approver(conn, case_id)
    filer = _approver(conn, case_id)
    freeze(
        conn,
        case_id=case_id,
        actor_id=freezer,
        revision_id=REVISION,
        payload=PAYLOAD_BYTES,
    )

    receipt = file_deliverable(
        conn, case_id=case_id, actor_id=filer, revision_id=REVISION
    )

    assert {receipt.signed_by, receipt.frozen_by, receipt.filed_by} == {
        signer,
        freezer,
        filer,
    }
    assert receipt.payload_sha256 == _digest(PAYLOAD_BYTES)
    assert receipt.audit_head, "the receipt carries the chain head it was filed at"


def test_a_receipt_names_all_three_roles_and_the_chain_head(
    signed: tuple[StoreConnection, UUID, UUID],
) -> None:
    """A `Receipt` is what a reader gets instead of the store. It has to say who
    signed, who froze, who filed, and where the chain stood -- the last of those
    is how a retained copy detects a chain rewritten afterwards."""
    conn, case_id, signer = signed
    freezer = _approver(conn, case_id)
    filer = _approver(conn, case_id)
    freeze(
        conn,
        case_id=case_id,
        actor_id=freezer,
        revision_id=REVISION,
        payload=PAYLOAD_BYTES,
    )

    receipt = file_deliverable(
        conn, case_id=case_id, actor_id=filer, revision_id=REVISION
    )

    assert isinstance(receipt, Receipt)
    assert receipt.signed_by == signer
    assert receipt.frozen_by == freezer
    assert receipt.filed_by == filer
    assert len(receipt.audit_head) == 64


def test_an_opinion_binds_a_revision_to_the_digest_it_was_signed_on() -> None:
    """`Opinion` carries the digest, not just the revision id. Signing "the
    current draft" would bind whatever the draft became."""
    opinion = Opinion(
        revision_id=REVISION, payload_sha256=_digest(PAYLOAD_BYTES), signed_by=uuid4()
    )

    assert opinion.payload_sha256 == _digest(PAYLOAD_BYTES)
    assert opinion.payload_sha256 != _digest(PAYLOAD_BYTES + b" amended")


def test_audit_package_verifies_with_stdlib_alone(
    signed: tuple[StoreConnection, UUID, UUID], tmp_path: Path
) -> None:
    """A named exit test.

    The archive is checked by re-deriving everything from what it holds: the
    payload's digest against the receipt, the export against a fresh render, and
    three distinct actors. Nothing consults the store it came from -- which is
    the one place a package never needs verifying.
    """
    conn, case_id, _signer = signed
    freezer = _approver(conn, case_id)
    filer = _approver(conn, case_id)
    freeze(
        conn,
        case_id=case_id,
        actor_id=freezer,
        revision_id=REVISION,
        payload=PAYLOAD_BYTES,
    )
    receipt = file_deliverable(
        conn, case_id=case_id, actor_id=filer, revision_id=REVISION
    )

    archive = build_package(PAYLOAD_BYTES, receipt_bytes(receipt), render(PAYLOAD_DATA))
    conn.close()

    verification = verify_package(archive)

    assert verification.verified is True, verification.reason


def test_a_package_whose_export_was_edited_does_not_verify(
    signed: tuple[StoreConnection, UUID, UUID],
) -> None:
    """The re-render is the check. An export edited after filing no longer comes
    from the payload beside it."""
    conn, case_id, _signer = signed
    freezer = _approver(conn, case_id)
    filer = _approver(conn, case_id)
    freeze(
        conn,
        case_id=case_id,
        actor_id=freezer,
        revision_id=REVISION,
        payload=PAYLOAD_BYTES,
    )
    receipt = file_deliverable(
        conn, case_id=case_id, actor_id=filer, revision_id=REVISION
    )
    edited = render(PAYLOAD_DATA).replace(b"1,240.0m", b"9,999.9m")

    verification = verify_package(
        build_package(PAYLOAD_BYTES, receipt_bytes(receipt), edited)
    )

    assert verification.verified is False
    assert verification.reason is not None
    assert "re-render" in verification.reason


def test_a_package_whose_payload_was_edited_does_not_verify(
    signed: tuple[StoreConnection, UUID, UUID],
) -> None:
    conn, case_id, _signer = signed
    freezer = _approver(conn, case_id)
    filer = _approver(conn, case_id)
    freeze(
        conn,
        case_id=case_id,
        actor_id=freezer,
        revision_id=REVISION,
        payload=PAYLOAD_BYTES,
    )
    receipt = file_deliverable(
        conn, case_id=case_id, actor_id=filer, revision_id=REVISION
    )

    verification = verify_package(
        build_package(
            PAYLOAD_BYTES + b" ", receipt_bytes(receipt), render(PAYLOAD_DATA)
        )
    )

    assert verification.verified is False
    assert "hash" in str(verification.reason)


def test_a_package_is_the_same_bytes_for_the_same_inputs() -> None:
    """A package whose bytes moved with the clock could not be compared against
    a retained copy, which is what detecting a rewrite depends on."""
    first = build_package(PAYLOAD_BYTES, b"{}", b"<html></html>")
    second = build_package(PAYLOAD_BYTES, b"{}", b"<html></html>")

    assert first == second


def test_a_package_holds_the_three_files_a_reader_needs() -> None:
    import zipfile
    from io import BytesIO

    archive = build_package(PAYLOAD_BYTES, b"{}", b"<html></html>")

    with zipfile.ZipFile(BytesIO(archive)) as opened:
        assert set(opened.namelist()) == {PAYLOAD, "receipt.json", EXPORT}


def test_a_filed_package_is_never_overwritten(tmp_path: Path) -> None:
    """§7: never overwriting. A filed deliverable that could be replaced in
    place is not one anybody can rely on having read."""
    path = tmp_path / "package.zip"
    write_package(path, build_package(PAYLOAD_BYTES, b"{}", b"<html></html>"))

    with pytest.raises(FileExistsError):
        write_package(path, build_package(PAYLOAD_BYTES, b"{}", b"<html></html>"))
