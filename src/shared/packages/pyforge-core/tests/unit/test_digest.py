"""Unit tests for ``pyforge.core.digest`` (Story 46.1, CAP-192)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pyforge.core.digest import sha256_file, verify_digest


def test_sha256_file_matches_hashlib_reference(tmp_path: Path) -> None:
    target = tmp_path / "artifact.bin"
    payload = b"\x00\x01\xffsome binary content" * 1000
    target.write_bytes(payload)

    assert sha256_file(target) == hashlib.sha256(payload).hexdigest()


def test_sha256_file_streams_across_chunk_boundary(tmp_path: Path) -> None:
    target = tmp_path / "big.bin"
    payload = b"a" * (2 * (1 << 20) + 17)  # spans multiple 1 MiB chunks
    target.write_bytes(payload)

    assert sha256_file(target) == hashlib.sha256(payload).hexdigest()


def test_verify_digest_true_for_matching_file(tmp_path: Path) -> None:
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"content")
    expected = hashlib.sha256(b"content").hexdigest()

    assert verify_digest(target, expected) is True


def test_verify_digest_is_case_and_whitespace_insensitive(tmp_path: Path) -> None:
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"content")
    expected = hashlib.sha256(b"content").hexdigest()

    assert verify_digest(target, f"  {expected.upper()}\n") is True


def test_verify_digest_false_for_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"content")

    assert verify_digest(target, "0" * 64) is False


def test_verify_digest_false_for_missing_file(tmp_path: Path) -> None:
    assert verify_digest(tmp_path / "does-not-exist.bin", "0" * 64) is False


def test_verify_digest_false_for_directory(tmp_path: Path) -> None:
    directory = tmp_path / "adir"
    directory.mkdir()

    assert verify_digest(directory, "0" * 64) is False
