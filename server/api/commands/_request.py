"""The request half every command shares (Task 4.2 decisions 2, 5 and 6).

A command route declares its dependencies in decision 2's order, and FastAPI
solves them in declaration order:

    actor: Caller, key: Key, standing: <require_case_*>, body: <json_body>, conn

1. Identity -- anonymous is 401 before anything else.
2. Path ids -- a case id that cannot be read is `CASE_NOT_FOUND`.
3. `Idempotency-Key` -- missing or malformed is 400
   `IDEMPOTENCY_KEY_REQUIRED`, before a connection opens or a body is read.
4. Visibility -- no live standing on the case is 404 `CASE_NOT_FOUND`,
   whatever the global role.
5. Global role -- a write needs ANALYST or ADMIN; READER is 403.
6. Floor -- standing below the command's floor is 403 `NOT_AUTHORISED`.
7. Body -- bounded, closed, and any failure 400 `REQUEST_INVALID`, never
   FastAPI's 422 that quotes the input.

Advisory: the governed write rechecks standing under the case lock at commit.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from server.api.deps import Caller, Store
from server.api.identity import Actor, GlobalRole
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.commands import CommandResult
from server.store.members import Standing, satisfies, standing_of

IO_BUDGET = 1  # the caller's standing on the case

IDEMPOTENCY_HEADER = "idempotency-key"
REPLAYED_HEADER = "idempotency-replayed"
MAX_BODY_BYTES = 16_384
_CANONICAL_UUID_CHARS = 36


def idempotency_key(request: Request) -> UUID:
    """The request's `Idempotency-Key`: a UUID in its hyphenated form."""
    value = request.headers.get(IDEMPOTENCY_HEADER)
    if value is None or len(value) != _CANONICAL_UUID_CHARS:
        raise Refusal(RefusalCode.IDEMPOTENCY_KEY_REQUIRED)
    try:
        return UUID(value)
    except ValueError:
        raise Refusal(RefusalCode.IDEMPOTENCY_KEY_REQUIRED) from None


Key = Annotated[UUID, Depends(idempotency_key)]


def json_body[M: BaseModel](
    model: type[M], max_bytes: int = MAX_BODY_BYTES
) -> Callable[[Request], Awaitable[M]]:
    """A dependency reading `model` from a JSON body of at most `max_bytes`.

    The content type must be `application/json`. A declared length over the
    bound is refused before reading, and a stream (chunked or lying about its
    length) is refused the moment it passes the bound. The validation error is
    dropped, so no part of the body reaches the answer.
    """

    async def read(request: Request) -> M:
        media = request.headers.get("content-type", "").split(";")[0].strip()
        declared = request.headers.get("content-length")
        if media.lower() != "application/json" or (
            declared is not None
            and (not declared.isdigit() or int(declared) > max_bytes)
        ):
            raise Refusal(RefusalCode.REQUEST_INVALID)
        raw = bytearray()
        async for part in request.stream():
            raw.extend(part)
            if len(raw) > max_bytes:
                raise Refusal(RefusalCode.REQUEST_INVALID)
        try:
            return model.model_validate_json(bytes(raw))
        except ValidationError:
            raise Refusal(RefusalCode.REQUEST_INVALID) from None

    return read


def case_standing(
    conn: StoreConnection,
    actor: Actor,
    case_id: UUID,
    floor: Standing,
    *,
    write: bool,
) -> Standing:
    """Visibility, then global role (writes only), then the floor."""
    standing = standing_of(conn, case_id=case_id, user_id=actor.user_id)
    if standing is None:
        raise Refusal(RefusalCode.CASE_NOT_FOUND)
    if write and actor.role is GlobalRole.READER:
        raise Refusal(RefusalCode.NOT_AUTHORISED)
    if not satisfies(standing, floor):
        raise Refusal(RefusalCode.NOT_AUTHORISED)
    return standing


def _path_case(request: Request) -> UUID:
    """The path's case id, read here so a malformed one refuses in order."""
    try:
        return UUID(str(request.path_params["case_id"]))
    except (KeyError, ValueError):
        raise Refusal(RefusalCode.CASE_NOT_FOUND) from None


def require_case_reader(request: Request, actor: Caller, conn: Store) -> Standing:
    """Any live standing: reads and previews."""
    return case_standing(conn, actor, _path_case(request), Standing.READER, write=False)


def require_case_writer(request: Request, actor: Caller, conn: Store) -> Standing:
    """WRITER standing and a global role that may write."""
    return case_standing(conn, actor, _path_case(request), Standing.WRITER, write=True)


def require_case_approver(request: Request, actor: Caller, conn: Store) -> Standing:
    """APPROVER standing and a global role that may write."""
    return case_standing(
        conn, actor, _path_case(request), Standing.APPROVER, write=True
    )


def command_response(result: CommandResult, model: type[BaseModel]) -> Response:
    """The receipt, validated against its model whether fresh or replayed."""
    body = model.model_validate(result.receipt).model_dump(mode="json")
    headers = {REPLAYED_HEADER: "true"} if result.replayed else None
    return JSONResponse(status_code=result.status, content=body, headers=headers)
