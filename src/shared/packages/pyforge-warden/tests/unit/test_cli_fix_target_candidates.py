"""CLI wiring for Story 14.1 ``fixed_version_candidates`` merge."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from pyforge.warden.actuator import Actuation
from pyforge.warden.cli import main
from pyforge.warden.engines import OsvEngine

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects" / "vuln_critical"
FINDING_ID = "vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0"


def test_scan_merges_engine_fixed_version_candidates_into_actuator(monkeypatch, capsys):
    captured: dict[str, object] = {}

    def spy(findings, **kwargs):  # noqa: ANN001
        captured["fixed_version_candidates"] = kwargs.get("fixed_version_candidates")
        return Actuation(dry_run=True, outcomes=())

    monkeypatch.setattr("pyforge.warden.cli.run_actuator", spy)

    real_run = OsvEngine.run

    def osv_with_candidates(self, target, inventory):  # noqa: ANN001
        result = real_run(self, target, inventory)
        return replace(
            result,
            fixed_version_candidates=MappingProxyType(
                {FINDING_ID: ("1.0.1", "1.1.0"), **dict(result.fixed_version_candidates)}
            ),
        )

    monkeypatch.setattr(OsvEngine, "run", osv_with_candidates)

    capsys.readouterr()
    rc = main(["scan", str(FIXTURES), "--fix-prs-dry-run", "--format", "json"])
    assert rc == 1
    merged = captured.get("fixed_version_candidates")
    assert isinstance(merged, dict)
    assert merged.get(FINDING_ID) == ("1.0.1", "1.1.0")
