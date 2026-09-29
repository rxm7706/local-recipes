"""Story 75.1 (CAP-164 / FR-37) -- `steward keys` and the GitHub Enterprise host.

Covers the host resolver (`enterprise_host` / `enterprise_credential` /
`resolve_headers` with a `bearer_token`), the two issued scopes, the one delivery
path (`steward keys exec`) with its approval gate and journal, the shared-payload
audit finding, and the flag `pyforge.steward.ghe_fleet_credentials` in both
states. Real `age` / `age-keygen` (as `test_keys_rotate.py` does); the probe
child writes its own environment to a file. Every host, token and reference is a
fixture -- nothing here is a real credential.
"""

from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path

import pytest

from pyforge.steward import cli as steward_cli
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main
from pyforge.steward.keys import (
    GHE_FLAG_KEY,
    GHE_PR_DRAFT_SCOPE,
    GHE_READ_SCOPE,
    GHE_SCOPES,
    HostScopedCredential,
    InventoryError,
    KeyIdentityEntry,
    encrypt_file,
    enterprise_credential,
    enterprise_host,
    find_shared_payloads,
    generate_identity,
    load_inventory,
    resolve_headers,
    save_inventory,
)

GHE_BASE = "https://ghe.example.test/api"
READ_TOKEN = "ghp_FIXTUREREADTOKEN0123456789abcdefABCDEF"
DRAFT_TOKEN = "ghp_FIXTUREDRAFTTOKEN9876543210zyxwvuZYXWVU"
AMBIENT = {
    "GITHUB_TOKEN": "ambient-github-token",
    "GH_TOKEN": "ambient-gh-token",
    "GH_ENTERPRISE_TOKEN": "ambient-gh-enterprise-token",
    "GITHUB_ENTERPRISE_TOKEN": "ambient-github-enterprise-token",
}
PROBE = "import json, os, sys; json.dump(dict(os.environ), open(sys.argv[1], 'w'))"


# --- fixtures -----------------------------------------------------------------


def _write_tree(tmp_path: Path, variant: str, name: str, *, state: str = "ENABLED") -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(
            {
                "flags": {
                    GHE_FLAG_KEY: {
                        "state": state,
                        "variants": {"on": True, "off": False},
                        "defaultVariant": variant,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch, tmp_path):
    """No ambient credential, no real netrc, the flag ON, a fixture GHE host."""
    for var in ("JFROG_API_KEY", "JFROG_USERNAME", "JFROG_PASSWORD", *AMBIENT):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NETRC", str(tmp_path / "netrc-does-not-exist"))
    monkeypatch.setenv("GITHUB_API_BASE_URL", GHE_BASE)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_write_tree(tmp_path, "on", "flags-on.json")))


@pytest.fixture
def flag_off(monkeypatch, tmp_path):
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_write_tree(tmp_path, "off", "flags-off.json")))


def _issue(tmp_path: Path, scope: str, token: str, *, payload: Path | None = None) -> KeyIdentityEntry:
    identity = tmp_path / f"{scope}-identity.txt"
    recipient = generate_identity(identity)
    plaintext = tmp_path / f"{scope}-token.txt"
    plaintext.write_text(token + "\n", encoding="utf-8")
    encrypted = payload or tmp_path / f"{scope}.age"
    encrypt_file(plaintext, recipient=recipient, output=encrypted)
    plaintext.unlink()
    return KeyIdentityEntry(
        name=scope,
        scope=scope,
        provenance="issued",
        status="active",
        last_rotated="2026-09-29T00:00:00+00:00",
        identity_path=str(identity),
        secrets=(str(encrypted),),
    )


@pytest.fixture
def inventory(tmp_path) -> Path:
    path = tmp_path / "keys-inventory.yaml"
    save_inventory(
        path,
        (_issue(tmp_path, GHE_READ_SCOPE, READ_TOKEN), _issue(tmp_path, GHE_PR_DRAFT_SCOPE, DRAFT_TOKEN)),
    )
    return path


def _exec(inventory: Path, scope: str, out: Path, *extra: str, approval: str | None = None) -> int:
    argv = ["keys", "exec", "--scope", scope, "--inventory", str(inventory)]
    if approval is not None:
        argv += ["--approval", approval]
    argv += ["--", sys.executable, "-c", PROBE, str(out), *extra]
    return main(argv)


def _child_env(out: Path) -> dict[str, str]:
    return json.loads(out.read_text(encoding="utf-8"))


