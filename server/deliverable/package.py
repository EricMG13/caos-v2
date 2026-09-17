"""Deterministic audit packages, portable consistency checks, exclusive creation.

§55: a package proves internal consistency, not externally authenticated signers.
Its archived verifier retains the renderer pin for that build.
"""

from __future__ import annotations

import zipfile
import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from server.deliverable.verify_package import verify

PAYLOAD = "payload.json"
RECEIPT = "receipt.json"
EXPORT = "deliverable.html"


def _compression(data: bytes) -> int:
    """Keep generated packages inside the verifier's bounded ratio policy."""
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed_size = len(compressor.compress(data) + compressor.flush())
    return (
        zipfile.ZIP_STORED
        if len(data) > 100 * max(1, compressed_size)
        else zipfile.ZIP_DEFLATED
    )


@dataclass(frozen=True, slots=True)
class Verification:
    """What a reader learns from the archive, and why it failed if it did."""

    verified: bool
    reason: str | None = None


def build_package(payload: bytes, receipt: bytes, export: bytes) -> bytes:
    """Five sorted members, fixed timestamps and compression for this build."""
    directory = Path(__file__).parent
    members = {PAYLOAD: payload, RECEIPT: receipt, EXPORT: export}
    for name in ("render.py", "verify_package.py"):
        members[name] = (directory / name).read_bytes()
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o600 << 16
            archive.writestr(
                info, data, compress_type=_compression(data), compresslevel=9
            )
    return buffer.getvalue()


def verify_package(archive_bytes: bytes) -> Verification:
    """The portable verifier's verdict in the host's existing return type."""
    return Verification(*verify(archive_bytes))


def write_package(path: Path, archive_bytes: bytes) -> None:
    """Create once; the filesystem atomically refuses any existing path."""
    with path.open("xb") as destination:
        destination.write(archive_bytes)
