"""Route selection, subject pin, gate preview and approval.

Empty until its slice adds the routes (Task 4.2 slice 4.2e); `server/api/app.py`
already includes the router, so that slice edits only this module.
"""

from __future__ import annotations

from fastapi import APIRouter

# No route yet, so no round trip; the slice that adds one measures its budget.
IO_BUDGET = 0

router = APIRouter()