# --- the credential object ---------------------------------------------------------


def test_bearer_token_is_never_in_the_repr_equality_or_hash():
    with_token = HostScopedCredential(hosts=("ghe.example.test",), bearer_token=READ_TOKEN)
    without = HostScopedCredential(hosts=("ghe.example.test",))
    assert READ_TOKEN not in repr(with_token)
    assert with_token == without
    assert hash(with_token) == hash(without)


@pytest.mark.parametrize(
    "bad",
    ["", "two words", "line\nbreak", "tab\there", "\x00nul", "ghp_\x7fdel", "gh\u00e9p_non_ascii"],
    ids=["empty", "space", "newline", "tab", "nul", "del", "non-ascii"],
)
def test_a_malformed_bearer_token_is_refused_without_echoing_it(bad):
    with pytest.raises(ValueError) as excinfo:
        HostScopedCredential(hosts=("ghe.example.test",), bearer_token=bad)
    message = str(excinfo.value)
    assert repr(bad) not in message
    if bad:
        assert bad not in message


def test_a_non_string_bearer_token_is_refused():
    with pytest.raises(TypeError):
        HostScopedCredential(hosts=("ghe.example.test",), bearer_token=12345)  # type: ignore[arg-type]


# --- the resolver matrix ----------------------------------------------------------


def test_the_enterprise_identity_attaches_only_to_the_enterprise_host(inventory):
    credential = enterprise_credential(inventory)
    assert credential is not None and credential.hosts == ("ghe.example.test",)
    assert resolve_headers(credential, "https://ghe.example.test/api/v3/repos/o/r") == {
        "Authorization": f"Bearer {READ_TOKEN}"
    }
    for other in (
        "https://api.github.com/repos/o/r",
        "https://github.com/o/r",
        "https://other.test/x",
        "https://evil-ghe.example.test/x",
        "https://ghe.example.test.evil.test/x",
        "https://xghe.example.test/x",
        "not-a-url",
    ):
        assert resolve_headers(credential, other) == {}, other


def test_the_enterprise_host_match_is_canonical(inventory):
    credential = enterprise_credential(inventory)
    assert credential is not None
    for same in ("https://GHE.Example.Test:8443/x", "https://ghe.example.test./x"):
        assert resolve_headers(credential, same) == {"Authorization": f"Bearer {READ_TOKEN}"}, same


def test_the_enterprise_credential_ignores_an_ambient_github_token(inventory, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", AMBIENT["GITHUB_TOKEN"])
    credential = enterprise_credential(inventory)
    assert credential is not None
    assert resolve_headers(credential, "https://ghe.example.test/x") == {"Authorization": f"Bearer {READ_TOKEN}"}
    assert resolve_headers(credential, "https://api.github.com/x") == {}


def test_without_a_base_url_no_enterprise_identity_resolves(inventory, monkeypatch):
    monkeypatch.delenv("GITHUB_API_BASE_URL")
    assert enterprise_host() is None
    assert enterprise_credential(inventory) is None


@pytest.mark.parametrize("base", ["https://api.github.com", "https://github.com/", "  ", "https://API.GitHub.com/"])
def test_a_public_github_base_url_names_no_enterprise_host(inventory, monkeypatch, base):
    monkeypatch.setenv("GITHUB_API_BASE_URL", base)
    assert enterprise_host() is None
    assert enterprise_credential(inventory) is None


def test_the_enterprise_host_is_the_hostname_of_the_base_url(monkeypatch):
    monkeypatch.setenv("GITHUB_API_BASE_URL", "https://GHE.Example.Test:8443/api/")
    assert enterprise_host() == "ghe.example.test"


def test_a_scope_with_no_issued_row_resolves_nothing(tmp_path):
    empty = tmp_path / "empty-inventory.yaml"
    save_inventory(empty, ())
    assert enterprise_credential(empty) is None


def test_the_draft_scope_never_resolves_in_process(inventory):
    with pytest.raises(ValueError, match="keys exec"):
        enterprise_credential(inventory, GHE_PR_DRAFT_SCOPE)


def test_flag_off_resolves_no_enterprise_host(inventory, flag_off):
    assert enterprise_host() is None
    assert enterprise_credential(inventory) is None


def test_an_absent_flag_tree_resolves_no_enterprise_host(inventory, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tmp_path / "missing.json"))
    monkeypatch.chdir(tmp_path)  # no src/platform/config/flags.json above tmp_path
    assert enterprise_host() is None
    assert GHE_FLAG_KEY in capsys.readouterr().err  # the named WARN


