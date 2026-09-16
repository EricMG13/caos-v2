"""The shared request dependencies every section read and `app.py` itself
declare on their routes: who is asking, the request's store connection, the
blob store, and the process's vendored methodology bundle.

Moved out of `server/api/app.py` (Task 4.1c) so the section reads under
`server/api/reads/` can depend on these functions directly instead of each
declaring its own lazily-imported wrapper. `app.py` used to be imported by
every section module (to register its router), which made importing `app.py`'s
dependencies from a section module a cycle -- whichever module loaded first
would find the other half-built. This module has no such edge: nothing here
imports `server.api.app`, so both `app.py` and `server/api/reads/*.py` import
it directly, and a test overriding one of these functions reaches every route
that declares it, section reads included.

`app.py` imports and re-exports every name here (`from server.api.deps import
store_connection as store_connection`, and so on) so `server.api.app.<name>` is
still the same function object -- an existing override of `app_module.X`
overrides this module's `X` too, because they are one object under two names.
`app.py`'s `_lifespan` keeps using `_database_url` the same way.

No round trip of its own: `IO_BUDGET = 0`, the same declaration
`server/api/identity.py` makes for the same reason.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import cache
from os import environ
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from psycopg import OperationalError

from server.api.identity import Actor, actor_from_headers
from server.blobs import BlobStore
from server.methodology.bundle import Bundle
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection, connect

IO_BUDGET = 0

DATABASE_URL = "CAOS_DATABASE_URL"
BLOB_ROOT = "CAOS_BLOB_ROOT"
# The vendored methodology bundle the image ships (`Dockerfile` copies it).
VENDORED_BUNDLE = Path(__file__).resolve().parents[2] / "vendor" / "deploy-v"


def _database_url() -> str:
    url = environ.get(DATABASE_URL)
    if not url:
        raise Refusal(RefusalCode.STORE_NOT_CONFIGURED)
    return url


def store_connection() -> Iterator[StoreConnection]:
    """One connection per request, from the environment.

    A store that does not answer is refused like any other store fault. The
    refusal is raised outside the `except`, so psycopg's message -- the host,
    the port and the role -- is neither chained behind it nor logged with it.
    """
    conn: StoreConnection | None
    try:
        conn = connect(_database_url())
    except OperationalError:
        conn = None
    if conn is None:
        raise Refusal(RefusalCode.STORE_UNAVAILABLE)
    with conn:
        yield conn


def blob_store() -> BlobStore:
    root = environ.get(BLOB_ROOT)
    if not root:
        raise Refusal(RefusalCode.STORE_NOT_CONFIGURED)
    return BlobStore(Path(root))


def actor_from_request(request: Request) -> Actor:
    """Who is asking. A dependency rather than a line in a route body.

    FastAPI builds a route's dependency list in the order its parameters declare
    them and solves it sequentially, so declaring this one before `Store` is
    what keeps identity ahead of the connection. Two things rest on that. An
    anonymous request is refused without opening one -- a connection is per
    request and unpooled, and asking in a loop costs the asker nothing. And the
    answer to a stranger does not depend on the store being reachable: a process
    that has lost its database still says "I do not know who you are", which is
    the only one of the two answers that is about the caller.

    It closes the anonymous half and not the whole of it. A request asserting
    any well-formed subject still reaches the connection, because whether that
    subject is real is the edge's question rather than this process's
    (`server/api/identity.py`).
    """
    return actor_from_headers(request.headers)


def methodology_bundle() -> Bundle:
    """The process's one bundle, which canonical records are verified under.

    Built once: its manifest snapshot is taken at construction and every use
    re-verifies the bytes (invariant 4), so a moved manifest refuses rather than
    being adopted.
    """
    return _vendored_bundle()


@cache
def _vendored_bundle() -> Bundle:
    return Bundle(VENDORED_BUNDLE)


Caller = Annotated[Actor, Depends(actor_from_request)]
Store = Annotated[StoreConnection, Depends(store_connection)]
Blobs = Annotated[BlobStore, Depends(blob_store)]
Methodology = Annotated[Bundle, Depends(methodology_bundle)]
