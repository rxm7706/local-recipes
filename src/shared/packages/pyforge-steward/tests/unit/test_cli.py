"""Story 1.1 — dispatcher behaviour and exit-code ownership (AD-8)."""

from __future__ import annotations

import pytest

from pyforge.steward import __version__
from pyforge.steward.cli import (
    _HELP,
    DUTIES,
    EXIT_FAILED,
    EXIT_INTERNAL,
    EXIT_INTERRUPTED,
    EXIT_OK,
    EXIT_USAGE,
    build_parser,
    main,
)
from pyforge.steward.interfaces import DutyResult
from pyforge.core.flags import FlagOff


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_help_lists_all_duties(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    out = capsys.readouterr().out
    for duty in DUTIES:
        assert duty in out


def test_there_are_exactly_twenty_five_duties():
    assert DUTIES == (
        "keys",
        "deploy",
        "provision",
        "budget",
        "sync",
        "workspace",
        "upgrade",
        "suite",
        "init",
        "shell-init",
        "setup",
        "initrepo",
        "validate-fast",
        "restore",
        "revoke",
        "track",
        "guards",
        "cutover",
        "ledger-query",
        "catalog",
        "load",
        "passport",
        "glass",
        "session",
        "deck-drift",
    )


def test_init_and_shell_init_are_wired_into_help():
    """Story 17.1 AC: bootstrap verbs are registered duties."""
    assert "init" in DUTIES
    assert "shell-init" in DUTIES
    assert "init" in _HELP
    assert "shell-init" in _HELP


def test_suite_is_wired_into_help():
    """Story 15.1 AC: `suite` is an eighth duty."""
    assert "suite" in DUTIES
    assert "suite" in _HELP


def test_upgrade_is_wired_into_help():
    """Story 14.1 AC: `upgrade` is a registered duty (was seventh when added)."""
    assert "upgrade" in DUTIES
    assert "upgrade" in _HELP


def test_workspace_is_wired_into_help():
    """Story 13.1 AC: `workspace` is a sixth duty."""
    assert "workspace" in DUTIES
    assert "workspace" in _HELP


def test_sync_is_wired_into_help():
    """Story 8.1 AC: `sync` is a fifth duty, dispatched exactly like the
    other four (structural conformance itself is already covered generically
    by `test_duty_protocol.py::test_every_declared_duty_resolves_to_a_
    conforming_implementation`)."""
    assert "sync" in DUTIES
    assert "sync" in _HELP


def test_setup_initrepo_validate_fast_are_wired_into_help():
    """Story 17.2 AC: bootstrap setup/initrepo/validate-fast verbs are registered."""
    for duty in ("setup", "initrepo", "validate-fast"):
        assert duty in DUTIES
        assert duty in _HELP


@pytest.mark.parametrize(
    "duty",
    [
        d
        for d in DUTIES
        # Excluded because a bare invocation either probes the real machine or
        # trips a required flag (exit 2), neither of which is a duty outcome.
        if d
        not in (
            "init",
            "setup",
            "initrepo",
            "validate-fast",
            "restore",
            "revoke",
            "cutover",
            "passport",
            "glass",
            "session",
            "deck-drift",
        )
    ],
)
def test_each_duty_dispatches_and_succeeds(duty):
    assert main([duty]) == EXIT_OK


def test_bare_invocation_prints_help(capsys):
    assert main([]) == EXIT_OK
    assert "Steward" in capsys.readouterr().out


def test_failing_duty_projects_to_exit_1(monkeypatch):
    class Failing:
        name = "keys"

        def run(self, ns):
            return DutyResult(ok=False, summary="nope")

    monkeypatch.setattr("pyforge.steward.cli.resolve_duty", lambda n: Failing())
    assert main(["keys"]) == EXIT_FAILED


def test_keyboard_interrupt_projects_to_130(monkeypatch):
    monkeypatch.setattr("pyforge.steward.cli.build_parser", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert main([]) == EXIT_INTERRUPTED


def test_crash_never_returns_bare_1(monkeypatch):
    """A crash must be distinguishable from a duty that legitimately failed."""

    class Crashing:
        name = "keys"

        def run(self, ns):
            raise RuntimeError("boom")

    monkeypatch.setattr("pyforge.steward.cli.resolve_duty", lambda n: Crashing())
    rc = main(["keys"])
    assert rc == EXIT_INTERNAL
    assert rc != EXIT_FAILED, "a crash must not be reported as a duty failure"


def test_flag_off_raised_inside_a_duty_projects_to_the_usage_code(monkeypatch, capsys):
    """Story 75.1: `pyforge.core.flags` defines no exit code -- `main()` maps `FlagOff` to
    steward's usage code 2 with the flag-off message on stderr, never to 1 or 70."""

    class Flagged:
        name = "keys"

        def run(self, ns):
            raise FlagOff("pyforge.test.some_capability")

    monkeypatch.setattr("pyforge.steward.cli.resolve_duty", lambda n: Flagged())
    rc = main(["keys"])
    assert rc == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.err == "steward: flag pyforge.test.some_capability is off\n"
    assert captured.out == ""


def test_keys_exec_is_a_verb_of_keys_not_a_new_duty(capsys):
    """`exec` joins `keys` (Story 75.1): the duty count stays 25, the verb list grows to seven."""
    assert len(DUTIES) == 25  # noqa: PLR2004
    assert "exec" not in DUTIES
    with pytest.raises(SystemExit):
        build_parser().parse_args(["keys", "--help"])
    out = capsys.readouterr().out
    assert "{encrypt,decrypt,rotate,list,audit,revoke,exec}" in out
    assert _HELP["keys"].endswith("encrypt/decrypt/rotate/list/audit/revoke/exec")
