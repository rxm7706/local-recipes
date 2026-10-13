"""Unit tests for ``seed.detect.referenced_deps`` (Story 11.5, Story 99.1)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import yaml
from pyforge.core.process import ProcessError

from pyforge.marshal.seed.detect.findings import FindingType, Severity
from pyforge.marshal.seed.detect.referenced_deps import (
    _CLI_TIMEOUT_S,
    referenced_dep_findings,
)
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


def test_nonzero_cli_exit_emits_not_installed(tmp_path: Path, monkeypatch):
    class _Result:
        returncode = 1
        stdout = ""
        stderr = "error"

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "copier")
    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run",
        lambda *args, **kwargs: _Result(),
    )
    manifest = _manifest(_referenced("copier", ">=9.17,<10"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert "not installed" in findings[0].message


def test_cli_probe_timeout_emits_timeout_message_not_not_installed(tmp_path: Path, monkeypatch):
    def _timeout(*args, **kwargs):
        raise ProcessError("command timed out after 5.0s: copier --version")

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "copier")
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run", _timeout)
    manifest = _manifest(_referenced("copier", ">=9.4"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert findings[0].type is FindingType.REFERENCED_DEP_MISSING
    assert findings[0].severity is Severity.DRIFT
    assert "did not answer within" in findings[0].message
    assert str(_CLI_TIMEOUT_S) in findings[0].message
    assert "not installed" not in findings[0].message
    assert "`copier --version`" in findings[0].message


def _sleeping_run_factory(sleep_s: float = 1.0):
    def _run(*args, **kwargs):
        time.sleep(sleep_s)
        return type("_R", (), {"returncode": 0, "stdout": "copier 9.18.0", "stderr": ""})()

    return _run


def _four_cli_manifest() -> Manifest:
    return _manifest(
        _referenced("copier", ">=9.17,<10"),
        _referenced("pixi", ">=0.76.1"),
        _referenced("tmux", ">=3.0"),
        _referenced("bmad-loop", ">=0.12.0"),
    )


def test_probes_run_in_parallel_with_doctor_on_path(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "doctor")
    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run",
        _sleeping_run_factory(1.0),
    )
    manifest = _four_cli_manifest()

    started = time.perf_counter()
    referenced_dep_findings(manifest, tmp_path)
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, f"expected parallel probes under 2.0 s, got {elapsed:.2f}s"


def test_probes_run_in_parallel_without_doctor(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.shutil.which",
        lambda name: None if name == "doctor" else f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run",
        _sleeping_run_factory(1.0),
    )
    manifest = _four_cli_manifest()

    started = time.perf_counter()
    referenced_dep_findings(manifest, tmp_path)
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, f"expected parallel probes under 2.0 s, got {elapsed:.2f}s"


def test_doctor_findings_win_over_local_probes(tmp_path: Path, monkeypatch):
    payload = [{"artifact_id": "pixi", "message": "installed pixi 0.1.0 is below floor >=0.76.1"}]

    class _DoctorResult:
        returncode = 1
        stdout = json.dumps(payload)
        stderr = ""

    class _LocalWouldFail:
        returncode = 0
        stdout = "copier 9.18.0"
        stderr = ""

    def _run(*args, **kwargs):
        argv = args[1] if len(args) >= 2 else args[0]
        if "pyforge.doctor.sources" in " ".join(str(a) for a in argv):
            return _DoctorResult()
        return _LocalWouldFail()

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "doctor")
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run", _run)
    manifest = _four_cli_manifest()

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "pixi"
    assert findings[0].message.startswith("[doctor]")


def test_local_findings_stay_in_manifest_order_when_probes_finish_out_of_order(tmp_path: Path, monkeypatch):
    finish_order: list[str] = []
    version_lines = {
        "copier": "copier 9.0.0",
        "pixi": "pixi 0.1.0",
        "tmux": "tmux 2.0",
        "bmad-loop": "bmad-loop 0.1.0",
    }

    def _run(*args, **kwargs):
        argv = args[1] if len(args) >= 2 else args[0]
        cmd = argv[0] if argv else ""
        if cmd in version_lines:
            delays = {"bmad-loop": 0.05, "tmux": 0.04, "pixi": 0.03, "copier": 0.01}
            time.sleep(delays[cmd])
            finish_order.append(cmd)
            stdout = version_lines[cmd]
            return type("_R", (), {"returncode": 0, "stdout": stdout, "stderr": ""})()
        raise AssertionError(f"unexpected argv: {argv!r}")

    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.shutil.which",
        lambda name: None if name == "doctor" else f"/usr/bin/{name}",
    )
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run", _run)
    manifest = _four_cli_manifest()

    findings = referenced_dep_findings(manifest, tmp_path)

    assert [f.path for f in findings] == ["copier", "pixi", "tmux", "bmad-loop"]
    assert finish_order.index("copier") < finish_order.index("bmad-loop")


def _conda_meta(tmp_path: Path, package: str, version: str, env_name: str = "default") -> None:
    meta_dir = tmp_path / ".pixi" / "envs" / env_name / "conda-meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / f"{package}-{version}-0.json").write_text("{}", encoding="utf-8")


def test_conda_referenced_package_satisfied_pin(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: None)
    _conda_meta(tmp_path, "headroom", "0.5.0")
    manifest = _manifest(_referenced("headroom", ">=0.5.0,<1"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert findings == ()


def test_conda_referenced_package_picks_highest_version(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: None)
    _conda_meta(tmp_path, "headroom", "0.4.0", env_name="a")
    _conda_meta(tmp_path, "headroom", "0.6.0", env_name="b")
    manifest = _manifest(_referenced("headroom", ">=0.5.0,<1"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert findings == ()


def test_conda_referenced_package_missing_emits_finding(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: None)
    manifest = _manifest(_referenced("headroom", ">=0.5.0"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "headroom"
    assert "not installed" in findings[0].message


def test_bmad_method_missing_manifest_yaml(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: None)
    manifest = _manifest(_referenced("bmad-method", ">=6.0.0"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert "not installed" in findings[0].message


def test_bmad_method_rejects_non_dict_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: None)
    config_dir = tmp_path / "_bmad" / "_config"
    config_dir.mkdir(parents=True)
    (config_dir / "manifest.yaml").write_text("just-a-scalar\n", encoding="utf-8")
    manifest = _manifest(_referenced("bmad-method", ">=6.0.0"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert "not installed" in findings[0].message


def test_bmad_method_invalid_version_treated_as_below_floor(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: None)
    config_dir = tmp_path / "_bmad" / "_config"
    config_dir.mkdir(parents=True)
    (config_dir / "manifest.yaml").write_text(
        yaml.safe_dump({"installation": {"version": "not-a-pep440-version"}}),
        encoding="utf-8",
    )
    manifest = _manifest(_referenced("bmad-method", ">=6.0.0"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert "below manifest floor" in findings[0].message


def test_cli_process_error_without_timeout_emits_not_installed(tmp_path: Path, monkeypatch):
    def _fail(*args, **kwargs):
        raise ProcessError("copier: command not found")

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "copier")
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run", _fail)
    manifest = _manifest(_referenced("copier", ">=9.17,<10"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert len(findings) == 1
    assert "not installed" in findings[0].message


def test_doctor_exit_two_falls_back_to_local_cli_probe(tmp_path: Path, monkeypatch):
    class _DoctorUnknown:
        returncode = 2
        stdout = ""
        stderr = ""

    class _CopierOk:
        returncode = 0
        stdout = "copier 9.18.0"
        stderr = ""

    def _run(*args, **kwargs):
        argv = args[1] if len(args) >= 2 else args[0]
        if "pyforge.doctor.sources" in " ".join(str(a) for a in argv):
            return _DoctorUnknown()
        return _CopierOk()

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "doctor")
    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run", _run)
    manifest = _manifest(_referenced("copier", ">=9.17,<10"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert findings == ()


def test_doctor_invalid_json_falls_back_to_local(tmp_path: Path, monkeypatch):
    class _DoctorBadJson:
        returncode = 0
        stdout = "{not-json"
        stderr = ""

    monkeypatch.setattr("pyforge.marshal.seed.detect.referenced_deps.shutil.which", lambda _name: "doctor")
    monkeypatch.setattr(
        "pyforge.marshal.seed.detect.referenced_deps.PosixProcess.run",
        lambda *args, **kwargs: _DoctorBadJson(),
    )
    _conda_meta(tmp_path, "headroom", "0.5.0")
    manifest = _manifest(_referenced("headroom", ">=0.5.0"))

    findings = referenced_dep_findings(manifest, tmp_path)

    assert findings == ()


def test_doctor_payload_skips_malformed_items(tmp_path: Path, monkeypatch):
    payload = [
        "not-a-dict",
        {"artifact_id": "", "message": "skip empty id"},
        {"artifact_id": "pixi", "message": ""},
        {"artifact_id": "pixi", "message": "installed pixi 0.1.0 is below floor >=0.76.1"},
    ]

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
    assert findings[0].path == "pixi"
