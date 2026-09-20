"""Unit tests for ``seed.detect.referenced_deps`` (Story 11.5)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from pyforge.marshal.seed.detect.findings import FindingType, Severity
from pyforge.marshal.seed.detect.referenced_deps import referenced_dep_findings
from pyforge.marshal.seed.model.manifest import AppliesTo, ArtifactClass, Manifest, ManifestEntry


def _manifest(*entries: ManifestEntry) -> Manifest:
    from pyforge.marshal.seed.model.version import ModelVersion

    return Manifest(model_version=ModelVersion.parse("1.0.0"), never_write=(), entries=tuple(entries))


def _referenced(entry_id: str, pin: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.REFERENCED,
        path="n/a",
        applies_to=AppliesTo.BOTH,
        rationale="test",
        pin=pin,
    )


def test_missing_cli_tool_emits_referenced_dep_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: None)
    manifest = _manifest(_referenced("copier", ">=9.17,<10"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert findings[0].type is FindingType.REFERENCED_DEP_MISSING
    assert findings[0].severity is Severity.DRIFT
    assert findings[0].path == "copier"
    assert "not installed" in findings[0].message


def test_below_floor_version_emits_referenced_dep_missing(tmp_path: Path, monkeypatch):
    class _Result:
        returncode = 0
        stdout = "copier 9.0.0"
        stderr = ""

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "copier")
    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run",
        lambda *args, **kwargs: _Result(),
    )
    manifest = _manifest(_referenced("copier", ">=9.17,<10"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert "below manifest floor" in findings[0].message


def test_satisfied_pin_produces_no_finding(tmp_path: Path, monkeypatch):
    class _Result:
        returncode = 0
        stdout = "copier 9.18.0"
        stderr = ""

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "copier")
    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run",
        lambda *args, **kwargs: _Result(),
    )
    manifest = _manifest(_referenced("copier", ">=9.17,<10"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert findings == ()


def test_bmad_method_reads_manifest_yaml(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: None)
    config_dir = tmp_path / "_bmad" / "_config"
    config_dir.mkdir(parents=True)
    (config_dir / "manifest.yaml").write_text(
        yaml.safe_dump({"installation": {"version": "6.10.0"}}),
        encoding="utf-8",
    )
    manifest = _manifest(_referenced("bmad-method", ">=6.11.0"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "bmad-method"


def test_doctor_delegation_when_json_returned(tmp_path: Path, monkeypatch):
    payload = [{"artifact_id": "pixi", "message": "installed pixi 0.1.0 is below floor >=0.76.1"}]

    class _Result:
        returncode = 1
        stdout = json.dumps(payload)
        stderr = ""

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "doctor")
    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run",
        lambda *args, **kwargs: _Result(),
    )
    manifest = _manifest(_referenced("pixi", ">=0.76.1"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert findings[0].message.startswith("[doctor]")
    assert findings[0].path == "pixi"
