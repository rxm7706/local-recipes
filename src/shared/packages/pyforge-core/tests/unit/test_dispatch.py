"""Unit tests for ``pyforge.core.dispatch`` (Story 22.1, FR-13)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

import pyforge.core.dispatch as dispatch_module
from pyforge.core.dispatch import (
    EXIT_NOT_FOUND,
    EXIT_USAGE,
    DispatchError,
    dispatch_argv,
    main,
    primary_console_script,
)
from pyforge.core.process import ProcessError, ProcessResult

# The interpreter running this suite, read before any test points ``sys.executable`` elsewhere.
REAL_PYTHON = sys.executable


@pytest.fixture(autouse=True)
def _no_script_beside_the_interpreter(tmp_path_factory, monkeypatch):
    """Steward Story 133.4: the front door looks beside ``sys.executable`` first, so an environment that
    installs a station would hand these tests an absolute path. Each test starts with an empty directory there."""
    empty = tmp_path_factory.mktemp("interpreter-bin")
    monkeypatch.setattr(sys, "executable", str(empty / "python"))


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

# Guild env without atlas, mason, or warden (marshal Story 71.1).
GUILD_FIVE = {
    "doctor": "doctor",
    "herald": "herald",
    "marshal": "marshal",
    "scribe": "scribe",
    "steward": "steward",
}


def test_dispatch_argv_forwards_noun_and_verb():
    assert dispatch_argv(["pyforge", "steward", "keys", "list"], script_map=MAP) == ["steward", "keys", "list"]


def test_dispatch_argv_unknown_station_raises():
    with pytest.raises(DispatchError, match="unknown station"):
        dispatch_argv(["pyforge", "nope", "verb", "x"], script_map=MAP)


def test_context_noun_alias_dispatches_to_marshal():
    # marshal Story 46.1 AC4: `pyforge context bootstrap` -> `marshal context bootstrap`.
    assert dispatch_argv(["pyforge", "context", "bootstrap"], script_map=MAP) == [
        "marshal",
        "context",
        "bootstrap",
    ]
    assert dispatch_argv(["pyforge", "context", "bootstrap", "--offline"], script_map=MAP) == [
        "marshal",
        "context",
        "bootstrap",
        "--offline",
    ]


def test_real_station_named_like_an_alias_wins():
    shadowing = {**MAP, "context": "context-station"}
    assert dispatch_argv(["pyforge", "context", "bootstrap"], script_map=shadowing) == [
        "context-station",
        "bootstrap",
    ]


def test_noun_alias_with_owner_absent_is_unknown_station(monkeypatch):
    def _no_dist(name: str):
        raise dispatch_module.PackageNotFoundError(name)

    # An env that happens to have pyforge-marshal installed must not rescue it.
    monkeypatch.setattr(dispatch_module, "distribution", _no_dist)
    without_marshal = {k: v for k, v in MAP.items() if k != "marshal"}
    with pytest.raises(DispatchError, match="unknown station 'context'"):
        dispatch_argv(["pyforge", "context", "bootstrap"], script_map=without_marshal)


def test_main_runs_the_aliased_argv(tmp_path):
    proc = _FakeProcess()
    code = main(["pyforge", "context", "bootstrap"], process=proc, script_map=MAP, cwd=tmp_path)
    assert code == 0
    assert proc.calls == [(["marshal", "context", "bootstrap"], tmp_path)]


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


def test_roster_station_not_installed_names_environment():
    with pytest.raises(DispatchError) as exc:
        dispatch_argv(["pyforge", "warden", "--help"], script_map=GUILD_FIVE)
    msg = str(exc.value)
    assert "station 'warden' is not installed in this environment" in msg
    assert "-e pyforge-warden" in msg
    assert "pixi run -e pyforge-warden pyforge warden" in msg


@pytest.mark.parametrize(
    ("token", "env"),
    [
        ("atlas", "pyforge-atlas"),
        ("mason", "pyforge-mason"),
    ],
)
def test_roster_station_not_installed_atlas_and_mason(token: str, env: str):
    with pytest.raises(DispatchError, match=f"-e {env}"):
        dispatch_argv(["pyforge", token, "--help"], script_map=GUILD_FIVE)


def test_off_roster_unknown_station_message_unchanged():
    with pytest.raises(DispatchError) as exc:
        dispatch_argv(["pyforge", "nosuch"], script_map=GUILD_FIVE)
    assert str(exc.value) == ("unknown station 'nosuch'; known: doctor, herald, marshal, scribe, steward")


def test_context_alias_still_works_in_guild_five():
    assert dispatch_argv(["pyforge", "context", "bootstrap"], script_map=GUILD_FIVE) == [
        "marshal",
        "context",
        "bootstrap",
    ]


def test_installed_warden_still_dispatches():
    assert dispatch_argv(["pyforge", "warden", "scan"], script_map=MAP) == ["warden", "scan"]


def test_main_roster_not_installed_is_usage(capsys):
    proc = _FakeProcess()
    code = main(["pyforge", "warden", "--help"], process=proc, script_map=GUILD_FIVE)
    assert code == EXIT_USAGE
    assert proc.calls == []
    err = capsys.readouterr().err
    assert "unknown station" not in err
    assert "-e pyforge-warden" in err


def test_help_lists_installed_and_missing_roster_stations():
    with pytest.raises(DispatchError) as exc:
        dispatch_argv(["pyforge", "--help"], script_map=GUILD_FIVE)
    msg = str(exc.value)
    assert "stations: doctor, herald, marshal, scribe, steward" in msg
    assert "not installed here:" in msg
    assert "atlas (-e pyforge-atlas)" in msg
    assert "mason (-e pyforge-mason)" in msg
    assert "warden (-e pyforge-warden)" in msg


def test_help_empty_map_lists_all_roster_environments():
    with pytest.raises(DispatchError) as exc:
        dispatch_argv(["pyforge", "--help"], script_map={})
    msg = str(exc.value)
    assert "stations: (none installed)" in msg
    assert "not installed here:" in msg
    for station in ("atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden"):
        assert f"{station} (-e pyforge-{station})" in msg


# --- steward Story 133.4 (DW-steward-review-2026-11-24-5, defect 1) --------------------------------------------------


def _child_script(tmp_path: Path, body: str) -> Path:
    """An executable Python script standing in for a station's console script."""
    script = tmp_path / "fake-station"
    script.write_text(f"#!{REAL_PYTHON}\n{body}", encoding="utf-8")
    script.chmod(0o755)
    return script