def test_a_shared_payload_refuses_the_read_credential(tmp_path):
    shared = tmp_path / "one.age"
    inventory = tmp_path / "shared-inventory.yaml"
    read = _issue(tmp_path, GHE_READ_SCOPE, READ_TOKEN, payload=shared)
    draft = KeyIdentityEntry(
        name=GHE_PR_DRAFT_SCOPE,
        scope=GHE_PR_DRAFT_SCOPE,
        provenance="issued",
        status="active",
        last_rotated=None,
        identity_path=read.identity_path,
        secrets=read.secrets,
    )
    save_inventory(inventory, (read, draft))
    with pytest.raises(InventoryError, match="share the payload"):
        enterprise_credential(inventory)


# --- keys exec: the read scope -----------------------------------------------------


def test_exec_read_gives_the_child_the_read_token_and_no_ambient_token(inventory, tmp_path, monkeypatch, capsys):
    for var, value in AMBIENT.items():
        monkeypatch.setenv(var, value)
    monkeypatch.setenv("GH_HOST", "github.com")
    out = tmp_path / "child-env.json"

    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_OK

    env = _child_env(out)
    assert env["GH_HOST"] == "ghe.example.test"
    assert env["GH_ENTERPRISE_TOKEN"] == READ_TOKEN
    for var in ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        assert var not in env, var
    assert not any(value in env.values() for value in AMBIENT.values())
    assert env["PATH"] == os.environ["PATH"], "the rest of the parent's environment is kept"
    # the token is on no argv (the probe's argv is python -c <script> <out>), no stream
    captured = capsys.readouterr()
    assert READ_TOKEN not in captured.out + captured.err


def test_exec_read_never_yields_the_draft_token(inventory, tmp_path):
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_OK
    assert DRAFT_TOKEN not in json.dumps(_child_env(out))


def test_exec_read_writes_no_journal_line(inventory, tmp_path):
    assert _exec(inventory, GHE_READ_SCOPE, tmp_path / "child-env.json") == EXIT_OK
    assert not (inventory.parent / "keys-exec.log").exists()


def test_exec_returns_the_childs_exit_code(inventory, tmp_path):
    argv = ["keys", "exec", "--scope", GHE_READ_SCOPE, "--inventory", str(inventory), "--"]
    assert main([*argv, sys.executable, "-c", "import sys; sys.exit(3)"]) == 3
    assert main([*argv, sys.executable, "-c", "pass"]) == EXIT_OK


def test_exec_maps_a_signal_death_to_128_plus_n(inventory):
    script = "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"
    argv = [
        "keys",
        "exec",
        "--scope",
        GHE_READ_SCOPE,
        "--inventory",
        str(inventory),
        "--",
        sys.executable,
        "-c",
        script,
    ]
    assert main(argv) == 128 + signal.SIGTERM


def test_exec_relays_the_childs_streams_with_the_token_redacted(inventory, capsys):
    script = (
        "import os, sys; t = os.environ['GH_ENTERPRISE_TOKEN']; print('out:' + t); print('err:' + t, file=sys.stderr)"
    )
    argv = [
        "keys",
        "exec",
        "--scope",
        GHE_READ_SCOPE,
        "--inventory",
        str(inventory),
        "--",
        sys.executable,
        "-c",
        script,
    ]
    assert main(argv) == EXIT_OK
    captured = capsys.readouterr()
    assert captured.out == "out:***\n"
    assert captured.err == "err:***\n"


