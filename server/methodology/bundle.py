"""The methodology bundle: authority, verified on the bytes at use.

Invariant 4. The bundle is the methodology authority, it is read-only at runtime,
and its integrity is checked *at use* rather than at startup only -- because a
digest verified when the process booted says nothing about the file the process
reads an hour later, and that file is the methodology a credit opinion rests on.

Two rules from `docs/DECISIONS.md` shape what is here.

*§5, the carve-out.* Upstream merged CP-PARSE into CP-0. The host keeps them as
separate stage-0 nodes because CP-PARSE owns the `document_parse_manifest` over
the host's own already-extracted blocks, which is host territory. `_CARVE_OUTS`
is the host's one declaration, and CP-PARSE receives the whole CP-0 skill.

*§5's consequence, which is easy to miss.* `assemble_authority` must not slice
`SKILL.md` on section markers. The merged skill has dropped
`## CP-PARSE runnable profile`, so a slicer looking for it would break CP-0 as
well as CP-PARSE. The whole file, or a refusal.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from hashlib import sha256
from pathlib import Path
from typing import Any

from server.refusals import Refusal, RefusalCode

MANIFEST_NAME = "DEPLOY_V_INTEGRITY_v1.json"
SKILLS_DIR = "skills"

# The host's one declaration (`docs/DECISIONS.md` §5). CP-PARSE is not a folder
# in this build; it is CP-0's authority under its own route node.
_CARVE_OUTS = {"CP-PARSE": "CP-0"}


@dataclass(frozen=True, slots=True)
class Authority:
    """Everything one module may read, and the bytes it actually read."""

    module_id: str
    build_id: str
    files: dict[str, bytes]


@dataclass(frozen=True)
class Bundle:
    """The vendored tree, and the manifest that says what it should contain."""

    root: Path

    @cached_property
    def _manifest(self) -> dict[str, Any]:
        raw = (self.root / MANIFEST_NAME).read_bytes()
        loaded: dict[str, Any] = json.loads(raw)
        return loaded

    @cached_property
    def manifest_sha256(self) -> str:
        """The one vendored file the manifest cannot cover: its own bytes.

        `docs/DECISIONS.md` §13 records this digest separately, because the host
        does not mint an identity for something that ships with one.
        """
        return sha256((self.root / MANIFEST_NAME).read_bytes()).hexdigest()

    @cached_property
    def build_id(self) -> str:
        """The build a run is pinned to. One build never executes as another."""
        return str(self._manifest["build_id"])

    def skill_of(self, module_id: str) -> dict[str, Any]:
        """The manifest entry for a module, following the host's carve-outs."""
        wanted = _CARVE_OUTS.get(module_id, module_id)
        for skill in self._manifest.get("skills", []):
            if skill.get("module_id") == wanted:
                entry: dict[str, Any] = skill
                return entry
        raise Refusal(RefusalCode.AUTHORITY_MODULE_UNKNOWN)


def verified_bytes(bundle: Bundle, module_id: str, relative_path: str) -> bytes:
    """One file of one module's authority, proven against the manifest.

    Refuses `AUTHORITY_BYTES_MISMATCH` for a file whose bytes have moved, one the
    tree no longer has, and one the manifest never named -- which is also what
    stops a path leaving the module's folder, since no traversal is a name the
    manifest carries. The refusal carries the code alone: a path or a body would
    put the vendor's filesystem into whatever logs it.
    """
    skill = bundle.skill_of(module_id)
    expected = skill.get("relative_file_hashes", {}).get(relative_path)
    if not isinstance(expected, dict):
        raise Refusal(RefusalCode.AUTHORITY_BYTES_MISMATCH)

    path = bundle.root / SKILLS_DIR / str(skill["folder_slug"]) / relative_path
    try:
        data = path.read_bytes()
    except OSError:
        raise Refusal(RefusalCode.AUTHORITY_BYTES_MISMATCH) from None

    if sha256(data).hexdigest() != expected.get("sha256"):
        raise Refusal(RefusalCode.AUTHORITY_BYTES_MISMATCH)
    return data


def assemble_authority(bundle: Bundle, module_id: str) -> Authority:
    """Every file the manifest gives this module, each verified as it is read.

    Never a slice of `SKILL.md`. See this module's docstring: the section marker
    a slicer would look for is gone from the merged upstream skill, so slicing
    breaks CP-0 and CP-PARSE together.
    """
    skill = bundle.skill_of(module_id)
    names = sorted(skill.get("relative_file_hashes", {}))
    return Authority(
        module_id=module_id,
        build_id=bundle.build_id,
        files={name: verified_bytes(bundle, module_id, name) for name in names},
    )


def authority_digest(authority: Authority) -> str:
    """What authority a module executed under, in one value.

    Over the build and the verified bytes, so two modules of one build differ and
    one module across two builds differs. A run records this; a replay that
    produced a different one did not run the same methodology.
    """
    digest = sha256()
    digest.update(authority.build_id.encode("utf-8"))
    for name in sorted(authority.files):
        digest.update(name.encode("utf-8"))
        digest.update(sha256(authority.files[name]).digest())
    return digest.hexdigest()
