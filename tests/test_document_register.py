"""The gate that keeps the document register honest about what the sets name.

A qualification set is the only thing in this tree that pins evidence, and the
register is the only place that says where that evidence came from and what is
still to be sourced. A set that names a document the register does not list is
a provenance hole, so it is a failure rather than a note.
"""

from __future__ import annotations

import hashlib
import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import document_register
import pytest

REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "qualification/documents.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO / "scripts/document_register.py"), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_as_main(args: list[str], monkeypatch: pytest.MonkeyPatch) -> int:
    """Drives the script as `__main__` in-process, so coverage can see its lines."""
    monkeypatch.setattr(sys, "argv", ["document_register.py", *args])
    with pytest.raises(SystemExit) as caught:
        runpy.run_path(str(REPO / "scripts/document_register.py"), run_name="__main__")
    assert isinstance(caught.value.code, int)
    return caught.value.code


def _transplant(tmp_path: Path) -> Path:
    """A copy of `qualification/` under a scratch repository root, register included."""
    root = tmp_path / "qualification"
    root.mkdir()
    shutil.copy(REGISTER, root / "documents.json")
    for source in sorted((REPO / "qualification").glob("*/qualification.json")):
        case = root / source.parent.name
        (case / "documents").mkdir(parents=True)
        shutil.copy(source, case / "qualification.json")
        for document in sorted((source.parent / "documents").iterdir()):
            shutil.copy(document, case / "documents" / document.name)
    return root / "documents.json"


def test_the_register_lists_every_document_every_qualification_set_names() -> None:
    register = document_register.load_register(REGISTER)
    sets = document_register.set_documents(REGISTER.parent)
    assert sets, "found no qualification set to check the register against"
    assert document_register.unlisted(register, sets) == []


def test_the_register_claims_in_hand_only_for_a_file_under_qualification() -> None:
    register = document_register.load_register(REGISTER)
    assert document_register.misplaced(register, REPO) == []


def test_every_in_hand_row_carries_the_digest_of_the_bytes_on_disk() -> None:
    register = document_register.load_register(REGISTER)
    in_hand = [row for row in register.documents if row.status == "in_hand"]
    assert in_hand, "the register claims nothing is in hand"
    for row in in_hand:
        assert row.local_path is not None
        path = REPO / row.local_path
        facts = document_register.measured(row, REPO)
        assert facts is not None
        size, digest = facts
        assert size == path.stat().st_size
        assert digest == hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_set_naming_a_document_the_register_does_not_list_fails(
    tmp_path: Path,
) -> None:
    register_path = _transplant(tmp_path)
    manifest = register_path.parent / "ccl-fy2025/qualification.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["cases"][0]["documents"].append("documents/CCL_FY2025_EXHIBIT.txt")
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    result = _run("--register", str(register_path), "--report")
    assert result.returncode == 1
    assert "CCL_FY2025_EXHIBIT.txt" in result.stderr
    assert "absent from the register" in result.stderr
    assert result.stdout == ""


def test_a_row_claiming_in_hand_for_an_absent_file_fails(tmp_path: Path) -> None:
    register_path = _transplant(tmp_path)
    payload = json.loads(register_path.read_text(encoding="utf-8"))
    for row in payload["documents"]:
        if row["id"] == "ccl-fy2025-10k":
            row["local_path"] = "qualification/ccl-fy2025/documents/NOT_THERE.txt"
    register_path.write_text(json.dumps(payload), encoding="utf-8")

    result = _run("--register", str(register_path))
    assert result.returncode == 1
    assert "claims in_hand" in result.stderr


def test_the_script_refuses_when_it_reads_no_qualification_set(tmp_path: Path) -> None:
    root = tmp_path / "qualification"
    root.mkdir()
    shutil.copy(REGISTER, root / "documents.json")

    result = _run("--register", str(root / "documents.json"))
    assert result.returncode == 2
    assert "scanned nothing is a failure" in result.stderr


def test_the_script_refuses_when_the_register_lists_no_document(tmp_path: Path) -> None:
    register_path = _transplant(tmp_path)
    register_path.write_text(json.dumps({"documents": []}), encoding="utf-8")

    result = _run("--register", str(register_path))
    assert result.returncode == 2
    assert "0 register rows" in result.stderr


def test_a_row_whose_status_is_not_one_of_the_four_refuses(tmp_path: Path) -> None:
    path = tmp_path / "documents.json"
    path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "id": "invented",
                        "issuer": None,
                        "document": "d",
                        "modules": [],
                        "pathways": [],
                        "source": None,
                        "status": "probably_fine",
                        "local_path": None,
                        "external_path": None,
                        "demand_verified": False,
                        "note": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(document_register.UnknownStatus, match="probably_fine"):
        document_register.load_register(path)


def test_the_report_names_every_row_and_the_key_source_it_never_admits() -> None:
    register = document_register.load_register(REGISTER)
    table = document_register.report(register, REPO)
    for row in register.documents:
        assert f"`{row.id}`" in table
    assert register.key_sources, "the register records no key source"
    for key in register.key_sources:
        assert f"`{key['id']}`" in table
        assert "never admitted" in table
    # Only the in-hand rows are asserted on: whether an out-of-tree row is
    # measured at all depends on the machine the register is read from.
    for row in register.documents:
        if row.status == "in_hand":
            facts = document_register.measured(row, REPO)
            assert facts is not None
            assert f"`{facts[1][:16]}…`" in table


def test_the_register_passes_its_own_gate_as_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _run_as_main(["--report"], monkeypatch) == 0