def test_exec_with_no_command_exits_2_and_starts_nothing(inventory, capsys):
    """With or without a bare `--`, no command means exit 2 before any token is read."""
    assert main(["keys", "exec", "--scope", GHE_READ_SCOPE, "--inventory", str(inventory)]) == EXIT_USAGE
    assert main(["keys", "exec", "--scope", GHE_READ_SCOPE, "--inventory", str(inventory), "--"]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert err.count("no command given") == 2
    assert READ_TOKEN not in err


def test_exec_reports_a_child_that_cannot_launch(inventory, capsys):
    argv = ["keys", "exec", "--scope", GHE_READ_SCOPE, "--inventory", str(inventory), "--", "no-such-binary-xyz-75"]
    assert main(argv) == EXIT_FAILED
    err = capsys.readouterr().err
    assert "keys exec" in err and READ_TOKEN not in err


def test_exec_refuses_an_unknown_scope_at_the_parser(inventory, capsys):
    argv = ["keys", "exec", "--scope", "jfrog", "--inventory", str(inventory), "--", "true"]
    assert main(argv) == EXIT_USAGE
    assert "invalid choice" in capsys.readouterr().err


def test_exec_has_no_flag_that_takes_a_secret():
    exec_parser = steward_cli.build_parser()._subparsers._group_actions[0].choices["keys"]  # type: ignore[union-attr]
    exec_parser = exec_parser._subparsers._group_actions[0].choices["exec"]  # type: ignore[union-attr]
    flags = {opt for action in exec_parser._actions for opt in action.option_strings}
    assert flags == {"-h", "--help", "--scope", "--approval", "--inventory"}


# --- keys exec: the draft scope, the approval gate, the journal --------------------


def test_exec_draft_without_approval_exits_2_and_the_probe_never_starts(inventory, tmp_path, capsys):
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_PR_DRAFT_SCOPE, out) == EXIT_USAGE
    assert not out.exists()
    assert not (inventory.parent / "keys-exec.log").exists()
    assert "--approval" in capsys.readouterr().err


@pytest.mark.parametrize("blank", ["", "   "])
def test_exec_draft_with_an_empty_approval_is_refused(inventory, tmp_path, blank):
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_PR_DRAFT_SCOPE, out, approval=blank) == EXIT_USAGE
    assert not out.exists()


def test_exec_draft_with_an_approval_runs_and_journals_without_the_token(inventory, tmp_path, capsys):
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_PR_DRAFT_SCOPE, out, approval="PROP-7") == EXIT_OK

    env = _child_env(out)
    assert env["GH_ENTERPRISE_TOKEN"] == DRAFT_TOKEN
    assert env["GH_HOST"] == "ghe.example.test"
    assert READ_TOKEN not in json.dumps(env)

    journal = (inventory.parent / "keys-exec.log").read_text(encoding="utf-8")
    lines = journal.splitlines()
    assert len(lines) == 1
    assert "PROP-7" in lines[0]
    assert f"scope={GHE_PR_DRAFT_SCOPE}" in lines[0]
    assert sys.executable in lines[0]
    assert lines[0].split(" ", 1)[0].endswith("+00:00"), "a UTC timestamp leads the line"
    assert DRAFT_TOKEN not in journal and READ_TOKEN not in journal
    captured = capsys.readouterr()
    assert DRAFT_TOKEN not in captured.out + captured.err


def test_each_approved_draft_run_appends_one_line(inventory, tmp_path):
    for ref in ("PROP-7", "PROP-8"):
        assert _exec(inventory, GHE_PR_DRAFT_SCOPE, tmp_path / f"env-{ref}.json", approval=ref) == EXIT_OK
    lines = (inventory.parent / "keys-exec.log").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and "PROP-7" in lines[0] and "PROP-8" in lines[1]


@pytest.mark.parametrize("separator", ["\n", "\r", "\u2028", "\u2029", "\u0085"], ids=repr)
def test_an_approval_with_a_newline_cannot_forge_a_second_journal_line(inventory, tmp_path, separator):
    """Every character `str.splitlines` splits on (not only `\\n`) is escaped in the journal."""
    forged = f'PROP-7{separator}2026-01-01T00:00:00+00:00 scope=ghe-fleet-pr-draft approval="FORGED" argv0="x"'
    assert _exec(inventory, GHE_PR_DRAFT_SCOPE, tmp_path / "child-env.json", approval=forged) == EXIT_OK
    journal = (inventory.parent / "keys-exec.log").read_bytes().decode("utf-8")
    assert len(journal.splitlines()) == 1
    assert journal.endswith("\n") and separator not in journal.removesuffix("\n")


def test_a_journal_that_cannot_be_written_refuses_to_run(inventory, tmp_path, capsys):
    (inventory.parent / "keys-exec.log").mkdir()  # a directory where the journal file must go
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_PR_DRAFT_SCOPE, out, approval="PROP-7") == EXIT_FAILED
    assert not out.exists()
    assert "cannot journal" in capsys.readouterr().err


# --- keys exec: what makes the child never start ------------------------------------


def test_exec_with_an_identity_that_cannot_decrypt_exits_1_and_the_child_never_starts(inventory, tmp_path, capsys):
    other_identity = tmp_path / "other-identity.txt"
    generate_identity(other_identity)
    entries = tuple(
        KeyIdentityEntry(**{**vars(e), "identity_path": str(other_identity)}) if e.scope == GHE_READ_SCOPE else e
        for e in load_inventory(inventory)
    )
    save_inventory(inventory, entries)
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_FAILED
    assert not out.exists()
    assert "keys exec: age exited" in capsys.readouterr().err


