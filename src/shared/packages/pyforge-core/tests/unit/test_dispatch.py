"""Unit tests for ``pyforge.core.dispatch`` (Story 22.1, FR-13)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from pyforge.core.dispatch import (
    EXIT_NOT_FOUND,
    EXIT_USAGE,
    DispatchError,
    dispatch_argv,
    main,
    primary_console_script,
)
from pyforge.core.process import ProcessError, ProcessResult


class _FakeProcess:
    def __init__(self, result: ProcessResult | None = None, *, error: Exception | None = None):
        self.result = result or ProcessResult(returncode=0, stdout="", stderr="")
        self.error = error
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, argv: Sequence[str], *, cwd: Path, timeout_s: float | None = None):
        self.calls.append((list(argv), cwd))
        if self.error is not None:
            raise self.error
        return self.result

    def is_alive(self, pid: int) -> bool:
        return False

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, log_path: Path) -> int:
        raise ProcessError("unused")


MAP = {
    "steward": "steward",
    "warden": "warden",
    "atlas": "pyforge-atlas",
    "marshal": "marshal",
}


def test_dispatch_argv_forwards_noun_and_verb():
    assert dispatch_argv(["pyforge", "steward", "keys", "list"], script_map=MAP) == ["steward", "keys", "list"]


def test_dispatch_argv_unknown_station_raises():
    with pytest.raises(DispatchError, match="unknown station"):
        dispatch_argv(["pyforge", "nope", "verb", "x"], script_map=MAP)


def test_main_forwards_child_exit_code(tmp_path, capsys):
    proc = _FakeProcess(ProcessResult(returncode=3, stdout="out\n", stderr="err\n"))
    code = main(
        ["pyforge", "steward", "keys", "list"],
        process=proc,
        script_map=MAP,
        cwd=tmp_path,
    )
    assert code == 3
    assert proc.calls == [(["steward", "keys", "list"], tmp_path)]
    captured = capsys.readouterr()
    assert captured.out == "out\n"
    assert captured.err == "err\n"


def test_main_unknown_station_is_usage_and_does_not_run(capsys):
    proc = _FakeProcess()
    code = main(["pyforge", "nope", "verb", "x"], process=proc, script_map=MAP)
    assert code == EXIT_USAGE
    assert proc.calls == []
    assert "unknown station" in capsys.readouterr().err


def test_main_missing_binary_exits_127(tmp_path, capsys):
    proc = _FakeProcess(error=ProcessError("executable not found: 'steward'"))
    code = main(
        ["pyforge", "steward", "keys", "list"],
        process=proc,
        script_map=MAP,
        cwd=tmp_path,
    )
    assert code == EXIT_NOT_FOUND
    assert "executable not found" in capsys.readouterr().err


def test_primary_console_script_skips_mcp_extra():
    assert (
        primary_console_script(
            "pyforge-marshal",
            {"marshal": "pyforge.marshal.cli.main:main", "marshal-mcp": "x:y"},
        )
        == "marshal"
    )


def test_primary_console_script_prefers_dist_name_for_atlas():
    assert primary_console_script("pyforge-atlas", {"pyforge-atlas": "pyforge.atlas.__main__:main"}) == "pyforge-atlas"
