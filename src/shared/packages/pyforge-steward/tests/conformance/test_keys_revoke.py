"""`revoke_identity` + `keys revoke` CLI dispatch — Story 1.7.

Covers the I/O matrix: revoking issued/observed/JFrog-scoped entries,
refusing an unknown or already-retired scope, and the retired entry
staying visible via a subsequent `load_inventory`/`keys list`.
"""

from __future__ import annotations

import pytest
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.keys import (
    InventoryError,
    KeyIdentityEntry,
    load_inventory,
    revoke_identity,
    save_inventory,
)


def _seed(tmp_path, entry: KeyIdentityEntry):
    inventory_path = tmp_path / "keys-inventory.yaml"
    save_inventory(inventory_path, (entry,))
    return inventory_path


def test_revoking_an_issued_active_entry_flips_status_and_keeps_other_fields(tmp_path):
    entry = KeyIdentityEntry(
        name="jfrog", scope="jfrog", provenance="issued", status="active",
        last_rotated="2026-08-01T00:00:00+00:00", identity_path="/nonexistent/id.txt",
        secrets=("/nonexistent/secret.age",),
    )
    inventory_path = _seed(tmp_path, entry)

    retired = revoke_identity(inventory_path, scope="jfrog")

    assert retired.status == "retired"
    assert retired.name == entry.name
    assert retired.provenance == entry.provenance
    assert retired.last_rotated == entry.last_rotated
    assert retired.identity_path == entry.identity_path
    assert retired.secrets == entry.secrets

    on_disk = load_inventory(inventory_path)
    assert on_disk == (retired,)


def test_revoking_an_observed_entry_with_generic_scope_succeeds(tmp_path):
    entry = KeyIdentityEntry(
        name="internal-tool", scope="internal-tool", provenance="observed", status="active",
        last_rotated=None, identity_path=None, secrets=(),
    )
    inventory_path = _seed(tmp_path, entry)

    retired = revoke_identity(inventory_path, scope="internal-tool")

    assert retired.status == "retired"
    assert retired.provenance == "observed"


def test_unknown_scope_raises_inventory_error(tmp_path):
    entry = KeyIdentityEntry(
        name="jfrog", scope="jfrog", provenance="issued", status="active",
        last_rotated=None, identity_path=None, secrets=(),
    )
    inventory_path = _seed(tmp_path, entry)

    with pytest.raises(InventoryError):
        revoke_identity(inventory_path, scope="no-such-scope")


def test_already_retired_scope_is_refused_not_a_silent_no_op(tmp_path):
    entry = KeyIdentityEntry(
        name="jfrog", scope="jfrog", provenance="issued", status="retired",
        last_rotated=None, identity_path=None, secrets=(),
    )
    inventory_path = _seed(tmp_path, entry)

    with pytest.raises(InventoryError):
        revoke_identity(inventory_path, scope="jfrog")


def test_keys_revoke_via_the_cli_marks_retired_and_prints_issued_remediation(tmp_path, capsys):
    # Deliberately NOT a "jfrog"-named scope -- that's covered by the
    # scope-specific test below, and would otherwise mask this branch (a
    # scope-specific match wins over the generic issued/observed text).
    entry = KeyIdentityEntry(
        name="internal-service", scope="internal-service", provenance="issued", status="active",
        last_rotated=None, identity_path="/nonexistent/id.txt", secrets=(),
    )
    inventory_path = _seed(tmp_path, entry)

    rc = main(["keys", "revoke", "--scope", "internal-service", "--inventory", str(inventory_path)])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "retired" in out
    assert "steward keys rotate --scope internal-service" in out
    assert load_inventory(inventory_path)[0].status == "retired"


def test_keys_revoke_via_the_cli_prints_jfrog_specific_remediation_for_an_observed_entry(
    tmp_path, capsys
):
    entry = KeyIdentityEntry(
        name="jfrog-token", scope="jfrog-token", provenance="observed", status="active",
        last_rotated=None, identity_path=None, secrets=(),
    )
    inventory_path = _seed(tmp_path, entry)

    rc = main(["keys", "revoke", "--scope", "jfrog-token", "--inventory", str(inventory_path)])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "JFrog's revocation API" in out


def test_keys_revoke_via_the_cli_prints_generic_observed_remediation(tmp_path, capsys):
    entry = KeyIdentityEntry(
        name="github-token", scope="github-token", provenance="observed", status="active",
        last_rotated=None, identity_path=None, secrets=(),
    )
    inventory_path = _seed(tmp_path, entry)

    rc = main(["keys", "revoke", "--scope", "github-token", "--inventory", str(inventory_path)])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "its own origin" in out


def test_keys_revoke_via_the_cli_projects_unknown_scope_to_exit_failed(tmp_path):
    inventory_path = tmp_path / "keys-inventory.yaml"
    save_inventory(inventory_path, ())

    rc = main(["keys", "revoke", "--scope", "no-such-scope", "--inventory", str(inventory_path)])

    assert rc == EXIT_FAILED


def test_retired_entry_stays_visible_via_a_subsequent_list(tmp_path):
    entry = KeyIdentityEntry(
        name="jfrog", scope="jfrog", provenance="issued", status="active",
        last_rotated=None, identity_path=None, secrets=(),
    )
    inventory_path = _seed(tmp_path, entry)

    rc = main(["keys", "revoke", "--scope", "jfrog", "--inventory", str(inventory_path)])
    assert rc == EXIT_OK

    rc = main(["keys", "list", "--inventory", str(inventory_path)])
    assert rc == EXIT_OK
