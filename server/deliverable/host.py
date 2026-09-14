"""Map the portable renderer's refusal to the host's closed refusal codes."""

from collections.abc import Mapping
from typing import Any

from server.deliverable.render import RenderRefused, render
from server.refusals import Refusal, RefusalCode


def render_payload(payload: Mapping[str, Any]) -> bytes:
    """Render frozen content with the host refusal contract."""
    try:
        return render(payload)
    except RenderRefused as exc:
        code = exc.code
    raise Refusal(RefusalCode(code))
