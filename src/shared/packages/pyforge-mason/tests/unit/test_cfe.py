"""Story 1.6 -- the CFE import-floor probe: full/partial floor, caching,
the `OSError`/`TimeoutExpired` fold-into-missing path, and
`ensure_import_floor`'s raise/no-raise paths. `subprocess.run` is mocked
throughout (AD-16: no test in this suite requires a real interpreter to
probe).

Story 1.7 extends this file with `ensure_cfe_root`'s raise/no-raise paths
over every `resolve.py` step."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

import pytest

from pyforge.mason.cfe import (
    CFE_IMPORT_FLOOR, ImportFloorResult, _build_probe_script,
    ensure_cfe_root, ensure_import_floor, probe_import_floor,
)
from pyforge.mason.errors import CfeImportFloorError, CfeUnresolvedError
from pyforge.mason.resolve import (
    STEP_CWD_WALK, STEP_ENVIRONMENT, STEP_FLAG, STEP_NOT_FOUND, ResolvedCfeRoot,
)


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


# --- Story 1.7: ensure_cfe_root ----------------------------------------------

@pytest.mark.parametrize("step", [STEP_FLAG, STEP_ENVIRONMENT, STEP_CWD_WALK])
def test_ensure_cfe_root_returns_none_for_every_resolved_step(step, tmp_path):
    resolved = ResolvedCfeRoot(root=tmp_path, step=step)
    assert ensure_cfe_root(resolved) is None


def test_ensure_cfe_root_raises_cfe_unresolved_error_when_not_found():
    resolved = ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND)
    with pytest.raises(CfeUnresolvedError):
        ensure_cfe_root(resolved)


def test_ensure_cfe_root_never_re_resolves():
    """`ensure_cfe_root` takes the already-computed `ResolvedCfeRoot` -- it
    must never call `resolve_cfe_root` to re-derive it (spec Never
    boundary).

    Review pass (2026-08-09): this used to monkeypatch
    `pyforge.mason.resolve.resolve_cfe_root`, but `cfe.py` never imports
    that name -- only `ResolvedCfeRoot`/`STEP_NOT_FOUND` -- so the
    monkeypatch exercised nothing and would not catch the realistic
    regression: a future `from .resolve import resolve_cfe_root` added to
    `cfe.py` and called unqualified would bind its own name in `cfe.py`'s
    module namespace, untouched by patching the attribute on the `resolve`
    module. A structural assertion that `cfe.py` never binds that name at
    all is the stronger guard -- it fails the moment such an import is
    added, regardless of whether it is ever called."""
    import pyforge.mason.cfe as cfe_module

    assert not hasattr(cfe_module, "resolve_cfe_root")
