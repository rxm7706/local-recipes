"""Story 7.1 ("One build, whole Guild"): `pyforge-atlas --version` regression proof.

Kedro's own Click-based command routing has no built-in `--version`, so
`pyforge.atlas.__main__.main` intercepts it before dispatching to
`find_run_command`. Scoped to the FIRST token only (mirrors marshal's
documented `--version` convention), so `--version` appearing later among
real run flags/values doesn't short-circuit a legitimate invocation.
"""
from __future__ import annotations

import pytest

from pyforge.atlas import __version__
from pyforge.atlas.__main__ import main


def test_version_flag_prints_version_and_returns(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["--version"])

    captured = capsys.readouterr()
    assert captured.out.strip() == f"pyforge-atlas {__version__}"
    assert result is None


def test_bare_argv_version_via_sys_argv(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["pyforge-atlas", "--version"])

    result = main()

    captured = capsys.readouterr()
    assert captured.out.strip() == f"pyforge-atlas {__version__}"
    assert result is None


def test_version_not_first_token_does_not_short_circuit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--version` anywhere but first must fall through to Kedro's own
    routing, not print the package version -- the position-scoping this
    story's review pass added (previously an unscoped membership check)."""
    with pytest.raises(SystemExit):
        main(["run", "--version"])

    captured = capsys.readouterr()
    assert f"pyforge-atlas {__version__}" not in captured.out
