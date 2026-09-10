"""The actor matrix: what a client may assert about itself.

`docs/REBUILD_PLAN.md`'s standing rules: "the first phase exposing an HTTP route
ships identity derivation and the actor matrix
(`test_production_never_trusts_role_header`,
`test_unauthorised_case_is_private_404`)". This is that phase; the second of the
pair lives with the route it is about, in `tests/test_api_routes.py`.

Both are the same instinct and the same refusal to indulge it. A role header is
convenient in development and is a client asserting its own authority; a 403 is
informative and tells a stranger the case exists. Each is the comfortable answer,
and each is refused.

The switch is off unless explicitly on. An environment variable that had to be
set to *disable* trust is one a misconfigured deployment forgets, and that
failure is silent and total.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from server.api.identity import TRUST_SWITCH, GlobalRole, actor_from_headers
from server.refusals import Refusal, RefusalCode

USER = uuid4()


def _headers(**extra: str) -> dict[str, str]:
    return {"x-caos-user": str(USER), **extra}


def test_production_never_trusts_role_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A named test. The client says it is an administrator; production does not
    care what the client says.

    The role is derived from the groups the proxy asserts and from nothing the
    caller can set. A role header that escalated would make every other authority
    check in this system a formality.
    """
    monkeypatch.delenv(TRUST_SWITCH, raising=False)

    actor = actor_from_headers(
        _headers(**{"x-caos-role": "ADMIN", "x-forwarded-groups": "caos-readers"})
    )

    assert actor.role is GlobalRole.READER, "the group decided, not the header"


def test_the_role_header_is_trusted_only_when_explicitly_switched_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Development's convenience, and it has to be asked for by name."""
    monkeypatch.setenv(TRUST_SWITCH, "1")

    actor = actor_from_headers(_headers(**{"x-caos-role": "ADMIN"}))

    assert actor.role is GlobalRole.ADMIN


@pytest.mark.parametrize("value", ["", "0", "true", "yes", "TRUE", "on"])
def test_anything_but_one_leaves_the_switch_off(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Off unless exactly `1`. A switch that also accepted "true", "yes" and "on"
    would eventually accept something a deployment set for another purpose."""
    monkeypatch.setenv(TRUST_SWITCH, value)

    actor = actor_from_headers(
        _headers(**{"x-caos-role": "ADMIN", "x-forwarded-groups": "caos-readers"})
    )

    assert actor.role is GlobalRole.READER


def test_an_unknown_role_name_under_trust_is_still_the_lowest_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even switched on, the header names a role from the closed set or names
    nothing. A parse that fell through to "whatever the client typed" is the
    header being trusted twice over."""
    monkeypatch.setenv(TRUST_SWITCH, "1")

    actor = actor_from_headers(_headers(**{"x-caos-role": "SUPERUSER"}))

    assert actor.role is GlobalRole.READER


def test_no_groups_and_no_trust_is_the_lowest_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed. An identity the proxy said nothing about is not an
    administrator by default."""
    monkeypatch.delenv(TRUST_SWITCH, raising=False)

    actor = actor_from_headers(_headers())

    assert actor.role is GlobalRole.READER


def test_a_request_with_no_user_at_all_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(TRUST_SWITCH, raising=False)

    with pytest.raises(Refusal) as caught:
        actor_from_headers({"x-forwarded-groups": "caos-admins"})

    assert caught.value.code is RefusalCode.NOT_AUTHENTICATED


def test_a_user_that_is_not_an_identifier_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The subject is a uuid the host issued. Anything else is a caller inventing
    an identity, which is the thing the role header would have done."""
    monkeypatch.delenv(TRUST_SWITCH, raising=False)

    with pytest.raises(Refusal) as caught:
        actor_from_headers({"x-caos-user": "../../etc/passwd"})

    assert caught.value.code is RefusalCode.NOT_AUTHENTICATED


def test_something_that_is_not_even_a_headers_object_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A caller of this function, not a client -- but the same refusal either
    way. Something with no `.get` at all is not a lesser kind of unauthenticated,
    it is the same one."""
    monkeypatch.delenv(TRUST_SWITCH, raising=False)

    with pytest.raises(Refusal) as caught:
        actor_from_headers(None)

    assert caught.value.code is RefusalCode.NOT_AUTHENTICATED


def test_trust_switched_on_with_no_role_header_at_all_is_the_lowest_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even switched on, a request that asserted no role at all gets the same
    answer as one asserting a role outside the closed set: the floor."""
    monkeypatch.setenv(TRUST_SWITCH, "1")

    actor = actor_from_headers(_headers())

    assert actor.role is GlobalRole.READER


def test_the_refusal_carries_no_part_of_what_was_sent() -> None:
    """§ refusals: the code travels, the offending text never does. An identity
    header is exactly the string that must not reach a log line."""
    with pytest.raises(Refusal) as caught:
        actor_from_headers({"x-caos-user": "mallory@example.test"})

    assert "mallory" not in str(caught.value)
    assert "mallory" not in repr(caught.value)


@pytest.mark.parametrize(
    ("groups", "expected"),
    [
        ("caos-admins", GlobalRole.ADMIN),
        ("caos-analysts", GlobalRole.ANALYST),
        ("caos-readers", GlobalRole.READER),
        ("something-else", GlobalRole.READER),
        ("caos-readers,caos-admins", GlobalRole.ADMIN),
        ("caos-analysts,caos-readers", GlobalRole.ANALYST),
        (" caos-admins , caos-readers ", GlobalRole.ADMIN),
    ],
)
def test_the_highest_group_wins(
    monkeypatch: pytest.MonkeyPatch, groups: str, expected: GlobalRole
) -> None:
    """Someone in two groups holds the greater of them, and a group this system
    does not know grants nothing."""
    monkeypatch.delenv(TRUST_SWITCH, raising=False)

    actor = actor_from_headers(_headers(**{"x-forwarded-groups": groups}))

    assert actor.role is expected


def test_an_actor_is_a_subject_and_a_role_and_nothing_else() -> None:
    """Persona is not authority (`SYSTEM_SPEC.md` §8). Which section a user is
    looking at composes a view and grants nothing, so it is not on the actor --
    and per-case standing lives in `case_members`, not in a header."""
    from server.api.identity import Actor

    assert set(Actor.__annotations__) == {"user_id", "role"}


def test_the_switch_is_read_at_the_request_not_at_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A process started in one mode must not keep behaving that way after the
    environment is corrected."""
    monkeypatch.delenv(TRUST_SWITCH, raising=False)
    before = actor_from_headers(_headers(**{"x-caos-role": "ADMIN"}))

    monkeypatch.setenv(TRUST_SWITCH, "1")
    after = actor_from_headers(_headers(**{"x-caos-role": "ADMIN"}))

    assert (before.role, after.role) == (GlobalRole.READER, GlobalRole.ADMIN)
