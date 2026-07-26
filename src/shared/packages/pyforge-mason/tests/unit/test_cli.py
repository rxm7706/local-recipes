"""Story 1.1 — the dispatcher and its exit-code ownership."""

from __future__ import annotations

import pytest

from pyforge.mason import __version__
from pyforge.mason.cli import (
    EXIT_INTERNAL, EXIT_INTERRUPTED, EXIT_OK, build_parser, main,
)


def test_version_is_reported(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_bare_invocation_prints_help_and_succeeds(capsys):
    assert main([]) == EXIT_OK
    assert "Mason" in capsys.readouterr().out


@pytest.mark.parametrize("verb", ["recipe", "package", "environment"])
def test_all_three_verb_groups_are_declared(verb, capsys):
    assert main([verb]) == EXIT_OK
    assert verb in capsys.readouterr().err


def test_help_lists_the_whole_surface(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    out = capsys.readouterr().out
    for verb in ("recipe", "package", "environment"):
        assert verb in out


def test_keyboard_interrupt_projects_to_130(monkeypatch):
    monkeypatch.setattr("pyforge.mason.cli.build_parser",
                        lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert main([]) == EXIT_INTERRUPTED


def test_unexpected_exception_never_returns_bare_1(monkeypatch, capsys):
    """A crash must project to a documented code, not the interpreter default."""
    monkeypatch.setattr("pyforge.mason.cli.build_parser",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    rc = main([])
    assert rc == EXIT_INTERNAL
    assert rc != 1
