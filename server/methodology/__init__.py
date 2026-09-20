"""The methodology boundary: the bundle, the registry, the calculator seam."""

from __future__ import annotations

from server.methodology.adapter_identity import (
    CANONICAL_ADAPTER_LABEL as CANONICAL_ADAPTER_LABEL,
)
from server.methodology.adapter_identity import (
    verify_canonical_adapter_pin as verify_canonical_adapter_pin,
)
from server.methodology.adapter_pin import CANONICAL_ADAPTER_SHA256

# The one host adapter every run pins (`docs/DECISIONS.md` §42.1, retired
# dispatch). A route with a module outside `handoff.ADAPTER_MODULES` pins it
# too and is refused at execution and acceptance (§42.2).
# The stored adapter field is the full content pin; the readable label remains
# available for release evidence and is never an acceptance identity.
CANONICAL_ADAPTER_VERSION = CANONICAL_ADAPTER_SHA256
