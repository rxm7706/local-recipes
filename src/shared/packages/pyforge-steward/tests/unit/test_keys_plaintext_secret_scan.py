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

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "plaintext_secret_candidate"
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
@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="chmod 000 does not restrict root")
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
    (tmp_path / "leaked.txt").write_text("sk-ant-api03-SYNTHETIC00000000000000000000000000000000000000TEST\n")
    (tmp_path / "ciphertext.age").write_bytes(bytes(range(256)))

    findings = scan_directory_for_secrets(tmp_path)

    assert len(findings) == 1
    assert findings[0].pattern_name == "anthropic-api-key"


def test_age_identity_and_pem_header_patterns_are_each_detected(tmp_path):
    # Word-marked placeholder, NOT a generated key: `O` is outside the Bech32
    # charset, so this string can never parse as a real age identity — it only
    # has to satisfy the scanner's deliberately loose [A-Z0-9]{20,} tail.
    (tmp_path / "identity.txt").write_text("AGE-SECRET-KEY-1TEST00FAKE00PLACEHOLDER00NOTREAL00SYNTHETIC\n")
    (tmp_path / "key.pem").write_text("-----BEGIN RSA PRIVATE KEY-----\nSYNTHETIC\n-----END RSA PRIVATE KEY-----\n")

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


# --- Story 118.9 (spec-pyforge-steward CAP-178): the same table over text in hand, and redaction ---


def test_scan_text_for_secrets_names_the_label_line_and_pattern_never_the_value():
    from pyforge.steward.keys import scan_text_for_secrets

    planted = "-----BEGIN OPENSSH PRIVATE KEY-----"
    findings = scan_text_for_secrets(f"commit abc\n+ok\n+{planted}\n", "origin/main..origin/gitops/x")
    assert [(f.line, f.pattern_name) for f in findings] == [(3, "pem-private-key-header")]
    assert str(findings[0].path) == "origin/main..origin/gitops/x"
    assert planted not in findings[0].message
    assert scan_text_for_secrets("GITOPS_DEPLOY_KEY\nenv: HETZNER_TOKEN\n", "nic-config.yaml") == []


def test_redact_secret_shapes_masks_known_values_and_every_pattern():
    from pyforge.steward.keys import redact_secret_shapes

    line = "token opaque-1 and AGE-SECRET-KEY-1TEST00FAKE00PLACEHOLDER00NOTREAL00SYNTHETIC end"
    assert redact_secret_shapes(line, ("opaque-1", "")) == "token *** and *** end"
    assert redact_secret_shapes("plain error") == "plain error"


# --- Story 118.9 review: the shapes a cloud GitOps run can leak, and multi-line redaction ---

# Synthetic, word-marked values: none is a real credential.
_HETZNER_SHAPED = "SyntheticHetznerToken0000FAKE0000placeholder0000NOTREAL0000Test0"
_KEY_BODY = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW"
_MULTILINE_KEY = f"-----BEGIN OPENSSH PRIVATE KEY-----\n{_KEY_BODY}\n-----END OPENSSH PRIVATE KEY-----"


@pytest.mark.parametrize(
    ("line", "pattern_name"),
    [
        ("-----begin openssh private key-----", "pem-private-key-header"),
        ("client-key-data: LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQo=", "pem-block-base64"),
        ("token: ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8", "github-token"),
        ("GH=ghs_" + "Z" * 36, "github-token"),
        ("github_pat_" + "11SYNTHETIC0000FAKE_placeholder", "github-fine-grained-token"),
        (f'hcloud_token: "{_HETZNER_SHAPED}"', "hetzner-api-token"),
        (f"HCLOUD_TOKEN={_HETZNER_SHAPED}", "hetzner-api-token"),
    ],
)
def test_the_table_finds_each_shape_a_cloud_run_can_leak(line: str, pattern_name: str) -> None:
    from pyforge.steward.keys import scan_text_for_secrets

    assert len(_HETZNER_SHAPED) == 64
    assert [f.pattern_name for f in scan_text_for_secrets(line, "x")] == [pattern_name]


@pytest.mark.parametrize(
    "line",
    [
        "image: ghcr.io/nebari/x@sha256:" + "0123456789abcdef" * 4,
        "digest: " + "0123456789ABCDEF" * 4,
        _HETZNER_SHAPED + "x",  # 65 alphanumerics
        "x" + _HETZNER_SHAPED[1:].lower(),  # 64, no uppercase
        "integrity: sha512-+" + _HETZNER_SHAPED + "/",  # a run inside a base64 string
        "env: GITOPS_DEPLOY_KEY",
        "ghp_short",
    ],
)
def test_a_digest_a_base64_run_and_an_env_name_are_not_secret_shaped(line: str) -> None:
    from pyforge.steward.keys import scan_text_for_secrets

    assert scan_text_for_secrets(line, "x") == []


