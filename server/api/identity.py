"""Who is asking. Derived from what the edge asserted, never from what the client
claimed about itself.

`SYSTEM_SPEC.md` §8, and `docs/DECISIONS.md` §22. The host sits behind a proxy
that authenticates the caller and forwards the subject and its groups. Those two
headers are the whole input, and neither is settable by a browser that reached
the proxy: a proxy that forwarded a client-supplied `x-forwarded-groups` would be
misconfigured in a way no code here can detect, which is why the group list is
the *only* thing this reads in production and the role header is off by default.

Two things this deliberately does not do.

*It does not carry per-case standing.* A `GlobalRole` says what kind of account
this is, not what it may do to a particular case; that is `case_members`, checked
at commit time inside the store call. An actor arriving at a route already
holding case authority would be authority checked at the request, which §8 says
is not the place.

*It does not carry persona.* Which section a user is reading composes a view and
grants nothing, so it is not on the actor and cannot be mistaken for authority.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from server.refusals import Refusal, RefusalCode

# No round trips: the actor comes out of two headers and a closed group table,
# and nothing here touches the store. Declared rather than exempted, because
# `server/api/` is where every module is on a request path and "it does no I/O"
# is a fact worth stating rather than a rule a gate has to infer every time
# (`scripts/io_budget.py`). The day this reads a user row, this number moves.
IO_BUDGET = 0

# The development convenience, and it is opt-in. An environment variable that had
# to be set to *disable* trust is one a deployment forgets, and that failure is
# silent and total: every request would arrive as whatever it said it was.
TRUST_SWITCH = "CAOS_TRUST_ROLE_HEADER"
TRUSTED = "1"

SUBJECT_HEADER = "x-caos-user"
GROUPS_HEADER = "x-forwarded-groups"
ROLE_HEADER = "x-caos-role"


class GlobalRole(StrEnum):
    """What kind of account this is. Not what it may do to a given case."""

    READER = "READER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


# Written out rather than derived from declaration order, so that adding a role
# in the middle of the enum cannot silently reorder authority.
_RANK = {GlobalRole.READER: 0, GlobalRole.ANALYST: 1, GlobalRole.ADMIN: 2}

# The identity provider's groups, mapped to this system's words. A group absent
# from here grants nothing -- an unknown group is not an unknown *role*, it is a
# group about some other system.
_GROUPS = {
    "caos-readers": GlobalRole.READER,
    "caos-analysts": GlobalRole.ANALYST,
    "caos-admins": GlobalRole.ADMIN,
}


@dataclass(frozen=True, slots=True)
class Actor:
    """The authenticated subject and its global role. Nothing else."""

    user_id: UUID
    role: GlobalRole


def actor_from_headers(headers: object) -> Actor:
    """The actor this request is from, or `NOT_AUTHENTICATED`.

    The switch is read here rather than at import, so a process started against a
    wrong environment starts behaving correctly the moment it is corrected --
    rather than for as long as it happens to stay up.
    """
    get = getattr(headers, "get", None)
    if get is None:
        raise Refusal(RefusalCode.NOT_AUTHENTICATED)

    subject = get(SUBJECT_HEADER)
    if not isinstance(subject, str):
        raise Refusal(RefusalCode.NOT_AUTHENTICATED)
    try:
        user_id = UUID(subject)
    except ValueError:
        # `from None`: the ValueError's message is the header the client sent.
        raise Refusal(RefusalCode.NOT_AUTHENTICATED) from None

    if os.environ.get(TRUST_SWITCH) == TRUSTED:
        return Actor(user_id=user_id, role=_claimed(get(ROLE_HEADER)))
    return Actor(user_id=user_id, role=_from_groups(get(GROUPS_HEADER)))


def _from_groups(groups: object) -> GlobalRole:
    """The greatest role any asserted group carries, READER if none does."""
    if not isinstance(groups, str):
        return GlobalRole.READER
    held = [
        _GROUPS[name]
        for name in (part.strip() for part in groups.split(","))
        if name in _GROUPS
    ]
    return max(held, key=_RANK.__getitem__, default=GlobalRole.READER)


def _claimed(role: object) -> GlobalRole:
    """The role the client asked for, when the switch says to believe it.

    Still a closed set: falling through to whatever string arrived would be
    trusting the header twice, once for the value and once for the vocabulary.
    """
    if not isinstance(role, str):
        return GlobalRole.READER
    try:
        return GlobalRole(role.strip().upper())
    except ValueError:
        return GlobalRole.READER
