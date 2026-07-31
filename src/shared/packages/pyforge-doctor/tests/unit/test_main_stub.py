"""Unit tests for ``pyforge.doctor.__main__``'s top-level parser (Story 1.1,
extended by Story 1.5). ``check`` is now a wired subcommand (its own
behavior lives in ``test_cli_check.py``) — the top-level subparsers are
``required=True`` (mirrors ``pyforge-warden``), so a bare ``doctor`` with no
subcommand is now a usage error, not a silent no-op. ``main`` always
returns an int and never raises ``SystemExit`` itself.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pyforge.doctor.__main__ import __version__, main
from pyforge.doctor.verdict import EXIT_SIGINT


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


def test_no_args_is_a_usage_error_exit_two(capsys):
    # Top-level subparsers are required=True (mirrors pyforge-warden): a
    # bare `doctor` with no subcommand no longer silently returns 0.
    exit_code = main([])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.err


def test_bogus_flag_returns_two_with_stderr_diagnostic(capsys):
    exit_code = main(["--bogus"])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.err


def test_main_never_raises_systemexit():
    """main() must RETURN an int; verdict.py is the sole exit-primitive
    caller under pyforge.doctor (sole-ownership rule)."""
    for argv in (["--version"], ["--help"], [], ["--bogus"]):
        try:
            main(argv)
        except SystemExit:
            pytest.fail(f"main({argv!r}) raised SystemExit instead of returning")


@pytest.mark.parametrize("argv", [["--version"], ["--help"], [], ["--bogus"]])
def test_exit_code_always_in_guarded_domain(argv, capsys):
    assert main(argv) in {0, 2, 130}


def test_keyboard_interrupt_during_parsing_returns_exit_sigint():
    with patch(
        "argparse.ArgumentParser.parse_args", side_effect=KeyboardInterrupt
    ):
        assert main([]) == EXIT_SIGINT


def test_keyboard_interrupt_during_check_dispatch_returns_exit_sigint():
    # A gather call is real multi-second work (Story 1.5's whole point), so
    # Ctrl-C during dispatch -- not just during argument parsing -- must
    # also return EXIT_SIGINT rather than escape main() as a raw
    # KeyboardInterrupt (main() never raises -- see its own docstring).
    with patch(
        "pyforge.doctor.__main__._run_check", side_effect=KeyboardInterrupt
    ):
        assert main(["check"]) == EXIT_SIGINT


def test_unexpected_exception_during_check_dispatch_returns_two_not_a_traceback(
    capsys,
):
    # Review finding: main()'s try/except only caught SystemExit/
    # KeyboardInterrupt -- any OTHER exception (e.g. a future schema/model
    # drift tripping _emit_json's jsonschema.validate self-check) escaped
    # uncaught, violating the documented {0, 2, 130} exit-code domain
    # (AD-2). Mirrors pyforge-warden's cli.py last-resort net.
    with patch(
        "pyforge.doctor.__main__._run_check",
        side_effect=RuntimeError("simulated internal defect"),
    ):
        exit_code = main(["check"])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "simulated internal defect" in captured.err
