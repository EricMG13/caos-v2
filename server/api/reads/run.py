"""The Run section read. No route yet: slice 4.1d adds it here."""

from __future__ import annotations

from fastapi import APIRouter

# No round trip while the router serves nothing; the route brings its measured
# budget with it.
IO_BUDGET = 0

router = APIRouter()
