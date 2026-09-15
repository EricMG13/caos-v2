"""A qualification set as a declared form on disk, and the loader that reads it.

`CLAUDE.md`'s Phase 10 ledger: a set lived in memory and was digested, not
stored -- "enough for the binding to be checkable and not enough for two people
to be sure they hold the same set without comparing digests by hand". Once a
case carried its documents as bytes it got worse: a set of any size became a
Python literal nobody would write.

The property that makes the form worth having is one line long: **a set read
from disk digests identically to the same set built in memory**. Without it the
file would be a convenience that quietly changes what a verdict binds. With it,
a reviewer can be handed a directory, and the digest in the verdict is a
statement about the bytes in their hands.

What the loader refuses is the other half. The file is authored by someone --
possibly not by this repository, possibly years later -- so it is read the way
`read_verdict` reads a verdict: a closed shape, refusals apart by remedy, and
nothing taken on trust. A document path that leaves the set's directory is the
one refusal that is about safety rather than shape.
"""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from server.boundary_text import BoundaryText
from server.evidence.ingest import Document
from server.qualification.matrix import (
    ExpectedCitation,
    QualificationCase,
    QualificationSet,
    qualification_set_digest,
)
from server.qualification.on_disk import MANIFEST, load_qualification_set
from server.refusals import Refusal, RefusalCode
from server.store.run_inputs import RunSubject

REPORT = b"""Acme Holdings plc annual report 2026
Total debt at 31 December 2026 was USD 1,240.0m
"""
OTHER = b"""Borealis Industries plc annual report 2026
Total debt at 31 December 2026 was USD 880.0m
"""
QUOTE = "Total debt at 31 December 2026"


def _in_memory() -> QualificationSet:
    """The set the fixture below writes out, built the way Python callers do."""
    return QualificationSet(
        cases=(
            QualificationCase(
                label="acme-2026",
                documents=(
                    Document(filename=BoundaryText.of("report.txt"), data=REPORT),
                ),
                profile_id="FULL_CREDIT_32",
                selection_id="DEEP_RESEARCH",
                expects=(
                    ExpectedCitation(
                        module_id="CP-0",
                        document_sha256=sha256(REPORT).hexdigest(),
                        matched_text=QUOTE,
                    ),
                ),
            ),
            QualificationCase(
                label="borealis-2026",
                documents=(
                    Document(filename=BoundaryText.of("report.txt"), data=OTHER),
                ),
                profile_id="FULL_CREDIT_32",
                selection_id="DEEP_RESEARCH",
                expects=(
                    ExpectedCitation(
                        module_id="CP-0",
                        document_sha256=sha256(OTHER).hexdigest(),
                        matched_text=QUOTE,
                    ),
                ),
            ),
        )
    )


def _manifest() -> dict[str, object]:
    return {
        "cases": [
            {
                "label": "acme-2026",
                "profile_id": "FULL_CREDIT_32",
                "selection_id": "DEEP_RESEARCH",
                "documents": ["documents/acme-2026/report.txt"],
                "expects": [
                    {
                        "module_id": "CP-0",
                        "document_sha256": sha256(REPORT).hexdigest(),
                        "matched_text": QUOTE,
                    }
                ],
            },
            {
                "label": "borealis-2026",
                "profile_id": "FULL_CREDIT_32",
                "selection_id": "DEEP_RESEARCH",
                "documents": ["documents/borealis-2026/report.txt"],
                "expects": [
                    {
                        "module_id": "CP-0",
                        "document_sha256": sha256(OTHER).hexdigest(),
                        "matched_text": QUOTE,
                    }
                ],
            },
        ]
    }


@pytest.fixture
def on_disk(tmp_path: Path) -> Path:
    """The set above, written out in the declared form."""
    return _write(tmp_path, _manifest())


