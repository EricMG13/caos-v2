"""The one canonical JSON serialisation the digesting sites share.

Seven places in this tree turned a value into bytes and hashed it, each writing
the same four `json.dumps` flags out longhand. They are the same four because
the result is a stored digest -- an audit link, a signed payload, a route pin, a
command receipt -- and two sites that disagree by a flag produce two digests for
one value. Writing the flags once is what stops the next site drifting.

Every flag earns its place. `sort_keys` and `separators` make one value into one
string. `ensure_ascii=False` keeps a European issuer's name as itself rather
than as escapes, which is only safe because the string is encoded UTF-8 here and
nowhere else. `allow_nan=False` refuses `NaN` and `Infinity`, which are not JSON
and would be a digest over bytes no other reader could parse.

The sites that escape non-ASCII (`server/store/audit.py`,
`server/deliverable/filing.py`, `server/qualification/matrix.py` and
`server/qualification/store.py`) are deliberately not here: `ensure_ascii` moves
the bytes for any non-ASCII input, so folding them in would invalidate every
digest already stored.

Two more sites spell the same four flags out and are still not callers.
`server/deliverable/canonical.py` writes the payload that is signed, and
`server/calculators/cash_flow.py` is byte-pinned by
`methodology/skills/HOST_INTEGRITY_v1.json` -- an edit of any kind there refuses
`AUTHORITY_BYTES_MISMATCH`, so its longhand stays exactly as it is.
"""

from __future__ import annotations

import json
from hashlib import sha256


def canonical_json(value: object) -> str:
    """One value, one string. Raises `ValueError` on a non-finite number."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_digest(value: object) -> str:
    """The SHA-256 of `canonical_json(value)` encoded UTF-8."""
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()
