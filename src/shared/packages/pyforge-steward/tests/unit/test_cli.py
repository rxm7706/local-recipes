"""Story 1.1 — dispatcher behaviour and exit-code ownership (AD-8)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pytest
from pyforge.core.flags import FlagOff

from pyforge.steward import __version__, bootstrap
from pyforge.steward.bootstrap import shell_init_script
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


def test_there_are_exactly_thirty_one_duties():
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
        "measure",
        "load",
        "passport",
        "glass",
        "quarantine",
        "session",
        "deck-drift",
        "estate",
        "ci",
        "pages",
        "preflight",
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
            "quarantine",
            "session",
            "deck-drift",
            "estate",
            "ci",
            "preflight",
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


@pytest.mark.parametrize("argv", [["--help"], ["keys", "--help"], ["keys", "list"]])
def test_a_bad_flag_environment_projects_to_the_usage_code_not_a_traceback(monkeypatch, capsys, argv):
    """Story 76.1: `build_parser` reads a flag (`keys exec`'s help), so a bad
    PYFORGE_ENVIRONMENT arrives before any verb runs -- a named message and steward's
    usage code 2, never a traceback and exit 70."""
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "qa")
    rc = main(argv)
    assert rc == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.err.startswith("steward: ")
    assert "PYFORGE_ENVIRONMENT" in captured.err
    assert "'qa'" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_a_bad_flag_overlay_projects_to_the_usage_code(monkeypatch, tmp_path, capsys):
    tree = tmp_path / "flags.json"
    tree.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.steward.ghe_fleet_credentials": {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": "off",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "flag-overlays.json").write_text(json.dumps({"dev": {"pyforge.nope": "off"}}), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    assert main(["--help"]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert "pyforge.nope" in err and "Traceback" not in err


def test_keys_exec_is_a_verb_of_keys_not_a_new_duty(capsys):
    """`exec` joins `keys` (Story 75.1): it is a verb, not a duty (31 with Story 102.3's `pages`); the verb list grows to seven."""
    assert len(DUTIES) == 31  # noqa: PLR2004
    assert "exec" not in DUTIES
    with pytest.raises(SystemExit):
        build_parser().parse_args(["keys", "--help"])
    out = capsys.readouterr().out
    assert "{encrypt,decrypt,rotate,list,audit,revoke,exec}" in out
    assert _HELP["keys"].endswith("encrypt/decrypt/rotate/list/audit/revoke/exec")


# --------------------------------------------------------------------------- Story 126.3
# ``steward shell-init`` completes every duty the parser registers. The bash completion carried its own duty
# list, written when the parser had 13 duties; the parser grew to 31 and the list did not. The completion now
# derives its words from the parser, and these tests fail when the two disagree.

_COMPGEN_RE = re.compile(r'compgen -W "([^"]*)"')


def _parser_duties() -> list[str]:
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction) and action.dest == "duty":
            return list(action.choices)
    raise AssertionError("steward's parser has no duty subparsers")


def _completion_words(script: str) -> list[str]:
    match = _COMPGEN_RE.search(script)
    assert match is not None, "shell-init emits no compgen word list"
    return match.group(1).split()


def test_completion_lists_every_duty_the_parser_has(tmp_path: Path) -> None:
    duties = _parser_duties()
    words = _completion_words(shell_init_script(root=tmp_path))
    missing = [duty for duty in duties if duty not in words]
    assert missing == [], f"duties the parser has and the completion lacks: {missing}"


def test_completion_lists_nothing_the_parser_lacks(tmp_path: Path) -> None:
    duties = _parser_duties()
    words = _completion_words(shell_init_script(root=tmp_path))
    assert [word for word in words if word not in duties] == []
    assert len(words) == len(set(words))


def test_a_duty_added_to_the_parser_reaches_the_completion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pyforge.steward.cli as cli

    monkeypatch.setattr(cli, "DUTIES", (*cli.DUTIES, "story-126-3-probe"))
    monkeypatch.setitem(cli._HELP, "story-126-3-probe", "probe duty")
    assert "story-126-3-probe" in _parser_duties()
    assert "story-126-3-probe" in _completion_words(shell_init_script(root=tmp_path))


# Story 126.3: the bootstrap duties' ``--help`` names the environment they really default to. Story 63.6 moved
# the default of ``setup``, ``initrepo`` and ``validate-fast`` from ``local-recipes`` (the 10 GB recipe factory)
# to the Guild environment; the three ``--env`` help strings kept saying ``local-recipes``.


def _env_help(duty: str) -> str:
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction) and action.dest == "duty":
            for option in action.choices[duty]._actions:
                if "--env" in option.option_strings:
                    return option.help or ""
    raise AssertionError(f"steward {duty} has no --env option")


@pytest.mark.parametrize("duty", ["setup", "initrepo", "validate-fast"])
def test_env_help_names_the_default_the_duty_uses(duty: str) -> None:
    assert f"(default: {bootstrap._DEFAULT_PIXI_ENV})" in _env_help(duty)
