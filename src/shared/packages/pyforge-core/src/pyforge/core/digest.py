"""pyforge.core.digest -- binary-safe sha256 digesting for artifact
integrity (Story 46.1, spec-pyforge-marshal CAP-192).

Full-length (64 hex char) sha256 over an artifact's raw bytes, streamed in
fixed-size chunks so a large binary (e.g. a codegraph index) is never
loaded whole into memory. This is a DIFFERENT domain from
``pyforge.marshal.seed.detect.hashes``: that module hashes line-ending-
normalized TEXT to an 8-hex-char truncation for hand-edit detection over
source files; this module hashes raw BYTES to a full digest for verifying
a downloaded artifact matches what published it -- no overlap, no shared
call site.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1 << 20  # 1 MiB


def sha256_file(path: Path) -> str:
    """The full 64-hex-char sha256 digest of ``path``'s raw bytes, read in
    ``_CHUNK_SIZE`` chunks. Raises ``OSError`` for a missing/unreadable
    file -- this function makes no missing-file allowance itself; a caller
    deciding whether a missing file is a fallback trigger (``verify_digest``
    below) is a different, narrower contract."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_digest(path: Path, expected: str) -> bool:
    """``True`` when ``path`` exists and its sha256 digest equals
    ``expected`` (case-insensitive, surrounding whitespace stripped).
    ``False`` for a missing file or any mismatch -- never raises, so a
    caller can use this directly as a fetch-succeeded predicate without a
    ``try/except`` of its own."""
    candidate = Path(path)
    if not candidate.is_file():
        return False
    return sha256_file(candidate).lower() == expected.strip().lower()