def test_redaction_masks_a_pem_header_to_the_end_of_its_line():
    from pyforge.steward.keys import redact_secret_shapes

    escaped = _MULTILINE_KEY.replace("\n", "\\n")
    out = redact_secret_shapes(f'parse key: "{escaped}"')
    assert out == 'parse key: "***'
    assert _KEY_BODY[:12] not in out


def test_redaction_masks_a_resolved_multiline_value_whole_escaped_and_line_by_line():
    from pyforge.steward.keys import redact_secret_shapes

    # A PEM key escaped onto one line is masked from its header to the end of the line.
    escaped = _MULTILINE_KEY.replace("\n", "\\n")
    assert redact_secret_shapes(f"x {escaped} y", (_MULTILINE_KEY,)) == "x ***"
    # A multi-line value with no PEM header is masked whole in its escaped form, and nothing more.
    opaque = "synthetic-line-one\nsynthetic-line-two"
    assert redact_secret_shapes(f"x {opaque.replace(chr(10), chr(92) + 'n')} y", (opaque,)) == "x *** y"
    assert redact_secret_shapes(f"bad line {_KEY_BODY}", (_MULTILINE_KEY,)) == "bad line ***"
    # A line shorter than eight characters is not masked on its own (it would mask ordinary words).
    assert redact_secret_shapes("ok short", ("ab\nshort",)) == "ok short"


# --- Story 118.9 second review: redaction order, short values, public PEM and SRI values ---


def test_redaction_masks_a_json_dumped_key_with_escaped_slashes_before_any_literal_mask():
    import json

    from pyforge.steward.keys import redact_secret_shapes

    body = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ/AAAAAAAAABAAAAMwAAAA+tzc2gt/ZW"
    key = f"-----BEGIN OPENSSH PRIVATE KEY-----\n{body}\n-----END OPENSSH PRIVATE KEY-----\n"
    line = "error " + json.dumps({"key": key}).replace("/", "\\/")
    out = redact_secret_shapes(line, (key,))
    assert out == 'error {"key": "***'
    for fragment in ("b3BlbnNzaC1rZXkt", "tzc2gt", "AAAAMwAAAA"):
        assert fragment not in out


def test_a_resolved_value_under_four_characters_is_not_masked_literally():
    from pyforge.steward.keys import redact_secret_shapes

    assert redact_secret_shapes("a banana at noon", ("a",)) == "a banana at noon"
    assert redact_secret_shapes("pin 1234 ok", ("1234",)) == "pin *** ok"


def _b64(text: str) -> str:
    import base64

    return base64.b64encode(text.encode()).decode()


@pytest.mark.parametrize(
    "header",
    [
        "RSA PRIVATE KEY",
        "OPENSSH PRIVATE KEY",
        "EC PRIVATE KEY",
        "PRIVATE KEY",
        "ENCRYPTED PRIVATE KEY",
        "PGP PRIVATE KEY BLOCK",
    ],
)
def test_a_base64_private_key_block_is_found(header: str):
    from pyforge.steward.keys import scan_text_for_secrets

    encoded = _b64(f"-----BEGIN {header}-----\nSYNTHETIC\n-----END {header}-----\n")
    assert [f.pattern_name for f in scan_text_for_secrets(f"client-key-data: {encoded}", "x")] == ["pem-block-base64"]


@pytest.mark.parametrize(
    "header",
    [
        "CERTIFICATE",
        "PUBLIC KEY",
        "RSA PUBLIC KEY",
        "X509 CRL",
        "TRUSTED CERTIFICATE",
        "NEW CERTIFICATE REQUEST",
        "CERTIFICATE REQUEST",
        "PGP PUBLIC KEY BLOCK",
    ],
)
def test_a_base64_public_block_is_not_secret_shaped(header: str):
    from pyforge.steward.keys import scan_text_for_secrets

    encoded = _b64(f"-----BEGIN {header}-----\nSYNTHETIC\n-----END {header}-----\n")
    assert scan_text_for_secrets(f"certificate-authority-data: {encoded}", "x") == []


def test_a_pgp_private_key_block_header_is_found():
    from pyforge.steward.keys import scan_text_for_secrets

    found = scan_text_for_secrets("-----BEGIN PGP PRIVATE KEY BLOCK-----", "x")
    assert [f.pattern_name for f in found] == ["pem-private-key-header"]


@pytest.mark.parametrize("algorithm", ["sha256", "sha384", "sha512"])
def test_an_sri_value_is_not_hetzner_shaped(algorithm: str):
    from pyforge.steward.keys import scan_text_for_secrets

    assert scan_text_for_secrets(f'"integrity": "{algorithm}-{_HETZNER_SHAPED}"', "x") == []
