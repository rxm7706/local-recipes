"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_sources_ci_pause_drift.py``.

The two tests that validate a payload against steward's shipped ``ci-status-schema.json`` read it from the
repository, so they run here; every test that drives a recorded fixture through a fake bridge stays in the package
half (``test_sources_ci_pause_drift.py``). jsonschema is a hard dependency of pyforge-doctor (``pyproject.toml``
``dependencies``), so it is a plain import.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pyforge.doctor import cli_bridge
from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import ci_pause_drift

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "ci_pause_drift"
_ALL_FIXTURES = sorted(FIXTURES.glob("*.json"))


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    """Steward's shipped schema, read per run (never at import: the live-tree split guard)."""
    repo_root = Path(__file__).resolve().parents[6]
    schema_path = repo_root / "src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json"
    return Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("fixture_path", _ALL_FIXTURES, ids=lambda p: p.name)
def test_fixture_matches_ci_status_schema(validator: Draft202012Validator, fixture_path: Path) -> None:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.json_path)
    assert not errors, f"{fixture_path.name}: {[e.message for e in errors]}"


def test_partial_read_on_stdout(validator: Draft202012Validator, monkeypatch, tmp_path: Path) -> None:
    """Steward Story 103.7: a partial read prints its report, with partial and run_list_errors, on stdout."""
    payload = {
        **json.loads((FIXTURES / "partial_with_drift.json").read_text(encoding="utf-8")),
        "partial": True,
        "run_list_errors": [".github/workflows/platform-ci.yml: HTTP 404"],
    }
    assert not list(validator.iter_errors(payload))
    text = json.dumps(payload)

    def _run(argv, *, cwd, timeout=120.0):
        assert argv[-3:] == ["ci", "status", "--json"]
        return 1, text, ""

    monkeypatch.setattr(cli_bridge, "run_argv", _run)
    findings = ci_pause_drift.gather(tmp_path)
    warn_checks = [f.check for f in findings if f.status == DoctorStatus.WARN]
    assert "ci-pause-drift" in warn_checks
    assert "ci-pause-partial" in warn_checks
    assert "ci-pause-unobserved" not in [f.check for f in findings]
