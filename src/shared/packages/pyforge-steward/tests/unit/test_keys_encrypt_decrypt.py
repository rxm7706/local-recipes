"""`age` encrypt/decrypt primitives + `KeysDuty` CLI dispatch — Story 1.3.

Covers the I/O matrix's round-trip, real-ciphertext, wrong-identity, and
bare/unimplemented-verb rows, both at the primitive level (`encrypt_file`/
`decrypt_file` directly) and through the CLI (`main(["keys", ...])`) — the
two surfaces this story wires. Identities are generated directly via the real
`age-keygen` binary in test setup, never through a Steward primitive (this
story's spec, "Never" — identity generation is a Story 1.4+ concern).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.keys import decrypt_file, encrypt_file

AGE_MAGIC = b"age-encryption.org/v1"


def _generate_identity(tmp_path: Path, name: str) -> tuple[Path, str]:
    key_path = tmp_path / name
    result = subprocess.run(
        ["age-keygen", "-o", str(key_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    # Parse the "Public key: " line specifically — age-keygen may emit extra
    # stderr lines (e.g. a file-permissions warning) around it.
    pubkey = next(
        line for line in result.stderr.splitlines() if line.startswith("Public key: ")
    ).removeprefix("Public key: ")
    return key_path, pubkey


@pytest.fixture
def identity(tmp_path):
    return _generate_identity(tmp_path, "identity.txt")


@pytest.fixture
def other_identity(tmp_path):
    return _generate_identity(tmp_path, "other-identity.txt")


def test_round_trip_reproduces_the_original_bytes_exactly(tmp_path, identity):
    key_path, pubkey = identity
    plaintext = tmp_path / "plaintext.txt"
    plaintext.write_bytes(b"synthetic test payload \x00\xff\n")
    encrypted = tmp_path / "out.age"
    decrypted = tmp_path / "back.txt"

    encrypt_file(plaintext, recipient=pubkey, output=encrypted)
    decrypt_file(encrypted, identity=key_path, output=decrypted)

    assert decrypted.read_bytes() == plaintext.read_bytes()


def test_encrypted_output_is_real_ciphertext_and_hides_the_plaintext(tmp_path, identity):
    _key_path, pubkey = identity
    plaintext = tmp_path / "plaintext.txt"
    plaintext.write_bytes(b"a synthetic secret value")
    encrypted = tmp_path / "out.age"

    encrypt_file(plaintext, recipient=pubkey, output=encrypted)

    data = encrypted.read_bytes()
    assert data.startswith(AGE_MAGIC)
    assert b"a synthetic secret value" not in data


def test_decrypt_with_wrong_identity_raises_calledprocesserror(tmp_path, identity, other_identity):
    _key_path, pubkey = identity
    other_key_path, _ = other_identity
    plaintext = tmp_path / "plaintext.txt"
    plaintext.write_bytes(b"synthetic payload")
    encrypted = tmp_path / "out.age"
    encrypt_file(plaintext, recipient=pubkey, output=encrypted)

    with pytest.raises(subprocess.CalledProcessError):
        decrypt_file(encrypted, identity=other_key_path, output=tmp_path / "back.txt")


def test_keysduty_encrypt_then_decrypt_round_trips_via_the_cli(tmp_path, identity):
    key_path, pubkey = identity
    plaintext = tmp_path / "plaintext.txt"
    plaintext.write_bytes(b"round trip via the CLI")
    encrypted = tmp_path / "out.age"
    decrypted = tmp_path / "back.txt"

    rc = main(
        ["keys", "encrypt", str(plaintext), "--recipient", pubkey, "--output", str(encrypted)]
    )
    assert rc == EXIT_OK
    assert encrypted.read_bytes().startswith(AGE_MAGIC)

    rc = main(
        ["keys", "decrypt", str(encrypted), "--identity", str(key_path), "--output", str(decrypted)]
    )
    assert rc == EXIT_OK
    assert decrypted.read_bytes() == plaintext.read_bytes()


def test_keysduty_decrypt_with_wrong_identity_projects_to_exit_failed(
    tmp_path, identity, other_identity
):
    _key_path, pubkey = identity
    other_key_path, _ = other_identity
    plaintext = tmp_path / "plaintext.txt"
    plaintext.write_bytes(b"synthetic payload")
    encrypted = tmp_path / "out.age"
    encrypt_file(plaintext, recipient=pubkey, output=encrypted)

    rc = main(
        [
            "keys", "decrypt", str(encrypted),
            "--identity", str(other_key_path),
            "--output", str(tmp_path / "back.txt"),
        ]
    )

    assert rc == EXIT_FAILED


def test_dash_sentinel_paths_are_rejected_not_silently_lost(tmp_path, identity):
    """age's `-` means stdin/stdout — under this wrapper's closed stdin and
    discarded capture it would encrypt the empty DEVNULL stream (input `-`)
    or report success while the payload vanished into the discarded capture
    (output `-`), so both primitives refuse it up front."""
    key_path, pubkey = identity
    plaintext = tmp_path / "plaintext.txt"
    plaintext.write_bytes(b"synthetic payload")

    with pytest.raises(ValueError):
        encrypt_file("-", recipient=pubkey, output=tmp_path / "out.age")
    with pytest.raises(ValueError):
        encrypt_file(plaintext, recipient=pubkey, output="-")
    with pytest.raises(ValueError):
        decrypt_file("-", identity=key_path, output=tmp_path / "back.txt")
    with pytest.raises(ValueError):
        decrypt_file(tmp_path / "out.age", identity=key_path, output="-")


def test_dash_sentinel_via_the_cli_projects_to_exit_failed(tmp_path, identity):
    _key_path, pubkey = identity
    plaintext = tmp_path / "plaintext.txt"
    plaintext.write_bytes(b"synthetic payload")

    rc = main(["keys", "encrypt", str(plaintext), "--recipient", pubkey, "--output", "-"])

    assert rc == EXIT_FAILED


def test_bare_keys_names_the_available_verbs_and_still_exits_ok(capsys):
    rc = main(["keys"])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "encrypt" in out
    assert "decrypt" in out


def test_cli_module_import_does_not_trigger_the_keys_bridge():
    """Importing `cli` must not import `keys` — keys.py refuses to load
    outside a local-recipes checkout (its `_http.py` bridge resolves at import
    time), so a top-level `cli -> keys` import would take `steward --help`/
    `--version` and every other duty down with it in an installed package.
    """
    import sys as _sys

    code = (
        "import sys; import pyforge.steward.cli; "
        "assert 'pyforge.steward.keys' not in sys.modules"
    )
    subprocess.run([_sys.executable, "-c", code], check=True, capture_output=True, text=True)
