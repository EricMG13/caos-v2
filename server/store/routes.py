"""Pinning a resolved route. The one place resolution meets the store.

`server/engine/route.py` is pure by design -- no I/O, no clock -- because
invariant 10 rests on a replay from the same pins taking the same path, and a
resolver that read anything mutable could not promise that. So the pin lives
here: the row, the digest, and the event, in one transaction.

Pinning is once per run. A second pin carrying the same digest is a replay of the
gate and is accepted silently; one carrying a different digest is refused, because
execution reads only the pin and moving it underneath a running route rewrites
what that run is.
"""

from __future__ import annotations

from json import dumps, loads
from uuid import UUID

from server.engine.route import (
    Edge,
    EdgeType,
    ResolvedRoute,
    RouteNode,
    route_digest,
)
from server.refusals import Refusal, RefusalCode
from server.store import StoreConnection
from server.store.events import RunEvent, append, lock_run


def pin_route(conn: StoreConnection, run_id: UUID, resolved: ResolvedRoute) -> str:
    """Pin `resolved` to the run and return its digest."""
    digest = route_digest(resolved)
    lock_run(conn, run_id)

    row = conn.execute(
        "SELECT route_digest FROM run_routes WHERE run_id = %s", (run_id,)
    ).fetchone()
    if row is not None:
        if str(row[0]) != digest:
            raise Refusal(RefusalCode.ROUTE_ALREADY_PINNED)
        conn.commit()  # the same gate, replayed; the lock is not worth holding
        return digest

    conn.execute(
        "INSERT INTO run_routes (run_id, profile_id, selection_id, route_digest,"
        " resolved) VALUES (%s, %s, %s, %s, %s)",
        (
            run_id,
            resolved.profile_id,
            resolved.selection_id,
            digest,
            _canonical(resolved),
        ),
    )
    append(conn, run_id, RunEvent.ROUTE_PINNED)
    conn.commit()
    return digest


def pinned_route(conn: StoreConnection, run_id: UUID) -> str | None:
    """The digest pinned to this run, or None. What execution reads."""
    row = conn.execute(
        "SELECT route_digest FROM run_routes WHERE run_id = %s", (run_id,)
    ).fetchone()
    return None if row is None else str(row[0])


def resolved_route(conn: StoreConnection, run_id: UUID) -> ResolvedRoute | None:
    """The pinned route itself, rebuilt from the row, or None before the gate.

    Read back rather than re-resolved. A surface that resolved the catalog again
    to draw a running route would draw whatever the catalog says today, which is
    the one thing pinning exists to prevent.
    """
    row = conn.execute(
        "SELECT resolved FROM run_routes WHERE run_id = %s", (run_id,)
    ).fetchone()
    if row is None:
        return None
    stored = loads(row[0]) if isinstance(row[0], str | bytes) else row[0]
    return ResolvedRoute(
        profile_id=str(stored["profile_id"]),
        selection_id=str(stored["selection_id"]),
        nodes=tuple(
            RouteNode(
                route_node_id=str(node["route_node_id"]),
                module_id=str(node["module_id"]),
                stage=int(node["stage"]),
            )
            for node in stored["nodes"]
        ),
        edges=tuple(
            Edge(
                source=str(edge["source"]),
                target=str(edge["target"]),
                type=EdgeType(edge["type"]),
            )
            for edge in stored["edges"]
        ),
        predicates=tuple((str(pair[0]), str(pair[1])) for pair in stored["predicates"]),
    )


def _canonical(resolved: ResolvedRoute) -> str:
    """The route as stored: the same shape `route_digest` hashes, so what a
    replay reads back and what the digest promised cannot disagree."""
    return dumps(
        {
            "profile_id": resolved.profile_id,
            "selection_id": resolved.selection_id,
            "nodes": [
                {
                    "route_node_id": node.route_node_id,
                    "module_id": node.module_id,
                    "stage": node.stage,
                }
                for node in resolved.nodes
            ],
            "edges": [
                {"source": edge.source, "target": edge.target, "type": edge.type.value}
                for edge in resolved.edges
            ],
            "predicates": [list(pair) for pair in resolved.predicates],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
