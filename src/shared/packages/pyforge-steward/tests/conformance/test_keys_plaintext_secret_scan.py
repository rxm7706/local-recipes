"""Plaintext-secret scan primitive — this story's second AC.

`keys.scan_directory_for_secrets` must flag the fixture as a
`PlaintextSecretFinding` — a type distinct from Story 1.2's `DriftFinding` —
and return `[]` for a directory with no secret-shaped content. Story 1.6
wires this into `steward keys audit`; this story only proves the primitive.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pyforge.steward.keys import (
    DriftFinding,
    PlaintextSecretFinding,
    scan_directory_for_secrets,
    scan_file_for_secrets,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "plaintext_secret_candidate"
FIXTURE_FILE = FIXTURE_DIR / "leaked_key.txt"


def test_fixture_directory_yields_exactly_one_plaintext_secret_finding():
    findings = scan_directory_for_secrets(FIXTURE_DIR)

    assert len(findings) == 1
    finding = findings[0]
    assert isinstance(finding, PlaintextSecretFinding)
    assert not isinstance(finding, DriftFinding)
    assert finding.pattern_name == "anthropic-api-key"
    assert finding.line > 0


def test_plaintextsecretfinding_is_a_distinct_type_from_driftfinding():
    assert PlaintextSecretFinding is not DriftFinding


def test_clean_directory_returns_empty_list(tmp_path):
    (tmp_path / "clean.txt").write_text("nothing secret here\n")

    assert scan_directory_for_secrets(tmp_path) == []


def test_nonexistent_directory_raises_instead_of_silently_reporting_clean(tmp_path):
    with pytest.raises(NotADirectoryError):
        scan_directory_for_secrets(tmp_path / "does-not-exist")


@pytest.mark.skipif(sys.platform == "win32", reason="chmod 000 does not restrict Windows")
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="chmod 000 does not restrict root"
)
def test_unreadable_subdirectory_raises_instead_of_silently_reporting_clean(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "leaked.txt").write_text("sk-ant-api03-SYNTHETIC0000000000000000000000TEST\n")
    locked.chmod(0o000)
    try:
        with pytest.raises(PermissionError):
            scan_directory_for_secrets(tmp_path)
    finally:
        locked.chmod(0o755)


def test_binary_age_file_alongside_a_leaked_secret_does_not_crash_the_scan(tmp_path):
    (tmp_path / "leaked.txt").write_text(
        "sk-ant-api03-SYNTHETIC00000000000000000000000000000000000000TEST\n"
    )
    (tmp_path / "ciphertext.age").write_bytes(bytes(range(256)))

    findings = scan_directory_for_secrets(tmp_path)

    assert len(findings) == 1
    assert findings[0].pattern_name == "anthropic-api-key"


def test_age_identity_and_pem_header_patterns_are_each_detected(tmp_path):
    # Word-marked placeholder, NOT a generated key: `O` is outside the Bech32
    # charset, so this string can never parse as a real age identity — it only
    # has to satisfy the scanner's deliberately loose [A-Z0-9]{20,} tail.
    (tmp_path / "identity.txt").write_text(
        "AGE-SECRET-KEY-1TEST00FAKE00PLACEHOLDER00NOTREAL00SYNTHETIC\n"
    )
    (tmp_path / "key.pem").write_text(
        "-----BEGIN RSA PRIVATE KEY-----\nSYNTHETIC\n-----END RSA PRIVATE KEY-----\n"
    )

    findings = scan_directory_for_secrets(tmp_path)

    assert {f.pattern_name for f in findings} == {"age-identity", "pem-private-key-header"}


def test_single_file_scan_agrees_with_the_directory_scan_for_the_fixture():
    assert scan_file_for_secrets(FIXTURE_FILE) == scan_directory_for_secrets(FIXTURE_DIR)


def test_utf16_encoded_secret_is_still_detected(tmp_path):
    """Interleaved UTF-16 NUL bytes must not defeat the patterns — a
    PowerShell-redirected key file is a routine Windows artifact, and a
    committed UTF-16 secret scanning as clean is a false negative in the
    exact primitive whose contract forbids silent-clean."""
    (tmp_path / "utf16.txt").write_text(
        'ANTHROPIC_API_KEY = "sk-ant-api03-TEST00FAKE00PLACEHOLDER00NOTREAL"\n',
        encoding="utf-16",
    )

    findings = scan_directory_for_secrets(tmp_path)

    assert [f.pattern_name for f in findings] == ["anthropic-api-key"]


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs privileges on Windows")
def test_dangling_symlink_raises_instead_of_silently_reporting_clean(tmp_path):
    """`is_file()` swallowed the OSError from an unresolvable symlink, letting
    it scan as clean; the stat()-based walk must raise instead."""
    (tmp_path / "dangling.txt").symlink_to(tmp_path / "does-not-exist")

    with pytest.raises(FileNotFoundError):
        scan_directory_for_secrets(tmp_path)
