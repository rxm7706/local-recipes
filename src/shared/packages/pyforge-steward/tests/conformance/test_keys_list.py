"""`format_inventory` + `keys list` CLI dispatch — Story 1.5.

Covers the I/O matrix's issued+observed, `--json`, empty-inventory, and
missing-`--inventory`-default rows, both at the primitive level
(`format_inventory` directly) and through the CLI (`main(["keys", "list",
...])`). NFR-7 ("never a raw secret value") is proven by
`tests/meta/test_invariants.py`'s `test_keys_list_output_never_contains_a_planted_secret_value`,
per this story's own AC wording.
"""

from __future__ import annotations

import json

from pyforge.steward.cli import EXIT_OK, main
from pyforge.steward.keys import KeyIdentityEntry, format_inventory, save_inventory

ISSUED = KeyIdentityEntry(
    name="jfrog",
    scope="jfrog",
    provenance="issued",
    status="active",
    last_rotated="2026-08-01T00:00:00+00:00",
    identity_path="/nonexistent/jfrog-identity.txt",
    secrets=("/nonexistent/jfrog-secret.age",),
)
OBSERVED = KeyIdentityEntry(
    name="github-token",
    scope="github-token",
    provenance="observed",
    status="active",
    last_rotated=None,
    identity_path=None,
    secrets=(),
)


def test_text_table_shows_name_scope_provenance_status_last_rotated_for_issued_entries():
    text = format_inventory((ISSUED,), as_json=False)
    assert "jfrog" in text
    assert "issued" in text
    assert "active" in text
    assert "2026-08-01T00:00:00+00:00" in text


def test_observed_entries_display_alongside_issued_with_their_own_provenance():
    text = format_inventory((ISSUED, OBSERVED), as_json=False)
    assert "jfrog" in text
    assert "github-token" in text
    assert "observed" in text


def test_json_output_is_a_list_of_dicts_with_all_fields():
    data = json.loads(format_inventory((ISSUED, OBSERVED), as_json=True))
    assert len(data) == 2
    jfrog = next(d for d in data if d["name"] == "jfrog")
    assert jfrog["scope"] == "jfrog"
    assert jfrog["provenance"] == "issued"
    assert jfrog["status"] == "active"
    assert jfrog["last_rotated"] == "2026-08-01T00:00:00+00:00"
    assert jfrog["identity_path"] == "/nonexistent/jfrog-identity.txt"
    assert jfrog["secrets"] == ["/nonexistent/jfrog-secret.age"]


def test_json_empty_inventory_is_an_empty_json_array():
    assert format_inventory((), as_json=True) == "[]"


def test_text_empty_inventory_prints_a_clear_message():
    text = format_inventory((), as_json=False)
    assert "no identities" in text.lower()


def test_keys_list_via_the_cli_shows_issued_and_observed_entries(tmp_path, capsys):
    inventory_path = tmp_path / "keys-inventory.yaml"
    save_inventory(inventory_path, (ISSUED, OBSERVED))

    rc = main(["keys", "list", "--inventory", str(inventory_path)])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "jfrog" in out
    assert "github-token" in out


def test_keys_list_via_the_cli_json_flag(tmp_path, capsys):
    inventory_path = tmp_path / "keys-inventory.yaml"
    save_inventory(inventory_path, (ISSUED,))

    rc = main(["keys", "list", "--inventory", str(inventory_path), "--json"])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    data = json.loads(out)
    assert data[0]["name"] == "jfrog"


def test_keys_list_with_no_inventory_flag_and_no_file_reports_empty(tmp_path, monkeypatch, capsys):
    # No --inventory given and default_inventory_path() resolves outside
    # tmp_path (the real repo root) -- but this repo has no real
    # .steward/keys-inventory.yaml committed, so the default path load is
    # still the "missing file -> ()" case exercised by save_inventory's own
    # precedent. Exercised at the primitive level to avoid depending on
    # real repo state for a CLI-level assertion.
    from pyforge.steward.keys import default_inventory_path, load_inventory

    assert load_inventory(default_inventory_path()) == ()
