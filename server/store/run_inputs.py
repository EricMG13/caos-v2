"""Complete historical input pins. Storage alone grants no execution authority."""

import json
import math
import re
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from uuid import UUID

import psycopg

from server import methodology
from server.boundary_text import BoundaryText
from server.engine.route import ResolvedRoute, route_digest
from server.evidence.ingest import _digest
from server.methodology.bundle import Bundle
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection, rollback_or_close
from server.store.events import RunEvent, append, lock_run
from server.store.routes import resolved_route
from server.store.source_sets import SourceSet, load_source_set

# The vendor's `validate_handoff.SUBJECT_KEY_RE`, and 0011's CHECK.
SUBJECT_KEY = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$")
COS_RUN_ID = re.compile(r"^COS-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{32}$")
_SUBJECT_TEXT_BYTES = 1024


@dataclass(frozen=True, slots=True)
class RunSubject:
    """Who and when a run is about. Pinned before approval; never the model's."""

    issuer_id: str
    issuer_name: str
    reporting_period: str
    analysis_date: str


@dataclass(frozen=True, slots=True)
class RunInput:
    run_id: UUID
    case_id: UUID
    source_version: int
    source_fingerprint: str
    route_digest: str
    build_id: str
    manifest_sha256: str
    adapter_version: str
    research_json: str | None
    input_fingerprint: str
    # Format version 2 only: both present, or both absent for version 1.
    subject: RunSubject | None = None
    cos_run_id: str | None = None

    @property
    def format_version(self) -> int:
        return 1 if self.subject is None else 2


def input_fields(pin: RunInput) -> dict[str, object]:
    """The pin as plain data; a version-1 pin keeps its version-1 keys exactly."""
    fields = asdict(pin)
    if pin.format_version == 1:
        del fields["subject"], fields["cos_run_id"]
    return fields


def cos_run_id(run_id: UUID, created_at: datetime) -> str:
    """The vendor run id, from the run's own creation instant converted to UTC."""
    return f"COS-{created_at.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}-{run_id.hex}"


def _subject_text(value: object) -> bool:
    try:
        return (
            type(value) is str
            and value == value.strip()
            and bool(value)
            and "\t" not in value
            and len(value.splitlines()) == 1
            and len(value.encode("utf-8")) <= _SUBJECT_TEXT_BYTES
            and BoundaryText.of(value, limit=_SUBJECT_TEXT_BYTES).value == value
        )
    except Refusal:
        return False


def _subject_valid(subject: RunSubject) -> bool:
    try:
        parsed = date.fromisoformat(subject.analysis_date)
    except (TypeError, ValueError):
        return False
    return (
        type(subject.issuer_id) is str
        and SUBJECT_KEY.fullmatch(subject.issuer_id) is not None
        and len(subject.issuer_id) <= 128
        and _subject_text(subject.issuer_name)
        and _subject_text(subject.reporting_period)
        and parsed.isoformat() == subject.analysis_date
    )


_V1_COLUMNS = (
    "run_id",
    "case_id",
    "source_version",
    "source_fingerprint",
    "route_digest",
    "build_id",
    "manifest_sha256",
    "adapter_version",
    "research_json",
    "input_fingerprint",
)


def _research_value(item: object) -> bool:
    if type(item) is dict:
        return len(item) <= 4096 and all(type(k) is str for k in item)
    if type(item) is list:
        return len(item) <= 4096
    if type(item) is str:
        try:
            return len(item) <= 4096 and BoundaryText.of(item).value == item
        except Refusal:
            return False
    return (
        item is None
        or type(item) is bool
        or (type(item) is int and -(2**63) <= item < 2**63)
        or (type(item) is float and math.isfinite(item))
    )


def _research(value: object) -> str | None:
    """Exact NFC JSON object or absence; bounds are storage policy, not CP_DR schema."""
    if value is None:
        return None
    if type(value) is not dict:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    pending: list[tuple[object, int]] = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 16 or count > 4096 or not _research_value(item):
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)
        if type(item) is dict:
            pending.extend((v, depth + 1) for pair in item.items() for v in pair)
        elif type(item) is list:
            pending.extend((v, depth + 1) for v in item)
    try:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID) from None
    if len(raw.encode("utf-8")) > 65536:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    return raw


def _fingerprint(pin: RunInput) -> str:
    fields = input_fields(pin)
    del fields["run_id"], fields["input_fingerprint"]
    fields.update(format_version=pin.format_version, case_id=str(pin.case_id))
    return _digest(fields)


def _validate(pin: RunInput) -> None:
    try:
        if type(pin.source_version) is not int or not 0 < pin.source_version < 2**63:
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)
        if not all(
            re.fullmatch(r"[0-9a-f]{64}", value)
            for value in (
                pin.source_fingerprint,
                pin.route_digest,
                pin.build_id,
                pin.manifest_sha256,
                pin.input_fingerprint,
            )
        ) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,63}", pin.adapter_version):
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)
        if pin.research_json is not None:
            if len(pin.research_json.encode("utf-8")) > 65536:
                raise Refusal(RefusalCode.RUN_INPUT_INVALID)
            if _research(json.loads(pin.research_json)) != pin.research_json:
                raise Refusal(RefusalCode.RUN_INPUT_INVALID)
        if (pin.subject is None) != (pin.cos_run_id is None) or (
            pin.subject is not None
            and (
                not _subject_valid(pin.subject)
                or COS_RUN_ID.fullmatch(str(pin.cos_run_id)) is None
            )
        ):
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)
        if _fingerprint(pin) != pin.input_fingerprint:
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    except (TypeError, ValueError, AttributeError, RecursionError):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID) from None


