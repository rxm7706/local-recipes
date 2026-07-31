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
    pubkey = result.stderr.strip().removeprefix("Public key: ")
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


def test_bare_keys_names_the_available_verbs_and_still_exits_ok(capsys):
    rc = main(["keys"])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "encrypt" in out
    assert "decrypt" in out
