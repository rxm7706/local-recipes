"""Tests for ``scripts/detectors.py``'s ``_doctor_sources()`` helper (Story 6.2).

Two branches, mirroring the spec's I/O & Edge-Case Matrix:

- ``pyforge.doctor`` importable -- ``(True, rows)``, one row per
  ``sources.REGISTRY`` entry, carrying ``scope``/``subject_station``/
  ``owning_station``.
- ``pyforge.doctor`` NOT importable -- ``(False, [])``, never a crash, never
  a registry finding.

Proves ``scripts/detectors.py``'s enumeration survives ``pyforge-doctor``
being absent from the active environment (the AC's own "not importable in
the active environment" scenario), without requiring the package to
actually be uninstalled to test it, and that the caller can always tell
"zero sources" apart from "the package isn't here" via the leading `bool`.
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
# `docs/dashboard/generate.py` reaches its own scripts/ siblings.
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
