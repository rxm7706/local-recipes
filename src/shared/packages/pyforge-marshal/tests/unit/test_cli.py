"""Unit tests for ``pyforge.marshal.cli.main`` (Story 1.1 stub) -- only
``--version``/``--help`` are wired; no real command dispatch yet. ``main``
always returns an int and never raises ``SystemExit`` itself.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.marshal.cli.main import __version__, main
from pyforge.marshal.core.verdict import EXIT_SIGINT

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_returns_zero_and_prints_version(capsys):
    exit_code = main(["--version"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_returns_zero_and_prints_usage(capsys):
    exit_code = main(["--help"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_no_args_returns_zero():
    assert main([]) == 0


def test_bogus_flag_returns_two_with_stderr_diagnostic(capsys):
    exit_code = main(["--bogus"])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.err


def test_main_never_raises_systemexit():
    """main() must RETURN an int; core/verdict.py is the sole exit-primitive
    caller under pyforge.marshal (sole-ownership rule)."""
    for argv in (["--version"], ["--help"], [], ["--bogus"]):
        try:
            main(argv)
        except SystemExit:
            pytest.fail(f"main({argv!r}) raised SystemExit instead of returning")


@pytest.mark.parametrize("argv", [["--version"], ["--help"], [], ["--bogus"]])
def test_exit_code_always_in_guarded_domain(argv, capsys):
    assert main(argv) in {0, 1, 2, 3, 4, 130}


def test_keyboard_interrupt_during_parsing_returns_exit_sigint():
    with patch(
        "argparse.ArgumentParser.parse_args", side_effect=KeyboardInterrupt
    ):
        assert main([]) == EXIT_SIGINT


def test_keyboard_interrupt_during_parser_construction_returns_exit_sigint():
    """The interrupt window opens before parse_args: _build_parser() must
    sit inside the same try, or a Ctrl-C during parser construction makes
    main() raise in violation of its returns-an-int-never-raises contract."""
    with patch(
        "pyforge.marshal.cli.main._build_parser", side_effect=KeyboardInterrupt
    ):
        assert main([]) == EXIT_SIGINT


def test_bool_systemexit_code_is_clamped_not_relayed():
    """``SystemExit(True)`` passes an isinstance-int check (bool is an int
    subclass) -- the relay must exclude bools like every other boundary in
    this package, clamping to the usage code instead of returning True."""
    with patch(
        "argparse.ArgumentParser.parse_args", side_effect=SystemExit(True)
    ):
        result = main([])
    assert result == 2
    assert not isinstance(result, bool)


def test_hand_synced_version_literal_matches_pyproject():
    """``__version__`` is hand-duplicated from ``pyproject.toml`` (scaffold
    stage -- see the module docstring); this is the safety net that catches
    the two drifting apart on the next version bump."""
    pyproject = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    assert __version__ == pyproject["project"]["version"]
