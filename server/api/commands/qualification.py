"""A reviewer signs a qualification verdict (F17's producer half; §65).

The one write in this system that is not a case's. Qualification spans a set
of cases, so there is no case to lock, no `case_members` standing to hold and
no governed unit through `run_command`: the write is `record_verdict`, in one
transaction, and the store's own bindings are what refuse it -- provider, set
digest and build must equal the recorded evidence, and the snapshot must be
`complete`. Nothing here repeats those checks; it maps them to the wire.

Three things the route keeps apart.

*The document is the reviewer's.* The body is the six bindings `read_verdict`
declares and nothing else, closed at the wire and read once, by that reader,
against the store's clock. The host originates none of it.

*The identity is the host's.* `reviewer_id` is `Actor.user_id`, derived at the
edge from the subject the proxy asserted. A body naming one is an undeclared
field and is refused before a connection opens.

*The floor is the top global rank.* A verdict turns every case's qualification
label to one person's word, which makes it the first authority here that is
account-wide rather than case-scoped -- the case `CLAUDE.md`'s ledger reserved
for the global role. Everywhere else an ANALYST's write needs case standing on
top of the role; with no case to stand on, the only separation available is
rank, and `_RANK` says which is highest. A caller below it is answered as a
stranger to a case is: not found, disclosing nothing about which evidence the
store holds.
"""

from __future__ import annotations

from re import fullmatch
from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from server.api.commands._request import json_body
from server.api.deps import Caller, Store
from server.api.identity import Actor, GlobalRole, at_least
from server.api.wire import SignVerdict, VerdictRecorded
from server.qualification.store import evidence_at, record_verdict
from server.qualification.verdict import Verdict, read_verdict
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, rollback_or_close

# The store's clock, the exact evidence lookup, then `record_verdict`: the
# `complete` read, `record_evidence`'s three statements, and the insert.
# Measured in `tests/test_qualification_sign.py`.
SIGN_IO = 1 + 1 + 5
IO_BUDGET = SIGN_IO

# Who may sign. Compared by rank (`at_least`), not by identity.
SIGNS = GlobalRole.ADMIN

router = APIRouter()


def require_reviewer(actor: Caller) -> Actor:
    """The actor, if its global role reaches the signing floor.

    Declared ahead of the body and the store, so a caller below the floor is
    answered before either is read -- and answered as unknown evidence is.
    """
    if not at_least(actor.role, SIGNS):
        raise Refusal(RefusalCode.QUALIFICATION_EVIDENCE_NOT_FOUND)
    return actor


def evidence_path(evidence_sha256: str) -> str:
    """The path's evidence digest, or the same private answer a stranger gets.

    Typed `str` and checked here rather than validated by FastAPI, so a
    malformed digest is the declared refusal body and not a 422 that quotes
    the path -- and, as a dependency before the store, opens no connection.
    """
    if fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None:
        raise Refusal(RefusalCode.QUALIFICATION_EVIDENCE_NOT_FOUND)
    return evidence_sha256


Reviewer = Annotated[Actor, Depends(require_reviewer)]
EvidencePath = Annotated[str, Depends(evidence_path)]


def _signed(
    conn: StoreConnection,
    *,
    evidence_sha256: str,
    reviewer_id: UUID,
    document: dict[str, Any],
) -> Verdict:
    """Every statement the request sends, so the route can type what fails.

    Its own function because each of these is the store answering: with them
    inline the route could not tell a driver fault from a refusal without
    catching `psycopg.Error` around raises of its own.
    """
    row = conn.execute("SELECT now()").fetchone()
    if row is None:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE)
    [now] = row
    verdict = read_verdict(document, now=now)
    evidence = evidence_at(conn, evidence_sha256=evidence_sha256)
    if evidence is None:
        raise Refusal(RefusalCode.QUALIFICATION_EVIDENCE_NOT_FOUND)
    record_verdict(conn, evidence=evidence, reviewer_id=reviewer_id, verdict=verdict)
    conn.commit()
    return verdict


@router.post("/api/v1/qualification/{evidence_sha256}/verdict")
def sign_verdict(
    reviewer: Reviewer,
    evidence_sha256: EvidencePath,
    body: Annotated[SignVerdict, Depends(json_body(SignVerdict))],
    conn: Store,
) -> Response:
    """Record the reviewer's verdict over one exact evidence identity.

    Order: the reviewer's document is read first, against the store's clock,
    because a document that is not a verdict is refused whatever it names;
    then the evidence it names must be held; then the store binds the two or
    refuses. A refusal after the first write rolls the transaction back, so a
    verdict that did not bind leaves no evidence row behind it either.
    """
    try:
        verdict = _signed(
            conn,
            evidence_sha256=evidence_sha256,
            reviewer_id=reviewer.user_id,
            document=body.model_dump(mode="json"),
        )
    except Refusal:
        rollback_or_close(conn)
        raise
    except psycopg.Error:
        # The clock, the lookup and the writes are all the store's to fail.
        # Outside this handler a driver error left the typed boundary as an
        # untyped 500 carrying the driver's own message into whatever logs it.
        rollback_or_close(conn)
        raise Refusal(RefusalCode.STORE_UNAVAILABLE) from None
    receipt = VerdictRecorded(
        evidence_sha256=evidence_sha256,
        reviewer_id=reviewer.user_id,
        decided_at=verdict.decided_at,
        expires_at=verdict.expires_at,
    )
    return JSONResponse(status_code=201, content=receipt.model_dump(mode="json"))
