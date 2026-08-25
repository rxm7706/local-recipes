"""Tests for ``scripts/detectors.py``'s Doctor-source integration.

Two groups:

1. ``_doctor_sources()`` (Story 6.2) -- the ``--list``-only diagnostic
   catalog view. Two branches, mirroring the spec's I/O & Edge-Case Matrix:
   ``pyforge.doctor`` importable -- ``(True, rows)``, one row per
   ``sources.REGISTRY`` entry; NOT importable -- ``(False, [])``, never a
   crash, never a registry finding.
2. ``_run_doctor_sources()`` / ``main()`` (Story 6.9) -- the REAL run path.
   Unlike group 1, an unimportable ``pyforge.doctor`` here is NOT a benign
   absence: post-retirement, the ten origin ``scripts/*_check.py`` files are
   gone, so this is the ONLY place those ten verdicts are measured. Pins the
   "unknown, never green" regression the story's own precondition names --
   confirmed to fail against the pre-fix code (this file's own git history:
   `_run_doctor_sources` reverted, the new test below went red -- a silent
   `exit_code == 0` over a post-retirement fixture with zero scanned
   detectors, exactly the false green the precondition describes).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# `pyforge.doctor` isn't installed in every env this test might run under
# (e.g. the fat `local-recipes` env doesn't carry the dedicated
# `pyforge-doctor` conda package) -- import it straight from source so the
# "importable" branch below is a real exercise of the merge, not a skip.
_DOCTOR_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"
if str(_DOCTOR_SRC) not in sys.path:
    sys.path.insert(0, str(_DOCTOR_SRC))

# `scripts/` has no `__init__.py` -- reach detectors.py the same way
# `pyforge.doctor.sources.fleet_scan` reaches its own scripts/ siblings.
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import detectors  # noqa: E402  (sys.path must be set up first)


def test_doctor_sources_returns_one_row_per_registry_entry_when_importable():
    from pyforge.doctor.sources import REGISTRY

    available, rows = detectors._doctor_sources()

    assert available is True
    assert len(rows) == len(REGISTRY)
    for row, registration in zip(rows, REGISTRY):
        assert row == registration.to_json_dict()


def test_doctor_sources_degrades_to_empty_list_when_package_not_importable(
    monkeypatch,
):
    # A name mapped to None in sys.modules makes the next
    # `from <name> import ...` raise ImportError, without actually
    # uninstalling anything -- the exact branch `_doctor_sources()` must
    # catch rather than let propagate.
    monkeypatch.setitem(sys.modules, "pyforge.doctor.sources", None)

    assert detectors._doctor_sources() == (False, [])


def test_list_json_includes_availability_flag_and_matching_source_rows():
    from pyforge.doctor.sources import REGISTRY

    proc = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / "detectors.py"), "--list", "--json"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(_DOCTOR_SRC)},
    )
    assert proc.returncode in (0, 1)  # 1 is a pre-existing registry finding, not this test's concern
    payload = json.loads(proc.stdout)
    assert payload["doctor_sources_available"] is True
    assert len(payload["doctor_sources"]) == len(REGISTRY)


def test_list_human_readable_reports_doctor_sources_section():
    proc = subprocess.run(
        [sys.executable, str(_SCRIPTS_DIR / "detectors.py"), "--list"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(_DOCTOR_SRC)},
    )
    assert "doctor sources (declared, not scanned):" in proc.stdout
    assert "marshal-durability" in proc.stdout
    assert "subject=marshal" in proc.stdout
    assert "owner=doctor" in proc.stdout


# --- _run_doctor_sources() / main() real run path (Story 6.9) -----------------


def _post_retirement_fixture(tmp_path: Path) -> None:
    """A repo tree shaped like the state AFTER this story's Commit 2:
    ``scripts/`` and ``docs/dashboard/`` exist but hold none of the ten
    retired ``*_check.py`` files -- ``discover()`` must find ZERO scanned
    detectors here, so the only way this fixture reports anything is via
    ``_run_doctor_sources``. Mirrors the story's own "post-retirement
    fixture" wording in its Code Map."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs" / "dashboard").mkdir(parents=True)
    (tmp_path / "pixi.toml").write_text("", encoding="utf-8")