def _write(root: Path, manifest: object) -> Path:
    for case, data in (("acme-2026", REPORT), ("borealis-2026", OTHER)):
        document = root / "documents" / case / "report.txt"
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_bytes(data)
    (root / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_a_set_read_from_disk_digests_identically_to_one_built_in_memory(
    on_disk: Path,
) -> None:
    """The property the whole form rests on.

    A verdict binds `qualification_set_sha256`. If loading changed the digest,
    the file would be a second way of saying something slightly different, and
    a signature given over the directory would not name the set a caller ran.
    """
    loaded = load_qualification_set(on_disk)

    assert qualification_set_digest(loaded) == qualification_set_digest(_in_memory())
    assert [case.label for case in loaded.cases] == ["acme-2026", "borealis-2026"]
    assert loaded.cases[0].documents[0].data == REPORT
    assert loaded.cases[0].documents[0].filename.value == "report.txt"


def test_the_bytes_on_disk_are_what_the_case_carries(on_disk: Path) -> None:
    """Edit a document and the digest moves, because the digest covers content.

    This is what stops a set being edited underneath a verdict that binds it:
    the file is not a name for a set, it is the set.
    """
    before = qualification_set_digest(load_qualification_set(on_disk))
    (on_disk / "documents" / "acme-2026" / "report.txt").write_bytes(b"something else")

    assert qualification_set_digest(load_qualification_set(on_disk)) != before


def test_a_document_path_that_leaves_the_set_is_refused(tmp_path: Path) -> None:
    """The one refusal here that is about safety rather than shape.

    A manifest is authored, possibly not by this repository. A path escaping the
    set's own directory would let a file anywhere the process can read be
    admitted into a case and digested as part of it.
    """
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"not part of the set")
    root = tmp_path / "set"
    root.mkdir()
    manifest = _manifest()
    manifest["cases"][0]["documents"] = ["../outside.txt"]  # type: ignore[index]

    with pytest.raises(Refusal) as refused:
        load_qualification_set(_write(root, manifest))

    assert refused.value.code is RefusalCode.QUALIFICATION_SET_PATH_ESCAPES


def test_an_absolute_document_path_is_refused(tmp_path: Path) -> None:
    """Absolute is the same escape by a shorter route, and `Path.joinpath`
    silently discards the root it was joined to when handed one."""
    root = tmp_path / "set"
    root.mkdir()
    manifest = _manifest()
    manifest["cases"][0]["documents"] = ["/etc/hostname"]  # type: ignore[index]

    with pytest.raises(Refusal) as refused:
        load_qualification_set(_write(root, manifest))

    assert refused.value.code is RefusalCode.QUALIFICATION_SET_PATH_ESCAPES


def test_a_manifest_that_is_not_the_declared_shape_is_refused(
    tmp_path: Path,
) -> None:
    """Every way the file can fail to be a qualification set, one code.

    Apart from the escape above, a malformed manifest has one remedy -- fix the
    file -- so it gets one refusal rather than a taxonomy nobody acts on
    differently.
    """
    root = tmp_path / "set"
    root.mkdir()
    malformed: list[object] = [
        {"cases": "not a list"},
        {"cases": [{"label": "a"}]},
        {"cases": [{**_manifest()["cases"][0], "documents": "not a list"}]},  # type: ignore[index]
        {"cases": [{**_manifest()["cases"][0], "expects": [{"module_id": "CP-0"}]}]},  # type: ignore[index]
        {"cases": [{**_manifest()["cases"][0], "label": ""}]},  # type: ignore[index]
        {"cases": [{**_manifest()["cases"][0], "undeclared": 1}]},  # type: ignore[index]
        ["not a mapping"],
    ]

    for manifest in malformed:
        with pytest.raises(Refusal) as refused:
            load_qualification_set(_write(root, manifest))
        assert refused.value.code is RefusalCode.QUALIFICATION_SET_FILE_INVALID, (
            manifest
        )


def test_an_undeclared_key_at_the_top_of_the_manifest_is_refused(
    tmp_path: Path,
) -> None:
    """Closed at the outer shape too, not only per case.

    A key this loader ignores is a statement its author believed they had made
    -- a `tolerance` or a `provider` at the top of the file would be read by a
    person and by nothing else.
    """
    root = tmp_path / "set"
    root.mkdir()
    manifest = {**_manifest(), "notes": "for the reviewer"}

    with pytest.raises(Refusal) as refused:
        load_qualification_set(_write(root, manifest))

    assert refused.value.code is RefusalCode.QUALIFICATION_SET_FILE_INVALID


def test_a_document_that_is_not_a_path_string_is_refused(tmp_path: Path) -> None:
    """`documents` is a list of paths; an object or a number in it is a manifest
    written against a different format than this one."""
    root = tmp_path / "set"
    root.mkdir()
    manifest = _manifest()
    manifest["cases"][0]["documents"] = [{"path": "documents/a.txt"}]  # type: ignore[index]

    with pytest.raises(Refusal) as refused:
        load_qualification_set(_write(root, manifest))

    assert refused.value.code is RefusalCode.QUALIFICATION_SET_FILE_INVALID