def test_exec_with_a_missing_identity_file_exits_1(inventory, tmp_path):
    entries = tuple(
        KeyIdentityEntry(**{**vars(e), "identity_path": str(tmp_path / "gone.txt")}) for e in load_inventory(inventory)
    )
    save_inventory(inventory, entries)
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_FAILED
    assert not out.exists()


def test_exec_with_no_issued_row_exits_1_naming_the_scope(tmp_path, capsys):
    empty = tmp_path / "empty-inventory.yaml"
    save_inventory(empty, ())
    assert _exec(empty, GHE_READ_SCOPE, tmp_path / "child-env.json") == EXIT_FAILED
    assert GHE_READ_SCOPE in capsys.readouterr().err


def test_exec_with_no_enterprise_host_exits_1(inventory, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_API_BASE_URL")
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_FAILED
    assert not out.exists()
    assert "GITHUB_API_BASE_URL" in capsys.readouterr().err


def test_exec_refuses_while_both_scopes_share_a_payload(tmp_path, capsys):
    shared = tmp_path / "one.age"
    read = _issue(tmp_path, GHE_READ_SCOPE, READ_TOKEN, payload=shared)
    draft = KeyIdentityEntry(**{**vars(read), "name": GHE_PR_DRAFT_SCOPE, "scope": GHE_PR_DRAFT_SCOPE})
    inventory = tmp_path / "keys-inventory.yaml"
    save_inventory(inventory, (read, draft))
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_FAILED
    assert not out.exists(), "the read scope must never hand out the draft-capable payload"
    assert "share the payload" in capsys.readouterr().err


@pytest.mark.parametrize(
    "content",
    ["", "two words\n", "line1\nline2\n", "ghp_\x7fdel\n", "gh\u00e9p_non_ascii\n"],
    ids=["empty", "space", "two-lines", "del", "non-ascii"],
)
def test_exec_refuses_a_payload_that_is_not_one_token(tmp_path, capsys, content):
    identity = tmp_path / "id.txt"
    recipient = generate_identity(identity)
    plain = tmp_path / "plain.txt"
    plain.write_text(content, encoding="utf-8")
    payload = tmp_path / "read.age"
    encrypt_file(plain, recipient=recipient, output=payload)
    inventory = tmp_path / "keys-inventory.yaml"
    save_inventory(
        inventory,
        (
            KeyIdentityEntry(
                name=GHE_READ_SCOPE,
                scope=GHE_READ_SCOPE,
                provenance="issued",
                status="active",
                last_rotated=None,
                identity_path=str(identity),
                secrets=(str(payload),),
            ),
        ),
    )
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_FAILED
    assert not out.exists()
    err = capsys.readouterr().err
    assert "exactly one token" in err
    if content.strip():
        assert content.strip() not in err


# --- the audit finding, list, rotate ------------------------------------------------


def _shared_inventory(tmp_path: Path) -> Path:
    read = _issue(tmp_path, GHE_READ_SCOPE, READ_TOKEN, payload=tmp_path / "one.age")
    draft = KeyIdentityEntry(**{**vars(read), "name": GHE_PR_DRAFT_SCOPE, "scope": GHE_PR_DRAFT_SCOPE})
    inventory = tmp_path / "shared-inventory.yaml"
    save_inventory(inventory, (read, draft))
    return inventory


def test_audit_reports_one_payload_serving_both_scopes_and_exits_1(tmp_path, capsys):
    inventory = _shared_inventory(tmp_path)
    assert main(["keys", "audit", "--inventory", str(inventory)]) == EXIT_FAILED
    err = capsys.readouterr().err
    assert "[inventory]" in err and "share the payload" in err
    assert READ_TOKEN not in err


def test_audit_compares_resolved_paths(tmp_path):
    read = _issue(tmp_path, GHE_READ_SCOPE, READ_TOKEN, payload=tmp_path / "one.age")
    alias = tmp_path / "alias.age"
    alias.symlink_to(tmp_path / "one.age")
    draft = KeyIdentityEntry(
        **{**vars(read), "name": GHE_PR_DRAFT_SCOPE, "scope": GHE_PR_DRAFT_SCOPE, "secrets": (str(alias),)}
    )
    assert len(find_shared_payloads((read, draft))) == 1


def test_audit_ignores_retired_and_observed_rows(tmp_path):
    read = _issue(tmp_path, GHE_READ_SCOPE, READ_TOKEN, payload=tmp_path / "one.age")
    retired = KeyIdentityEntry(
        **{**vars(read), "name": "old", "scope": GHE_PR_DRAFT_SCOPE, "status": "retired"},
    )
    observed = KeyIdentityEntry(
        **{**vars(read), "name": "obs", "scope": GHE_PR_DRAFT_SCOPE, "provenance": "observed"},
    )
    assert find_shared_payloads((read, retired, observed)) == []


def test_audit_over_two_separate_payloads_is_clean(inventory, capsys):
    assert main(["keys", "audit", "--inventory", str(inventory)]) == EXIT_OK
    out = capsys.readouterr().out
    assert out.strip() == f"[inventory] clean: {inventory}"


def test_audit_without_inventory_flag_keeps_its_old_output(capsys):
    """Flag-less `keys audit` over the repo's own inventory: unchanged degrade message."""
    assert main(["keys", "audit"]) == EXIT_OK
    assert capsys.readouterr().out.strip() == "keys audit: pass --drift and/or --secrets <path>"


def test_audit_with_a_malformed_inventory_fails_naming_it(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a list\n", encoding="utf-8")
    assert main(["keys", "audit", "--inventory", str(bad)]) == EXIT_FAILED
    assert "[inventory]" in capsys.readouterr().err


def test_list_and_audit_print_no_secret_value(inventory, capsys):
    assert main(["keys", "list", "--inventory", str(inventory)]) == EXIT_OK
    assert main(["keys", "list", "--json", "--inventory", str(inventory)]) == EXIT_OK
    assert main(["keys", "audit", "--inventory", str(inventory)]) == EXIT_OK
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert GHE_READ_SCOPE in text and GHE_PR_DRAFT_SCOPE in text, "both rows are shown"
    assert READ_TOKEN not in text and DRAFT_TOKEN not in text


def test_rotate_re_encrypts_each_scopes_payload_and_exec_still_delivers(inventory, tmp_path):
    old_identities = {e.scope: e.identity_path for e in load_inventory(inventory)}
    for scope in GHE_SCOPES:
        new_identity = tmp_path / f"{scope}-rotated-identity.txt"
        assert (
            main(
                ["keys", "rotate", "--scope", scope, "--new-identity", str(new_identity), "--inventory", str(inventory)]
            )
            == EXIT_OK
        )

    read_out, draft_out = tmp_path / "read.json", tmp_path / "draft.json"
    assert _exec(inventory, GHE_READ_SCOPE, read_out) == EXIT_OK
    assert _exec(inventory, GHE_PR_DRAFT_SCOPE, draft_out, approval="PROP-7") == EXIT_OK
    assert _child_env(read_out)["GH_ENTERPRISE_TOKEN"] == READ_TOKEN
    assert _child_env(draft_out)["GH_ENTERPRISE_TOKEN"] == DRAFT_TOKEN

    active = {e.scope: e for e in load_inventory(inventory) if e.status == "active"}
    for scope in GHE_SCOPES:
        assert active[scope].identity_path != old_identities[scope]
        assert active[scope].identity_path.endswith(f"{scope}-rotated-identity.txt")


# --- the flag, in both states ----------------------------------------------------------


def test_flag_on_lists_exec_without_the_disabled_marker(capsys):
    with pytest.raises(SystemExit):
        steward_cli.build_parser().parse_args(["keys", "--help"])
    out = capsys.readouterr().out
    assert "exec" in out
    assert "[disabled" not in out.replace("\n", " ")


def test_flag_off_lists_exec_as_disabled_and_exec_exits_2(inventory, tmp_path, flag_off, capsys):
    with pytest.raises(SystemExit):
        steward_cli.build_parser().parse_args(["keys", "--help"])
    listing = " ".join(capsys.readouterr().out.split())
    assert "exec" in listing
    assert f"[disabled: flag {GHE_FLAG_KEY} is off]" in listing

    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_USAGE
    assert not out.exists()
    assert f"flag {GHE_FLAG_KEY} is off" in capsys.readouterr().err


def test_flag_off_refuses_the_draft_scope_too(inventory, tmp_path, flag_off):
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_PR_DRAFT_SCOPE, out, approval="PROP-7") == EXIT_USAGE
    assert not out.exists()
    assert not (inventory.parent / "keys-exec.log").exists()


def test_an_unreadable_flag_tree_reads_off_and_exec_exits_2_with_a_named_warn(inventory, tmp_path, monkeypatch, capsys):
    broken = tmp_path / "broken.json"
    broken.write_text("{nope", encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(broken))
    assert _exec(inventory, GHE_READ_SCOPE, tmp_path / "child-env.json") == EXIT_USAGE
    err = capsys.readouterr().err
    assert "WARN" in err and GHE_FLAG_KEY in err


def test_state_disabled_is_the_kill_switch(inventory, tmp_path, monkeypatch):
    path = tmp_path / "killed.json"
    path.write_text(
        json.dumps(
            {
                "flags": {
                    GHE_FLAG_KEY: {"state": "DISABLED", "variants": {"on": True, "off": False}, "defaultVariant": "on"}
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(path))
    assert enterprise_host() is None
    assert _exec(inventory, GHE_READ_SCOPE, tmp_path / "child-env.json") == EXIT_USAGE


def test_the_tracked_tree_carries_the_flag_off_by_default():
    tree = Path(__file__).resolve().parents[5] / "platform" / "config" / "flags.json"
    entry = json.loads(tree.read_text(encoding="utf-8"))["flags"][GHE_FLAG_KEY]
    assert entry["variants"] == {"on": True, "off": False}
    assert entry["defaultVariant"] == "off"
    assert entry["state"] == "ENABLED"


# --- pins between cli.py and keys.py ----------------------------------------------------


def test_the_cli_literals_equal_the_keys_constants():
    assert steward_cli._KEYS_EXEC_FLAG == GHE_FLAG_KEY
    assert steward_cli._KEYS_EXEC_SCOPES == GHE_SCOPES


def test_exec_is_a_registered_keys_verb():
    from pyforge.steward.keys import _KEYS_VERBS

    assert _KEYS_VERBS == ("encrypt", "decrypt", "rotate", "list", "audit", "revoke", "exec")
    assert main(["keys"]) == EXIT_OK  # bare `keys` names the verbs and still succeeds


# --- keys exec: rows that cannot name exactly one payload ------------------------------


def _rewrite_read_row(inventory: Path, **changes: object) -> None:
    entries = tuple(
        KeyIdentityEntry(**{**vars(e), **changes}) if e.scope == GHE_READ_SCOPE else e
        for e in load_inventory(inventory)
    )
    save_inventory(inventory, entries)


def _duplicate_read_row(inventory: Path) -> None:
    entries = load_inventory(inventory)
    read = next(e for e in entries if e.scope == GHE_READ_SCOPE)
    save_inventory(inventory, (*entries, KeyIdentityEntry(**{**vars(read), "name": "ghe-fleet-read-dup"})))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"identity_path": None}, "no identity_path"),
        ({"secrets": ()}, "0 payloads"),
        ({"secrets": ("one.age", "two.age")}, "2 payloads"),
    ],
    ids=["no-identity-path", "no-payload", "two-payloads"],
)
def test_exec_refuses_a_row_that_does_not_name_exactly_one_payload(inventory, tmp_path, capsys, changes, message):
    _rewrite_read_row(inventory, **changes)
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_FAILED
    assert not out.exists(), "the child must never start"
    err = capsys.readouterr().err
    assert "keys exec:" in err and message in err
    assert READ_TOKEN not in err