def _front_door(script: Path, *args: str) -> list[str]:
    """``pyforge fake <args>`` run for real, with no injected process, mapped to ``script``."""
    code = (
        "import sys\n"
        "from pyforge.core.dispatch import main\n"
        f"raise SystemExit(main(['pyforge', 'fake', *sys.argv[1:]], script_map={{'fake': {str(script)!r}}}))\n"
    )
    return [REAL_PYTHON, "-c", code, *args]


def test_the_front_door_streams_its_child_output_as_it_is_written(tmp_path):
    release = tmp_path / "release"
    script = _child_script(
        tmp_path,
        "import pathlib, sys, time\n"
        "print('first', flush=True)\n"
        "release = pathlib.Path(sys.argv[1])\n"
        "deadline = time.monotonic() + 5\n"
        "while time.monotonic() < deadline and not release.exists():\n"
        "    time.sleep(0.05)\n"
        "print('released' if release.exists() else 'never released', flush=True)\n"
        "raise SystemExit(3)\n",
    )
    with subprocess.Popen(_front_door(script, str(release)), stdout=subprocess.PIPE, text=True) as door:
        assert door.stdout is not None
        first = door.stdout.readline()  # arrives while the child still waits, or only once it has given up
        release.touch()
        rest = door.stdout.read()
        code = door.wait(timeout=30)
    assert first == "first\n"
    assert rest == "released\n", "the child's first line arrived only after the child exited"
    assert code == 3


def test_the_front_door_hands_its_child_the_callers_stdin(tmp_path):
    script = _child_script(tmp_path, "import sys\nsys.stdout.write(sys.stdin.read().upper())\n")
    done = subprocess.run(
        _front_door(script), input="typed by the caller\n", capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout == "TYPED BY THE CALLER\n"


def test_main_runs_the_script_beside_the_interpreter_not_one_off_path(tmp_path, monkeypatch):
    bin_dir = tmp_path / "env" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "steward").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(bin_dir / "python"))
    proc = _FakeProcess()
    code = main(["pyforge", "steward", "keys", "list"], process=proc, script_map=MAP, cwd=tmp_path)
    assert code == 0
    assert proc.calls == [([str(bin_dir / "steward"), "keys", "list"], tmp_path)]


def test_main_keeps_the_bare_name_when_no_script_sits_beside_the_interpreter(tmp_path):
    proc = _FakeProcess()
    main(["pyforge", "steward", "keys", "list"], process=proc, script_map=MAP, cwd=tmp_path)
    assert proc.calls == [(["steward", "keys", "list"], tmp_path)]


def test_main_bad_environment_is_one_line_and_the_usage_code(tmp_path, monkeypatch, capsys):
    def _no_dist(name: str):
        raise dispatch_module.PackageNotFoundError(name)

    tree = tmp_path / "flags.json"
    tree.write_text(json.dumps({"flags": {}}), encoding="utf-8")
    monkeypatch.setattr(dispatch_module, "distribution", _no_dist)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "bogus")
    proc = _FakeProcess()
    code = main(["pyforge", "warden", "scan"], process=proc, script_map=GUILD_FIVE)
    assert code == EXIT_USAGE
    assert proc.calls == []
    err = capsys.readouterr().err
    assert err.count("\n") == 1
    assert "PYFORGE_ENVIRONMENT 'bogus'" in err
    assert "Traceback" not in err
    assert os.environ["PYFORGE_ENVIRONMENT"] == "bogus"