def test_a_filename_the_boundary_refuses_is_a_malformed_manifest(
    tmp_path: Path,
) -> None:
    """A filename is digested and admitted, so it crosses `BoundaryText`.

    Retyped on the way out: a bidi override in a document's name is a defect in
    the file being read, and `BOUNDARY_TEXT_INVALID` would send a reader looking
    at the loader rather than at the manifest that named it.
    """
    root = tmp_path / "set"
    root.mkdir()
    hostile = root / "documents" / "acme-2026"
    hostile.mkdir(parents=True, exist_ok=True)
    # U+202E, one of the nine controls `BoundaryText` refuses.
    (hostile / "re\u202eport.txt").write_bytes(REPORT)
    manifest = _manifest()
    manifest["cases"][0]["documents"] = [  # type: ignore[index]
        "documents/acme-2026/re\u202eport.txt"
    ]

    with pytest.raises(Refusal) as refused:
        load_qualification_set(_write(root, manifest))

    assert refused.value.code is RefusalCode.QUALIFICATION_SET_FILE_INVALID


def test_a_missing_manifest_or_document_is_refused(tmp_path: Path) -> None:
    """A set is its bytes. One named document absent is not a smaller set."""
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(Refusal) as refused:
        load_qualification_set(empty)
    assert refused.value.code is RefusalCode.QUALIFICATION_SET_FILE_INVALID

    root = _write(tmp_path / "set", _manifest())
    (root / "documents" / "acme-2026" / "report.txt").unlink()
    with pytest.raises(Refusal) as gone:
        load_qualification_set(root)
    assert gone.value.code is RefusalCode.QUALIFICATION_SET_FILE_INVALID


def test_a_manifest_that_is_not_json_is_refused(tmp_path: Path) -> None:
    """Bytes that will not parse say nothing about a set."""
    root = _write(tmp_path / "set", _manifest())
    (root / MANIFEST).write_text("{ not json", encoding="utf-8")

    with pytest.raises(Refusal) as refused:
        load_qualification_set(root)

    assert refused.value.code is RefusalCode.QUALIFICATION_SET_FILE_INVALID


# `_in_memory()`'s digest before a case could carry a subject. A set whose cases
# carry none must keep binding exactly this, or every earlier verdict is orphaned.
GOLDEN = "64bc178c0010b0fe104e01f4f7fac2bce35d1dc09f21fea86ff996aa99233373"
SUBJECT = {
    "issuer_id": "ACME",
    "issuer_name": "Acme Holdings plc",
    "reporting_period": "FY2026",
    "analysis_date": "2026-09-13",
}


def test_a_set_without_subjects_keeps_its_golden_digest(on_disk: Path) -> None:
    assert qualification_set_digest(_in_memory()) == GOLDEN
    loaded = load_qualification_set(on_disk)
    assert all(case.subject is None for case in loaded.cases)
    assert qualification_set_digest(loaded) == GOLDEN


def test_a_declared_subject_round_trips_and_is_digested(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["cases"][0]["subject"] = dict(SUBJECT)  # type: ignore[index]
    loaded = load_qualification_set(_write(tmp_path, manifest))

    subject = RunSubject(**SUBJECT)
    assert loaded.cases[0].subject == subject
    assert loaded.cases[1].subject is None
    with_subject = qualification_set_digest(loaded)
    assert with_subject != GOLDEN
    first, second = _in_memory().cases
    built = QualificationSet((replace(first, subject=subject), second))
    assert qualification_set_digest(built) == with_subject
    for key, value in SUBJECT.items():
        moved = replace(subject, **{key: value + "X"})
        changed = QualificationSet((replace(first, subject=moved), second))
        assert qualification_set_digest(changed) not in {with_subject, GOLDEN}, key


@pytest.mark.parametrize(
    "declared",
    [
        {k: v for k, v in SUBJECT.items() if k != "analysis_date"},
        {**SUBJECT, "cos_run_id": "COS-1"},
        {**SUBJECT, "issuer_id": 7},
        {**SUBJECT, "issuer_name": ""},
        {**SUBJECT, "issuer_name": " padded"},
        {**SUBJECT, "analysis_date": "2026-02-30"},
        [SUBJECT["issuer_id"]],
        None,
    ],
)
def test_a_subject_that_is_not_the_closed_shape_is_refused(
    tmp_path: Path, declared: object
) -> None:
    manifest = _manifest()
    manifest["cases"][0]["subject"] = declared  # type: ignore[index]

    with pytest.raises(Refusal) as refused:
        load_qualification_set(_write(tmp_path, manifest))

    assert refused.value.code is RefusalCode.QUALIFICATION_SET_FILE_INVALID
