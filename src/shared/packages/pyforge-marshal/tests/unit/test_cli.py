"""Unit tests for ``pyforge.marshal.cli.main`` (Story 1.1 stub) -- only
``--version``/``--help`` are wired; no real command dispatch yet. ``main``
always returns an int and never raises ``SystemExit`` itself.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.marshal.cli.main import __version__, main
from pyforge.marshal.core.verdict import EXIT_SIGINT

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover -- this package requires-python >=3.12
    import tomli as tomllib

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


def test_hand_synced_version_literal_matches_pyproject():
    """``__version__`` is hand-duplicated from ``pyproject.toml`` (scaffold
    stage -- see the module docstring); this is the safety net that catches
    the two drifting apart on the next version bump."""
    pyproject = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    assert __version__ == pyproject["project"]["version"]
