"""Immutable source snapshots; historical membership is not read authority."""

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID

import psycopg

from server.boundary_text import BoundaryText
from server.evidence.extract import ExtractorIdentity
from server.evidence.ingest import _digest
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, rollback_or_close
from server.store.cases import lock_case


@dataclass(frozen=True, slots=True)
class SourceSetMember:
    source_id: UUID
    document_sha256: str
    filename: str
    admitted_at: str
    extractor_identity: str
    output_sha256: str
    extraction_sha256: str


@dataclass(frozen=True, slots=True)
class SourceSet:
    case_id: UUID
    version: int
    fingerprint: str
    members: tuple[SourceSetMember, ...]


def _valid_member(member: SourceSetMember) -> bool:
    identity = json.loads(member.extractor_identity)
    timestamp = datetime.fromisoformat(member.admitted_at)
    return (
        ExtractorIdentity(**identity).canonical() == member.extractor_identity
        and BoundaryText.of(member.filename).value == member.filename
        and timestamp.tzinfo is not None
        and timestamp.astimezone(UTC).isoformat() == member.admitted_at
        and all(
            re.fullmatch("[0-9a-f]{64}", digest)
            for digest in (
                member.document_sha256,
                member.output_sha256,
                member.extraction_sha256,
            )
        )
        and _digest(
            {
                "format_version": 1,
                "document_sha256": member.document_sha256,
                "extractor_identity": identity,
                "output_sha256": member.output_sha256,
            }
        )
        == member.extraction_sha256
    )


def _fingerprint(case_id: UUID, members: tuple[SourceSetMember, ...]) -> str:
    """Validate stored provenance before using it as snapshot authority."""
    try:
        valid = all(_valid_member(member) for member in members)
        digest = _digest(
            {
                "format_version": 1,
                "case_id": str(case_id),
                "members": [
                    {**asdict(member), "source_id": str(member.source_id)}
                    for member in sorted(members, key=lambda m: m.source_id)
                ],
            }
        )
    except (Refusal, TypeError, ValueError, AttributeError, OverflowError):
        raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID) from None
    if not valid or not members or len({m.source_id for m in members}) != len(members):
        raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID)
    return digest


def load_source_set(
    conn: StoreConnection, case_id: UUID, version: int
) -> SourceSet | None:
    """Load exactly one case/version; caller owns the read transaction."""
    header = conn.execute(
        "SELECT fingerprint, member_count FROM source_set_versions"
        " WHERE case_id = %s AND version = %s",
        (case_id, version),
    ).fetchone()
    if header is None:
        return None
    members = tuple(
        SourceSetMember(*row)
        for row in conn.execute(
            "SELECT source_id, document_sha256, filename, admitted_at,"
            " extractor_identity, output_sha256, extraction_sha256"
            " FROM source_set_members"
            " WHERE case_id = %s AND version = %s ORDER BY source_id",
            (case_id, version),
        ).fetchall()
    )
    if len(members) != header[1] or _fingerprint(case_id, members) != header[0]:
        raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID)
    return SourceSet(case_id, version, header[0], members)


def snapshot_source_set(conn: StoreConnection, case_id: UUID) -> SourceSet:
    """Own and finish the transaction, including replay; commit setup first."""
    try:
        result = _snapshot(conn, case_id)
        conn.commit()
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except OverflowError:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.SOURCE_IDENTITY_INVALID) from None
    except BaseException:
        rollback_or_close(conn)
        raise
    return result


def _snapshot(conn: StoreConnection, case_id: UUID) -> SourceSet:
    lock_case(conn, case_id)
    rows = conn.execute(
        "SELECT s.source_id, s.document_sha256, s.filename, s.admitted_at,"
        " e.extractor_identity, e.output_sha256, e.extraction_sha256"
        " FROM live_sources s LEFT JOIN source_extractions e USING (source_id)"
        " WHERE s.case_id = %s ORDER BY s.source_id",
        (case_id,),
    ).fetchall()
    if not rows:
        raise Refusal(RefusalCode.SOURCE_PACK_EMPTY)
    members = tuple(
        SourceSetMember(
            row[0],
            row[1],
            row[2],
            row[3].astimezone(UTC).isoformat(),
            row[4],
            row[5],
            row[6],
        )
        for row in rows
    )
    fingerprint = _fingerprint(case_id, members)
    latest = conn.execute(
        "SELECT version FROM source_set_versions WHERE case_id = %s"
        " ORDER BY version DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    previous = None if latest is None else load_source_set(conn, case_id, latest[0])
    if previous is not None and previous.fingerprint == fingerprint:
        return previous
    version = 1 if previous is None else previous.version + 1
    conn.execute(
        "INSERT INTO source_set_versions VALUES (%s, %s, 1, %s, %s)",
        (case_id, version, fingerprint, len(members)),
    )
    with conn.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO source_set_members"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [(case_id, version, *asdict(member).values()) for member in members],
        )
    return SourceSet(case_id, version, fingerprint, members)


def pinned_live_sources(conn: StoreConnection, run_id: UUID) -> dict[str, UUID]:
    """Document digest to source id: the run's captured members still usable now.

    The one reader of a run's evidence for everything proven after the call --
    the orchestration proof and the canonical deliverable. A captured member
    counts only while it is live and its document and extraction identity are
    still the ones the pin captured (invariant 1: withdrawal is checked at every
    use); a source admitted after the pin is never a member.

    A document captured under several such members resolves to the lowest
    source id when all of them carry one extraction output -- identical tokens,
    so identical rectangles, whichever copy a call cited -- and to none when
    their outputs differ, since a digest cannot say which rectangles it meant.
    Caller owns the read transaction.
    """
    rows = conn.execute(
        "SELECT m.document_sha256, m.source_id, m.output_sha256 FROM run_inputs i"
        " JOIN source_set_members m"
        " ON (m.case_id, m.version) = (i.case_id, i.source_version)"
        " JOIN live_sources s ON (s.case_id, s.source_id) = (m.case_id, m.source_id)"
        " JOIN source_extractions e ON e.source_id = s.source_id"
        " WHERE i.run_id = %s AND (s.document_sha256, e.extractor_identity,"
        " e.output_sha256, e.extraction_sha256) = (m.document_sha256,"
        " m.extractor_identity, m.output_sha256, m.extraction_sha256)"
        " ORDER BY m.source_id",
        (run_id,),
    ).fetchall()
    resolved: dict[str, UUID] = {}
    outputs: dict[str, set[str]] = {}
    for document, source, output in rows:
        resolved.setdefault(str(document), UUID(str(source)))
        outputs.setdefault(str(document), set()).add(str(output))
    return {doc: source for doc, source in resolved.items() if len(outputs[doc]) == 1}
