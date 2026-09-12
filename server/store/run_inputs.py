"""Complete historical input pins. Storage alone grants no execution authority."""

import json
import math
import re
from dataclasses import asdict, dataclass, replace
from uuid import UUID

import psycopg

from server.boundary_text import BoundaryText
from server.engine.route import route_digest
from server.evidence.ingest import _digest
from server.methodology import executor
from server.methodology.bundle import Bundle
from server.refusals import Refusal, RefusalCode
from server.store import RunStatus, StoreConnection, rollback_or_close
from server.store.events import RunEvent, append, lock_run
from server.store.routes import resolved_route
from server.store.source_sets import load_source_set


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
    fields = asdict(pin)
    del fields["run_id"], fields["input_fingerprint"]
    fields.update(format_version=1, case_id=str(pin.case_id))
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
        if _fingerprint(pin) != pin.input_fingerprint:
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    except (TypeError, ValueError, AttributeError, RecursionError):
        raise Refusal(RefusalCode.RUN_INPUT_INVALID) from None


def load_run_input(conn: StoreConnection, run_id: UUID) -> RunInput | None:
    """Verify historical shape/content; never adopt today's bundle or adapter.

    This read retains the caller's transaction, including on database failure.
    """
    try:
        row = conn.execute(
            "SELECT run_id, case_id, source_version, source_fingerprint, route_digest,"
            " build_id, manifest_sha256, adapter_version, research_json,"
            " input_fingerprint, format_version FROM run_inputs WHERE run_id = %s",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        pin = RunInput(*row[:-1])
        _validate(pin)
        owner = conn.execute(
            "SELECT case_id FROM runs WHERE run_id = %s", (run_id,)
        ).fetchone()
        source = load_source_set(conn, pin.case_id, pin.source_version)
        route = resolved_route(conn, run_id)
        if (
            row[-1] != 1
            or owner != (pin.case_id,)
            or source is None
            or source.fingerprint != pin.source_fingerprint
            or route is None
            or route_digest(route) != pin.route_digest
        ):
            raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    except psycopg.Error:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    return pin


def pin_run_input(
    conn: StoreConnection,
    run_id: UUID,
    source_version: int,
    bundle: Bundle,
    research: object = None,
) -> RunInput:
    """Own one case-first/run-locked row/event transaction; setup commits separately."""
    if conn.autocommit:
        raise Refusal(RefusalCode.STORE_NOT_TRANSACTIONAL)
    try:
        candidate = _pin(conn, run_id, source_version, bundle, research)
        conn.commit()
    except psycopg.Error:
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    except BaseException:
        rollback_or_close(conn)
        raise
    return candidate


def _pin(
    conn: StoreConnection,
    run_id: UUID,
    source_version: int,
    bundle: Bundle,
    research: object,
) -> RunInput:
    if type(source_version) is not int or not 0 < source_version < 2**63:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    raw = _research(research)
    status = lock_run(conn, run_id)
    owner = conn.execute(
        "SELECT case_id FROM runs WHERE run_id = %s", (run_id,)
    ).fetchone()
    if owner is None:
        raise Refusal(RefusalCode.RUN_NOT_FOUND)
    source = load_source_set(conn, owner[0], source_version)
    route = resolved_route(conn, run_id)
    if source is None or route is None:
        raise Refusal(RefusalCode.RUN_INPUT_INVALID)
    candidate = RunInput(
        run_id,
        owner[0],
        source.version,
        source.fingerprint,
        route_digest(route),
        bundle.build_id,
        bundle.manifest_sha256,
        executor.CLAIMS_ADAPTER_VERSION,
        raw,
        "",
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
            " adapter_version, research_json, input_fingerprint)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            tuple(asdict(candidate).values()),
        )
        append(conn, run_id, RunEvent.INPUT_PINNED)
    return candidate
