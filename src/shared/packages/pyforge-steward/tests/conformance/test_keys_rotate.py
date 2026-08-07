"""`rotate_identity` + `keys rotate` CLI dispatch — Story 1.4.

Covers the I/O matrix's happy-path rotation, old-identity-now-fails,
unknown-scope, observed-provenance, already-retired, dash-sentinel, and
rotate-twice rows, both at the primitive level (`rotate_identity` directly)
and through the CLI (`main(["keys", "rotate", ...])`). Test identities are
generated directly via `generate_identity`/`age-keygen` (mirrors Story 1.3's
identical precedent for `encrypt_file`/`decrypt_file` — this story's own
tests construct the pre-existing inventory entry by hand, never through a
Steward "issue" primitive, since none exists yet).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.keys import (
    InventoryError,
    KeyIdentityEntry,
    decrypt_file,
    encrypt_file,
    generate_identity,
    load_inventory,
    rotate_identity,
    save_inventory,
)


def _make_scope(tmp_path: Path, scope: str, n_secrets: int = 2) -> tuple[Path, Path]:
    """Build a fresh `issued`/`active` inventory entry for `scope`, with
    `n_secrets` files encrypted to a freshly generated identity. Returns
    (inventory_path, old_identity_path)."""
    identity_path = tmp_path / f"{scope}-identity.txt"
    pubkey = generate_identity(identity_path)

    secrets = []
    for i in range(n_secrets):
        plaintext = tmp_path / f"secret-{i}-plain.txt"
        plaintext.write_bytes(f"synthetic secret {i} for {scope}".encode())
        encrypted = tmp_path / f"secret-{i}.age"
        encrypt_file(plaintext, recipient=pubkey, output=encrypted)
        secrets.append(str(encrypted))

    inventory_path = tmp_path / "keys-inventory.yaml"
    save_inventory(
        inventory_path,
        (
            KeyIdentityEntry(
                name=scope,
                scope=scope,
                provenance="issued",
                status="active",
                last_rotated=None,
                identity_path=str(identity_path),
                secrets=tuple(secrets),
            ),
        ),
    )
    return inventory_path, identity_path


def test_happy_path_rotation_re_encrypts_every_secret_and_retires_the_old_entry(tmp_path):
    inventory_path, old_identity = _make_scope(tmp_path, "jfrog", n_secrets=2)
    new_identity_path = tmp_path / "new-identity.txt"

    new_entry = rotate_identity(inventory_path, scope="jfrog", new_identity_path=new_identity_path)

    assert new_entry.status == "active"
    assert new_entry.scope == "jfrog"
    assert new_entry.name == "jfrog-2"

    entries = load_inventory(inventory_path)
    assert len(entries) == 2
    old = next(e for e in entries if e.name == "jfrog")
    active = next(e for e in entries if e.name == "jfrog-2")
    assert old.status == "retired"
    assert active.status == "active"
    assert active.secrets == old.secrets

    for secret_path_str in active.secrets:
        out = tmp_path / f"decrypted-{Path(secret_path_str).name}"
        decrypt_file(Path(secret_path_str), identity=new_identity_path, output=out)
        assert out.read_bytes()

    del old_identity  # kept for the next test's parity with this fixture


def test_old_identity_can_no_longer_decrypt_after_rotation(tmp_path):
    inventory_path, old_identity = _make_scope(tmp_path, "jfrog", n_secrets=1)
    new_identity_path = tmp_path / "new-identity.txt"

    new_entry = rotate_identity(inventory_path, scope="jfrog", new_identity_path=new_identity_path)
    secret_path = Path(new_entry.secrets[0])

    with pytest.raises(subprocess.CalledProcessError):
        decrypt_file(secret_path, identity=old_identity, output=tmp_path / "should-not-exist.txt")


def test_unknown_scope_raises_inventory_error_and_touches_nothing(tmp_path):
    inventory_path, _old_identity = _make_scope(tmp_path, "jfrog", n_secrets=1)
    before = load_inventory(inventory_path)

    with pytest.raises(InventoryError):
        rotate_identity(inventory_path, scope="no-such-scope", new_identity_path=tmp_path / "x.txt")

    assert load_inventory(inventory_path) == before
    assert not (tmp_path / "x.txt").exists()


def test_observed_provenance_is_refused(tmp_path):
    inventory_path = tmp_path / "keys-inventory.yaml"
    save_inventory(
        inventory_path,
        (
            KeyIdentityEntry(
                name="github-token",
                scope="github-token",
                provenance="observed",
                status="active",
                last_rotated=None,
                identity_path=None,
                secrets=(),
            ),
        ),
    )

    with pytest.raises(InventoryError):
        rotate_identity(
            inventory_path, scope="github-token", new_identity_path=tmp_path / "new.txt"
        )


def test_already_retired_entry_is_refused(tmp_path):
    inventory_path = tmp_path / "keys-inventory.yaml"
    save_inventory(
        inventory_path,
        (
            KeyIdentityEntry(
                name="jfrog",
                scope="jfrog",
                provenance="issued",
                status="retired",
                last_rotated="2026-01-01T00:00:00+00:00",
                identity_path=str(tmp_path / "old.txt"),
                secrets=(),
            ),
        ),
    )

    with pytest.raises(InventoryError):
        rotate_identity(inventory_path, scope="jfrog", new_identity_path=tmp_path / "new.txt")


def test_dash_new_identity_is_rejected_before_touching_any_file(tmp_path):
    inventory_path, _old_identity = _make_scope(tmp_path, "jfrog", n_secrets=1)
    before = load_inventory(inventory_path)

    with pytest.raises(ValueError):
        rotate_identity(inventory_path, scope="jfrog", new_identity_path="-")

    assert load_inventory(inventory_path) == before


def test_rotating_twice_produces_a_third_generation_entry(tmp_path):
    inventory_path, _old_identity = _make_scope(tmp_path, "jfrog", n_secrets=1)

    rotate_identity(inventory_path, scope="jfrog", new_identity_path=tmp_path / "second.txt")
    rotate_identity(inventory_path, scope="jfrog", new_identity_path=tmp_path / "third.txt")

    entries = load_inventory(inventory_path)
    names = {e.name for e in entries}
    assert names == {"jfrog", "jfrog-2", "jfrog-3"}
    active = [e for e in entries if e.status == "active"]
    assert [e.name for e in active] == ["jfrog-3"]


def test_keys_rotate_via_the_cli_round_trips(tmp_path):
    inventory_path, _old_identity = _make_scope(tmp_path, "jfrog", n_secrets=1)
    new_identity_path = tmp_path / "new-identity.txt"

    rc = main(
        [
            "keys", "rotate",
            "--scope", "jfrog",
            "--new-identity", str(new_identity_path),
            "--inventory", str(inventory_path),
        ]
    )

    assert rc == EXIT_OK
    entries = load_inventory(inventory_path)
    assert {e.name for e in entries} == {"jfrog", "jfrog-2"}


def test_keys_rotate_via_the_cli_projects_unknown_scope_to_exit_failed(tmp_path):
    inventory_path, _old_identity = _make_scope(tmp_path, "jfrog", n_secrets=1)

    rc = main(
        [
            "keys", "rotate",
            "--scope", "no-such-scope",
            "--new-identity", str(tmp_path / "new.txt"),
            "--inventory", str(inventory_path),
        ]
    )

    assert rc == EXIT_FAILED


def test_rotate_summary_never_contains_the_public_key(tmp_path, capsys):
    inventory_path, _old_identity = _make_scope(tmp_path, "jfrog", n_secrets=1)
    new_identity_path = tmp_path / "new-identity.txt"

    rc = main(
        [
            "keys", "rotate",
            "--scope", "jfrog",
            "--new-identity", str(new_identity_path),
            "--inventory", str(inventory_path),
        ]
    )
    assert rc == EXIT_OK

    # The new identity's own public key, parsed straight from the file
    # age-keygen wrote, must never appear anywhere in stdout/stderr.
    pubkey_line = next(
        line for line in new_identity_path.read_text().splitlines()
        if line.startswith("# public key: ")
    )
    pubkey = pubkey_line.removeprefix("# public key: ")
    out = capsys.readouterr().out
    assert pubkey not in out
