"""The governed commands under `/api/v1/cases` (Task 4.2).

One module per command family, each owning its `APIRouter` and `IO_BUDGET`:
`cases` (create case, admission), `runs` (route, input, preview, approval) and
`execution` (start, retry, cancel). `_request` holds the dependencies they
share; `server/api/app.py` includes the three routers.
"""