def test_run_doctor_sources_returns_ten_unknown_rows_when_unimportable(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyforge.doctor.sources", None)

    rows = detectors._run_doctor_sources("all")

    assert len(rows) == 10
    assert all(row["status"] == "unknown" for row in rows)
    assert all(row["rc"] == 2 for row in rows)
    assert all("pyforge.doctor is not importable" in row["summary"] for row in rows)


def test_run_doctor_sources_filters_by_scope_like_a_scanned_detector():
    # Steward 30.2: dashboard-drift is repo-scope (reintroduction gate).
    repo_rows = detectors._run_doctor_sources("repo")
    all_rows = detectors._run_doctor_sources("all")

    assert len(all_rows) == 10
    assert len(repo_rows) == 10
    assert "dashboard-drift" in {row["name"] for row in repo_rows}
    assert "dashboard-drift" in {row["name"] for row in all_rows}


def test_main_scope_repo_reports_ten_unknown_rows_and_never_exits_zero_when_unimportable(
    monkeypatch, tmp_path: Path, capsys,
):
    """The regression this story's own precondition names: with
    ``pyforge.doctor`` unimportable and NOTHING left for ``discover()`` to
    scan (the post-retirement shape), ``detectors.py --scope repo`` must
    report ten ``unknown`` rows and exit non-zero -- never 0 with a
    silently empty registry. Confirmed to fail against the pre-fix code by
    temporarily reverting ``_run_doctor_sources``/its call in ``main()``:
    without it, ``results`` is `[]`, `registry_findings` is `[]`, and
    ``main()`` returns the exact false-green ``0`` this test pins."""
    _post_retirement_fixture(tmp_path)
    monkeypatch.setattr(detectors, "ROOT", tmp_path)
    # SEARCH is a module-level constant DERIVED from ROOT at import time
    # (`ROOT / "scripts"`, `ROOT / "docs" / "dashboard"`) -- patching ROOT
    # alone does not retroactively move it, so discover() would otherwise
    # keep scanning THIS checkout's real scripts/ regardless of the fixture.
    monkeypatch.setattr(
        detectors, "SEARCH",
        ((tmp_path / "scripts", "*_check.py"),
         (tmp_path / "docs" / "dashboard", "check_*.py")),
    )
    monkeypatch.setitem(sys.modules, "pyforge.doctor.sources", None)
    monkeypatch.setattr(sys, "argv", ["detectors.py", "--scope", "repo"])

    exit_code = detectors.main()

    assert exit_code != 0, "unknown, never a silent 0 (the story's own precondition)"
    assert exit_code == 2
    out = capsys.readouterr().out
    unknown_lines = [ln for ln in out.splitlines() if "unknown" in ln and ln.strip().startswith("?")]
    assert len(unknown_lines) == 10, out


def test_discover_reports_zero_registry_findings_against_the_real_scripts_tree():
    """Regression pin for the gap review pass 2 found: nothing exercised
    ``discover()`` against this checkout's OWN live ``scripts/``/
    ``docs/dashboard/`` tree, so ``spec_surface_check.py``/
    ``bmad_drift_check.py`` matching the ``*_check.py`` glob with no
    ``DETECTOR`` marker (Story 6.9 review pass 1 reduced both to
    mutation-only residuals) went undetected as a permanent registry red
    until an adversarial pass caught it live. The synthetic fixture above
    can't catch this class of gap by construction -- it never has any
    matching file on disk."""
    _detectors, registry_findings = detectors.discover()

    assert registry_findings == [], (
        "a *_check.py-named file with no DETECTOR marker must explicitly "
        "opt out via `DETECTOR = None`, not silently trip the registry gap"
    )


def test_declared_scope_treats_detector_none_as_an_explicit_opt_out(tmp_path: Path):
    opt_out = tmp_path / "residual_check.py"
    opt_out.write_text("DETECTOR = None\n", encoding="utf-8")
    missing = tmp_path / "forgotten_check.py"
    missing.write_text("X = 1\n", encoding="utf-8")

    assert detectors._declared_scope(opt_out) is detectors._NOT_A_DETECTOR
    assert detectors._declared_scope(missing) is None


def test_discover_skips_detector_none_files_without_a_registry_finding(monkeypatch, tmp_path: Path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs" / "dashboard").mkdir(parents=True)
    (tmp_path / "pixi.toml").write_text("", encoding="utf-8")
    (tmp_path / "scripts" / "residual_check.py").write_text("DETECTOR = None\n", encoding="utf-8")
    monkeypatch.setattr(detectors, "ROOT", tmp_path)
    monkeypatch.setattr(
        detectors, "SEARCH",
        ((tmp_path / "scripts", "*_check.py"),
         (tmp_path / "docs" / "dashboard", "check_*.py")),
    )

    found, registry_findings = detectors.discover()

    assert found == []
    assert registry_findings == []