def load_run_input(conn: StoreConnection, run_id: UUID) -> RunInput | None:
    """Verify historical shape/content; never adopt today's bundle or adapter.

    This read retains the caller's transaction, including on database failure.
    """
    loaded = _load_run_input(conn, run_id)
    return None if loaded is None else loaded[0]


def _load_run_input(
    conn: StoreConnection, run_id: UUID
) -> tuple[RunInput, ResolvedRoute, SourceSet] | None:
    """One verified component load for historical and execution-authority reads."""
    try:
        row = conn.execute(
            "SELECT run_id, case_id, source_version, source_fingerprint, route_digest,"
            " build_id, manifest_sha256, adapter_version, research_json,"
            " input_fingerprint, issuer_id, issuer_name, reporting_period,"
            " analysis_date, cos_run_id, format_version"
            " FROM run_inputs WHERE run_id = %s",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        subject = None if row[10] is None else RunSubject(*row[10:14])
        pin = RunInput(**dict(zip(_V1_COLUMNS, row[:10], strict=True)))
        pin = replace(pin, subject=subject, cos_run_id=row[14])
        _validate(pin)
        run = conn.execute(
            "SELECT case_id, created_at FROM runs WHERE run_id = %s", (run_id,)
        ).fetchone()
        owner = None if run is None else (run[0],)
        created = None if run is None else run[1]
        source = load_source_set(conn, pin.case_id, pin.source_version)
        route = resolved_route(conn, run_id)
        if (
            row[-1] != pin.format_version
            or owner != (pin.case_id,)
            or (
                pin.cos_run_id is not None
                and (created is None or pin.cos_run_id != cos_run_id(run_id, created))
            )
            or source is None
            or source.fingerprint != pin.source_fingerprint
            or route is None
            or route_digest(route) != pin.route_digest
        ):
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    except psycopg.Error:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    return pin, route, source


def pin_run_input(  # noqa: PLR0913 -- subject is keyword-only
    conn: StoreConnection,
    run_id: UUID,
    source_version: int,
    bundle: Bundle,
    research: object = None,
    *,
    subject: RunSubject | None = None,
) -> RunInput:
    """Own one case-first/run-locked row/event transaction; setup commits separately.

    A `subject` pins format version 2, whose fingerprint and gate preview bind
    the subject and the UTC vendor run id; without one, version 1 is unchanged.
    """
    if conn.autocommit:
        raise Refusal(RefusalCode.STORE_NOT_TRANSACTIONAL)
    try:
        candidate = _pin(conn, run_id, source_version, bundle, research, subject)
        conn.commit()
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except BaseException:
        rollback_or_close(conn)
        raise
    return candidate


def _pin(  # noqa: PLR0913 -- pin_run_input's arguments
    conn: StoreConnection,
    run_id: UUID,
    source_version: int,
    bundle: Bundle,
    research: object,
    subject: RunSubject | None,
) -> RunInput:
    if type(source_version) is not int or not 0 < source_version < 2**63:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    if subject is not None and not _subject_valid(subject):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    raw = _research(research)
    status = lock_run(conn, run_id)
    owner = conn.execute(
        "SELECT case_id, created_at FROM runs WHERE run_id = %s", (run_id,)
    ).fetchone()
    if owner is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    source = load_source_set(conn, owner[0], source_version)
    route = resolved_route(conn, run_id)
    if source is None or route is None:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    adapter = methodology.adapter_for(route)
    if adapter == methodology.CANONICAL_ADAPTER_VERSION and subject is None:
        # A canonical handoff names its subject; there is none to name.
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    candidate = RunInput(
        run_id,
        owner[0],
        source.version,
        source.fingerprint,
        route_digest(route),
        bundle.build_id,
        bundle.manifest_sha256,
        adapter,
        raw,
        "",
        subject,
        None if subject is None else cos_run_id(run_id, owner[1]),
    )
    candidate = replace(candidate, input_fingerprint=_fingerprint(candidate))
    _validate(candidate)
    stored = load_run_input(conn, run_id)
    if stored is not None:
        if stored != candidate:
            raise Refusal(RefusalCode.RUN_INPUT_ALREADY_PINNED)
    else:
        if status is not RunStatus.RUNNING:
            raise Refusal(RefusalCode.RUN_NOT_RUNNING)
        if conn.execute(
            "SELECT 1 FROM run_attempts WHERE run_id = %s LIMIT 1", (run_id,)
        ).fetchone():
            raise Refusal(RefusalCode.RUN_INPUT_TOO_LATE)
        conn.execute(
            "INSERT INTO run_inputs (run_id, case_id, source_version,"
            " source_fingerprint, route_digest, build_id, manifest_sha256,"
            " adapter_version, research_json, input_fingerprint, issuer_id,"
            " issuer_name, reporting_period, analysis_date, cos_run_id,"
            " format_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                *(getattr(candidate, name) for name in _V1_COLUMNS),
                *(
                    (None,) * 4
                    if subject is None
                    else (
                        subject.issuer_id,
                        subject.issuer_name,
                        subject.reporting_period,
                        subject.analysis_date,
                    )
                ),
                candidate.cos_run_id,
                candidate.format_version,
            ),
        )
        append(conn, run_id, RunEvent.INPUT_PINNED)
    return candidate
