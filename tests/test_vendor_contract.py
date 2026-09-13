"""The vendor's own validators, loaded from verified bytes without touching the
interpreter's import state (Phase 3 Task 3.1, brief correction 4)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from server.methodology.bundle import Bundle
from server.methodology.vendor import load_vendor_contract
from server.refusals import Refusal, RefusalCode

VENDORED = Path(__file__).resolve().parents[1] / "vendor/deploy-v"
GENERIC = (
    "validate_handoff",
    "completeness_check",
    "cp_tables",
    "credit_os",
    "credit_os_v",
)


def _import_state() -> tuple[object, ...]:
    return (
        list(sys.path),
        list(sys.meta_path),
        dict(sys.path_importer_cache),
        sys.dont_write_bytecode,
    )


def test_vendor_loader_leaves_sys_path_untouched() -> None:
    before = _import_state()
    contract = load_vendor_contract(Bundle(VENDORED))
    assert _import_state() == before
    # Standard-library imports the vendor code makes are ordinary; no vendor
    # module, generic or privately named, is left registered.
    assert not any(
        name.split(".")[0] in GENERIC or name.startswith("_caos_vendor")
        for name in sys.modules
    )
    assert not list(VENDORED.rglob("__pycache__"))
    # The loaded code is the vendor's: its validator rejects an empty handoff.
    assert contract.validate_handoff.validate_text("", filename="x.md").exit_code != 0


def test_vendor_code_that_moved_refuses(tmp_path: Path) -> None:
    import shutil

    root = tmp_path / "bundle"
    shutil.copytree(VENDORED, root)
    target = root / "skills/cp-os-credit-os/scripts/validate_handoff.py"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(Refusal) as refused:
        load_vendor_contract(Bundle(root))
    assert refused.value.code is RefusalCode.AUTHORITY_BYTES_MISMATCH