def test_exec_refuses_two_issued_active_rows_for_one_scope(inventory, tmp_path, capsys):
    _duplicate_read_row(inventory)
    out = tmp_path / "child-env.json"
    assert _exec(inventory, GHE_READ_SCOPE, out) == EXIT_FAILED
    assert not out.exists(), "an ambiguous inventory is never resolved by picking the first row"
    err = capsys.readouterr().err
    assert "2 issued/active identities" in err and READ_TOKEN not in err


def test_enterprise_credential_raises_for_two_issued_active_rows(inventory):
    _duplicate_read_row(inventory)
    with pytest.raises(InventoryError, match="2 issued/active identities"):
        enterprise_credential(inventory)


# --- keys exec: the default journal location ---------------------------------------------


def test_the_default_journal_lands_beside_the_default_inventory(inventory, tmp_path, monkeypatch):
    steward_dir = tmp_path / "default-root" / ".steward"
    steward_dir.mkdir(parents=True)
    default_inventory = steward_dir / "keys-inventory.yaml"
    default_inventory.write_bytes(inventory.read_bytes())
    monkeypatch.setattr("pyforge.steward.keys.default_inventory_path", lambda: default_inventory)

    out = tmp_path / "child-env.json"
    argv = [
        "keys",
        "exec",
        "--scope",
        GHE_PR_DRAFT_SCOPE,
        "--approval",
        "PROP-9",
        "--",
        sys.executable,
        "-c",
        PROBE,
        str(out),
    ]
    assert main(argv) == EXIT_OK

    assert _child_env(out)["GH_ENTERPRISE_TOKEN"] == DRAFT_TOKEN
    journal = (steward_dir / "keys-exec.log").read_text(encoding="utf-8")
    assert len(journal.splitlines()) == 1 and "PROP-9" in journal
    assert DRAFT_TOKEN not in journal and READ_TOKEN not in journal
    assert not (inventory.parent / "keys-exec.log").exists(), "only the default inventory's directory is written"


