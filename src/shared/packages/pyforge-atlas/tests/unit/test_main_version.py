"""Story 7.1 ("One build, whole Guild"): `pyforge-atlas --version` regression proof.

Kedro's own Click-based command routing has no built-in `--version`, so
`pyforge.atlas.__main__.main` intercepts it before importing or dispatching
to Kedro at all. Scoped to the FIRST token only (mirrors marshal's
documented `--version` convention), so `--version` appearing later among
real run flags/values doesn't short-circuit a legitimate invocation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pyforge.atlas import __version__
from pyforge.atlas.__main__ import main


def test_version_flag_prints_version_and_returns(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["--version"])

    captured = capsys.readouterr()
    assert captured.out.strip() == f"pyforge-atlas {__version__}"
    assert result is None


def test_bare_argv_version_via_sys_argv(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["pyforge-atlas", "--version"])

    result = main()

    captured = capsys.readouterr()
    assert captured.out.strip() == f"pyforge-atlas {__version__}"
    assert result is None


def test_version_via_args_keyword(capsys: pytest.CaptureFixture[str]) -> None:
    """Click's own `main(args=[...])` keyword form must hit the intercept too.

    The dispatch below the intercept forwards `**kwargs` straight to Click,
    so a caller passing argv by keyword is a supported shape; resolving only
    positional args would have silently bypassed `--version` for them.
    """
    result = main(args=["--version"])

    captured = capsys.readouterr()
    assert captured.out.strip() == f"pyforge-atlas {__version__}"
    assert result is None


def test_explicit_none_positional_falls_back_to_sys_argv(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`main(None)` is Click's documented "read sys.argv" shape.

    The keyword branch has always tested `is not None`; the positional branch
    tested truthiness, so `(None,)` -- a non-empty tuple -- resolved `cli_args`
    to `None` and skipped the intercept, making the two shapes disagree about
    the same value.
    """
    monkeypatch.setattr("sys.argv", ["pyforge-atlas", "--version"])

    result = main(None)

    captured = capsys.readouterr()
    assert captured.out.strip() == f"pyforge-atlas {__version__}"
    assert result is None


def test_version_not_first_token_does_not_short_circuit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--version` anywhere but first must fall through to Kedro's own
    routing, not print the package version -- the position-scoping this
    story's review pass added (previously an unscoped membership check)."""
    with pytest.raises(SystemExit) as excinfo:
        main(["run", "--version"])

    # Click's own "No such option" usage error, not a print-version
    # short-circuit and not an unrelated failure swallowed into exit 1.
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert f"pyforge-atlas {__version__}" not in captured.out


def test_version_is_one_clean_line_in_a_real_process() -> None:
    """The in-process tests above CANNOT catch the noise regression.

    Importing `kedro.framework.project` installs Kedro's rich logging config
    and prints an INFO banner (a wrapped absolute path) to STDOUT at import
    time. Under pytest that fires during collection, outside `capsys`'s
    window, so the `capsys` assertions stayed green while the shipped CLI
    emitted nine lines including the build host's checkout path. Only a
    fresh process proves the real contract, so this is the test that guards
    the deferred-import fix.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pyforge.atlas", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == f"pyforge-atlas {__version__}"
    assert proc.stdout.count("\n") == 1
    # Asserted on BOTH streams, not just stdout: the contract this guards is
    # "one clean version line, no checkout path leaked", and a logging config
    # is free to be emitted on stderr instead -- which would keep the stdout
    # assertions green while `pyforge-atlas --version 2>&1` stayed exactly as
    # polluted as before the deferred-import fix.
    combined = proc.stdout + proc.stderr
    assert "logging configuration" not in combined
    assert str(Path(__file__).resolve().parents[2]) not in combined
