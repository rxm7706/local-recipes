"""The retired ``--specs`` mode of scripts/bmad_drift_check.py (marshal Story 76.1).

``spec-one-chain-per-station:CAP-11`` retires the legacy ``docs/specs/`` intake
tier, so the drift script's ``--specs`` report (each intake spec's status and
whether ``CLAUDE.md`` indexes it) goes with it. The flag must now be rejected
as an unrecognised argument, and the modes that stay must keep working.

Harness style matches test_bmad_loop_baseline_drift_check.py: importlib-load
the script by path. Only the read-only modes are exercised in-process; ``--fix``
and ``--write-baseline`` mutate the project tree and are not run here.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bmad_drift_check.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "bmad_drift_check_under_test", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bmad_drift_check_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_specs_flag_is_rejected_as_unrecognised(capsys):
    mod = _load_script()
    with pytest.raises(SystemExit) as exc:
        mod.main(["--specs"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unrecognized arguments" in err
    assert "--specs" in err


def test_specs_flag_exits_2_from_the_command_line():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--specs"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 2
    assert "unrecognized arguments: --specs" in proc.stderr
    assert proc.stdout == ""


def test_specs_mode_leaves_no_code_behind():
    mod = _load_script()
    assert not hasattr(mod, "cmd_specs")
    assert not hasattr(mod, "DOCS_SPECS")
    assert not hasattr(mod, "frontmatter_status")


@pytest.mark.parametrize("flag", ["--json", "--groundtruth"])
def test_ground_truth_modes_still_print_the_same_json(flag, capsys):
    mod = _load_script()
    assert mod.main([flag]) == 0
    out = capsys.readouterr().out
    assert json.loads(out) == mod.ground_truth()


def test_bare_run_still_points_at_doctor_and_lists_only_live_modes(capsys):
    mod = _load_script()
    assert mod.main([]) == 2
    err = capsys.readouterr().err
    assert "python -m pyforge.doctor.sources bmad-drift" in err
    assert "--specs" not in err
    for live in ("--json", "--groundtruth", "--fix", "--write-baseline"):
        assert live in err
