"""Story 24.2 / spec-pyforge-scribe CAP-32 -- `scripts/bmad_estate_check.py`.

The wrapper's own contract: exit 0 when the committed catalog matches its sources
(proved against this checkout), 2 when the root carries no sources (never a false
green), and a JSON shape for the registry. The drift cases themselves are proved by
`pyforge-scribe/tests/unit/test_catalog_bmad_estate.py`, which owns the generator.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "bmad_estate_check.py"

pytest.importorskip("pyforge.scribe", reason="the scribe package is not installed in this environment")


def _load():
    spec = importlib.util.spec_from_file_location("bmad_estate_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_declares_repo_scope_for_the_registry() -> None:
    assert _load().DETECTOR == {"scope": "repo"}


def test_committed_catalog_matches_its_sources() -> None:
    proc = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok -- the catalog matches its sources" in proc.stdout


def test_missing_sources_are_could_not_run_never_green(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--json"], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "could-not-run" and payload["exit"] == 2
    assert any("could-not-run" in line for line in payload["findings"])
