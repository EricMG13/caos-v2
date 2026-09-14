"""One read module per enabled section (Task 4.1).

Each owns its `APIRouter` and its `IO_BUDGET`, so a slice adding a section's
read touches only its own module; `server/api/app.py` includes all four.
"""