# --- the resolver composed with the credential, across the states ------------------------


def _enterprise_headers(inventory: Path, url: str) -> dict[str, str]:
    """`enterprise_credential` composed with `resolve_headers`; no credential is no header."""
    credential = enterprise_credential(inventory)
    return {} if credential is None else resolve_headers(credential, url)


def test_enterprise_credential_composed_with_resolve_headers_across_the_states(inventory, tmp_path, monkeypatch):
    enterprise_url = "https://ghe.example.test/api/v3/repos/o/r"
    urls = (enterprise_url, "https://other.test/x", "https://api.github.com/x")

    # flag ON, GITHUB_API_BASE_URL set: a Bearer header for the enterprise URL, nothing elsewhere
    assert _enterprise_headers(inventory, enterprise_url) == {"Authorization": f"Bearer {READ_TOKEN}"}
    assert _enterprise_headers(inventory, "https://other.test/x") == {}

    # GITHUB_API_BASE_URL unset
    with monkeypatch.context() as unset:
        unset.delenv("GITHUB_API_BASE_URL")
        assert enterprise_credential(inventory) is None
        assert [_enterprise_headers(inventory, url) for url in urls] == [{}, {}, {}]

    # flag OFF, and the kill switch (state DISABLED wins over an `on` default)
    for state, variant in (("ENABLED", "off"), ("DISABLED", "on")):
        with monkeypatch.context() as patched:
            tree = _write_tree(tmp_path, variant, f"flags-{state}-{variant}.json", state=state)
            patched.setenv("PYFORGE_FLAGS_PATH", str(tree))
            assert enterprise_credential(inventory) is None, state
            assert [_enterprise_headers(inventory, url) for url in urls] == [{}, {}, {}], state


