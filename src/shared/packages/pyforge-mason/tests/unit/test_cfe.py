"""Story 1.6 -- the CFE import-floor probe: full/partial floor, caching,
the `OSError`/`TimeoutExpired` fold-into-missing path, and
`ensure_import_floor`'s raise/no-raise paths. `subprocess.run` is mocked
throughout (AD-16: no test in this suite requires a real interpreter to
probe)."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

import pytest

from pyforge.mason.cfe import (
    CFE_IMPORT_FLOOR, ImportFloorResult, _build_probe_script,
    ensure_import_floor, probe_import_floor,
)
from pyforge.mason.errors import CfeImportFloorError


@pytest.fixture(autouse=True)
def _clear_probe_cache():
    """`probe_import_floor` is `functools.lru_cache`-wrapped for the process
    lifetime; without clearing it here, one test's cached result for a given
    interpreter string would leak into another test reusing that same
    string."""
    probe_import_floor.cache_clear()
    yield
    probe_import_floor.cache_clear()


def _fake_completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _all_ok_stdout() -> str:
    return "\n".join(f"{name}:ok" for name in CFE_IMPORT_FLOOR.values())


# --- I/O & Edge-Case Matrix --------------------------------------------------

def test_full_floor_importable_reports_nothing_missing():
    with patch("pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())) as mock_run:
        result = probe_import_floor("/fake/python")

    assert result == ImportFloorResult(interpreter="/fake/python", missing=())
    mock_run.assert_called_once()


def test_partial_floor_missing_reported_in_floor_declared_order():
    # Report the subprocess output in the OPPOSITE order from
    # CFE_IMPORT_FLOOR's declaration, to prove `missing`'s ordering comes
    # from the floor table, not from subprocess-output order.
    stdout_lines = []
    for name in reversed(list(CFE_IMPORT_FLOOR.values())):
        if name in ("truststore", "ruamel.yaml"):
            stdout_lines.append(f"{name}:missing")
        else:
            stdout_lines.append(f"{name}:ok")
    stdout = "\n".join(stdout_lines)

    with patch("pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(stdout)):
        result = probe_import_floor("/fake/python")

    assert result.missing == ("truststore", "ruamel.yaml")


def test_second_probe_of_same_interpreter_uses_cache():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())
    ) as mock_run:
        first = probe_import_floor("/same/python")
        second = probe_import_floor("/same/python")

    assert first == second
    mock_run.assert_called_once()


def test_different_interpreters_are_probed_independently():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())
    ) as mock_run:
        probe_import_floor("/one/python")
        probe_import_floor("/two/python")

    assert mock_run.call_count == 2


def test_interpreter_cannot_be_spawned_reports_every_module_missing():
    with patch("pyforge.mason.cfe.subprocess.run", side_effect=OSError("no such file")):
        result = probe_import_floor("/does/not/exist")

    assert result.missing == tuple(CFE_IMPORT_FLOOR)
    assert result.interpreter == "/does/not/exist"


def test_probe_timeout_reports_every_module_missing():
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["python"], timeout=15.0),
    ):
        result = probe_import_floor("/slow/python")

    assert result.missing == tuple(CFE_IMPORT_FLOOR)


def test_ensure_import_floor_raises_when_missing():
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        return_value=_fake_completed("yaml:missing\nrequests:ok\npackaging:ok\ntruststore:ok\nruamel.yaml:ok\nconda_forge_metadata:ok"),
    ):
        with pytest.raises(CfeImportFloorError) as excinfo:
            ensure_import_floor("/fake/python")

    assert excinfo.value.missing == ("pyyaml",)
    assert excinfo.value.interpreter == "/fake/python"


def test_ensure_import_floor_returns_none_when_full_floor_present():
    with patch("pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())):
        assert ensure_import_floor("/fake/python") is None


# --- Probe invocation shape (list argv, never shell=True, timeout) --------

def test_probe_invokes_subprocess_with_list_argv_and_no_shell():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())
    ) as mock_run:
        probe_import_floor("/fake/python")

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv[0] == "/fake/python"
    assert argv[1] == "-c"
    assert isinstance(argv[2], str)
    assert kwargs.get("shell", False) is False
    assert "timeout" in kwargs
    assert kwargs.get("check") is False


# --- Review pass: probe script actually runs correctly (not just mocked) ---

def test_build_probe_script_actually_runs_correctly_under_a_real_interpreter():
    """`_build_probe_script`'s generated source is never exercised by the
    mocked tests above -- this test runs it for real under `sys.executable`
    (which always has `importlib` and the stdlib modules on the floor:
    `packaging` ships with `pip`/build tooling and is installed in this test
    environment) to prove the generated code is syntactically valid and
    produces the documented `:ok`/`:missing` marker format, not just that
    the mocked parsing logic in `probe_import_floor` is self-consistent."""
    script = _build_probe_script()

    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=15.0, check=False,
    )

    assert completed.stderr == ""
    lines = completed.stdout.splitlines()
    assert len(lines) == len(CFE_IMPORT_FLOOR)
    for import_name, line in zip(CFE_IMPORT_FLOOR.values(), lines):
        assert line in (f"{import_name}:ok", f"{import_name}:missing")


def test_build_probe_script_reports_missing_for_a_module_that_does_not_exist(monkeypatch):
    """A floor entry with no real backing module must produce `:missing`,
    not a raw traceback -- proven against a real interpreter, not a mock."""
    monkeypatch.setattr(
        "pyforge.mason.cfe.CFE_IMPORT_FLOOR",
        {"definitely-not-a-real-package": "definitely_not_a_real_module_xyz"},
    )
    script = _build_probe_script()

    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=15.0, check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout.splitlines() == ["definitely_not_a_real_module_xyz:missing"]


# --- Review pass: ensure_import_floor shares probe_import_floor's cache ---

def test_ensure_import_floor_reuses_probe_import_floor_cache():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())
    ) as mock_run:
        ensure_import_floor("/same/python")
        ensure_import_floor("/same/python")

    mock_run.assert_called_once()


# --- Review pass: a crash partway through the probe script still credits
# modules that printed their marker before the crash ----------------------

def test_nonzero_returncode_with_partial_output_still_credits_printed_modules():
    stdout = "yaml:ok\nrequests:ok\n"  # only 2 of 6 lines printed before a crash
    completed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout=stdout, stderr="Traceback (most recent call last)...",
    )
    with patch("pyforge.mason.cfe.subprocess.run", return_value=completed):
        result = probe_import_floor("/fake/python")

    assert "pyyaml" not in result.missing
    assert "requests" not in result.missing
    assert result.missing == ("packaging", "truststore", "ruamel.yaml", "conda-forge-metadata")
