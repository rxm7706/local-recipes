"""Story 11.2: reliability of the CLI-triggered equivalents to the
original Epic 11 AC's webhook-retry/cron/gate-check/operator-alert
machinery -- none of which exists in this architecture (see
``docs/dreams/herald-moments-2-4-live-backend.md``). What DOES apply here:

* the operator-role write gate (AD-16) is enforced *consistently* across
  every one of the SIX write commands that exist now that all three
  Moments are real -- not spot-checked one at a time per module (each
  module's own test file already does that; this file is the cross-cutting
  view over all six at once, plus a structural guard against a future
  write command silently forgetting the gate).
* graceful (non-raising) behavior when a Moment's local storage is
  completely absent -- no ``.herald/`` directory at all, not even an empty
  one -- for the two read paths the story names explicitly
  (``success validate --all``, ``notice list``). Storage-module-level
  coverage of this already exists per-module (``test_claims.py``,
  ``test_notices.py``) -- verified, not just assumed, before this file was
  written; this adds the *CLI-level* case (through ``cli.main``, on a
  freshly-``chdir``'d empty ``tmp_path``) since the per-module tests never
  went through the CLI dispatch layer at all.

Progress's own write-idempotency (upsert, not duplicate, on a second
same-day ``--update``) is already covered end to end by Story 8.1's
storage-level tests (``test_progress.py``) and Story 8.3's CLI-level test
(``test_cli_progress.py::test_update_a_second_time_same_day_replaces_not_appends``)
-- deliberately not duplicated here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.herald import auth, cli

_CLI_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "pyforge" / "herald" / "cli.py"
).read_text(encoding="utf-8")


def test_exactly_six_write_gate_call_sites_exist_in_cli():
    """A structural guard, not a behavioral one: counts
    ``auth.require_operator_role(`` call sites in ``cli.py``'s source.

    This is deliberately brittle -- if a Moment 5 write command is ever
    added, this count must be bumped in the same change that wires the new
    handler, forcing a conscious decision about whether the new command is
    gated (rather than a reviewer having to notice a missing gate call by
    reading the whole diff). Today: ``progress --update``, ``success
    publish``, ``notice author``, ``notice publish``, ``notice close``,
    ``notice archive`` -- six, one per write command that exists."""
    assert _CLI_SOURCE.count("auth.require_operator_role(") == 6


# Every write command, as the minimal ``cli.main`` argv that reaches its
# handler's own gate check (each handler calls the gate before touching any
# storage or other args, so a nonexistent claim id / component name never
# matters -- the refusal happens first).
_WRITE_COMMANDS = {
    "progress --update": [
        "progress",
        "warden",
        "--update",
        "--unblock-narrative",
        "n",
    ],
    "success publish": ["success", "--repo-root", "{repo_root}", "publish", "no-id"],
    "notice author": ["notice", "author"],
    "notice publish": ["notice", "publish", "no-component"],
    "notice close": ["notice", "close", "no-component"],
    "notice archive": ["notice", "archive", "--rename", "old", "new"],
}


@pytest.mark.parametrize("command_name", list(_WRITE_COMMANDS))
def test_write_command_refuses_without_operator_role(
    command_name, monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "viewer:tok")
    argv = [
        a.replace("{repo_root}", str(tmp_path)) for a in _WRITE_COMMANDS[command_name]
    ]
    rc = cli.main(argv)
    assert rc == 1, f"{command_name} did not refuse a non-operator role"
    assert "unauthorized" in capsys.readouterr().err


@pytest.mark.parametrize("command_name", list(_WRITE_COMMANDS))
def test_write_command_refuses_with_no_auth_context_at_all(
    command_name, monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    argv = [
        a.replace("{repo_root}", str(tmp_path)) for a in _WRITE_COMMANDS[command_name]
    ]
    rc = cli.main(argv)
    assert rc == 1, f"{command_name} did not refuse a missing auth context"
    assert "auth context missing" in capsys.readouterr().err


# --- graceful behavior on completely absent local storage -----------------


def test_notice_list_on_a_freshly_chdird_empty_repo(monkeypatch, tmp_path, capsys):
    """No ``.herald/notices-index.json``, no ``notices/`` tree -- nothing
    has ever been authored in this ``tmp_path``."""
    monkeypatch.chdir(tmp_path)
    assert cli.main(["notice", "list"]) == 0
    assert "no notices found" in capsys.readouterr().out

    assert cli.main(["notice", "--json", "list"]) == 0
    assert json.loads(capsys.readouterr().out.strip()) == []


def test_success_validate_all_on_a_freshly_chdird_empty_repo(tmp_path, capsys):
    """No ``.herald/claims.json`` at all -- zero claims to re-validate."""
    rc = cli.main(["success", "--repo-root", str(tmp_path), "validate", "--all"])
    assert rc == 0
    assert "revalidated evidence for 0 claim(s)" in capsys.readouterr().out