# --- keys audit: a broken inventory is a finding, never an early return -------------------

_PLANTED_SECRET = "AGE-SECRET-KEY-1" + "A" * 24


@pytest.mark.parametrize(
    "content",
    ["- just\n- a list\n", "identities: [unclosed\n", "a: b: c\n"],
    ids=["not-a-mapping", "yaml-parser-error", "yaml-scanner-error"],
)
def test_audit_with_a_broken_inventory_reports_it_and_still_scans_for_secrets(tmp_path, capsys, content):
    bad = tmp_path / "bad.yaml"
    bad.write_text(content, encoding="utf-8")
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / "leak.txt").write_text(_PLANTED_SECRET + "\n", encoding="utf-8")

    assert main(["keys", "audit", "--inventory", str(bad), "--secrets", str(scan)]) == EXIT_FAILED

    err = capsys.readouterr().err
    assert err.count("[inventory]") == 1
    assert "[secrets]" in err and "leak.txt" in err
    assert _PLANTED_SECRET not in err


def test_audit_with_a_broken_inventory_still_runs_the_drift_scan(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("identities: [unclosed\n", encoding="utf-8")
    clean = tmp_path / "clean.py"
    clean.write_text("x = 1\n", encoding="utf-8")
    assert main(["keys", "audit", "--inventory", str(bad), "--drift", "--path", str(clean)]) == EXIT_FAILED
    err = capsys.readouterr().err
    assert "[inventory]" in err and f"[drift] clean: {clean}" in err


def test_a_bare_audit_with_a_broken_default_inventory_reports_the_finding(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("identities: [unclosed\n", encoding="utf-8")
    monkeypatch.setattr("pyforge.steward.keys.default_inventory_path", lambda: bad)
    assert main(["keys", "audit"]) == EXIT_FAILED
    err = capsys.readouterr().err
    assert "[inventory]" in err and "pass --drift" not in err
