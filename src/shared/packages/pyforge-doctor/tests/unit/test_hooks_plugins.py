"""Unit tests for ``pyforge.doctor.hooks`` (Story 17.1) -- every I/O matrix
row: default plugins on ``pyforge.core.hooks``, diagnose gather via the
plugin (atlas-only and directory checks), prescribe via the plugin, and
``SecondVerdictError`` when a Doctor plugin would publish a Warden-owned
verdict.

``sources.atlas.gather`` / ``sources.warden.gather`` /
``checks.env_hygiene.gather`` are monkeypatched like ``test_cli_diagnose.py``
so this suite never spawns a subprocess, opens MCP, or scans a real tree
for gather work. Directory-check rows still need a real ``tmp_path`` so
``Path.is_dir()`` matches the CLI's detection rule.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest
from pyforge.core.hooks import (
    ENTRY_POINT_GROUP,
    DummyPlugin,
    HookSpec,
    SecondVerdictError,
    publish_verdict,
)

from pyforge.doctor import hooks, prescribe
from pyforge.doctor.checks import env_hygiene
from pyforge.doctor.hooks import (
    GATHER_HOOK_SPEC,
    PRESCRIBE_HOOK_SPEC,
    DefaultGatherPlugin,
    DefaultPrescribePlugin,
    build_prescriptions,
    default_registry,
    gather_for_diagnose,
)
from pyforge.doctor.models import DoctorStatus, Finding, Partition, Prescription, Source
from pyforge.doctor.sources import atlas
from pyforge.doctor.sources import warden as warden_source

_DOCTOR_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _finding(source, check, status=DoctorStatus.WARN, evidence=None):
    return Finding(source=source, check=check, status=status, message="stub", evidence=evidence or {})


def _stub_atlas(monkeypatch, by_axis: dict[str, tuple[Finding, ...]]):
    def fake_gather(axis, *, target=None, **kwargs):
        return by_axis.get(axis, ())

    monkeypatch.setattr(atlas, "gather", fake_gather)


def _forbidden_directory_gather(target):
    raise AssertionError("must not gather engine/env checks when directory_checks is False")


def _action_text(pf: prescribe.PartitionedFinding) -> str:
    if pf.partition is Partition.ACTIONABLE:
        if pf.finding.status is DoctorStatus.OK:
            return pf.reason
        return f"address {pf.finding.check} ({pf.finding.source.value})"
    if pf.partition is Partition.BLOCKED:
        return f"blocked -- {pf.reason}"
    return f"accepted risk -- {pf.reason}"


def _expected_prescriptions(findings: tuple[Finding, ...]) -> tuple[Prescription, ...]:
    """Today's prescribe pipeline, assembled the same way Story 3.4 did."""
    partitioned = prescribe.partition(findings)
    ranked = prescribe.rank(partitioned)
    rank_by_finding = {id(rp.finding): (rp.rank, rp.rank_factors) for rp in ranked}
    out: list[Prescription] = []
    for pf in partitioned:
        rank_value, rank_factors = rank_by_finding.get(id(pf.finding), (None, None))
        safe_upgrade_target, safe_upgrade_reason = prescribe.recommend_safe_upgrade(pf.finding)
        out.append(
            Prescription(
                finding_ref=f"{pf.finding.source.value}:{pf.finding.check}",
                partition=pf.partition,
                rank=rank_value,
                rank_factors=rank_factors,
                action=_action_text(pf),
                root_cause=prescribe.name_root_cause(pf.finding, findings),
                safe_upgrade_target=safe_upgrade_target,
                safe_upgrade_reason=safe_upgrade_reason,
            )
        )
    return tuple(out)


def test_default_registry_registers_doctor_owned_gather_and_prescribe_plugins():
    registry = default_registry()
    gather_plugins = [p for p in registry.plugins if p.hook_spec == GATHER_HOOK_SPEC.name]
    prescribe_plugins = [p for p in registry.plugins if p.hook_spec == PRESCRIBE_HOOK_SPEC.name]
    assert len(gather_plugins) == 1
    assert len(prescribe_plugins) == 1
    assert gather_plugins[0].owner == "doctor"
    assert prescribe_plugins[0].owner == "doctor"
    assert isinstance(gather_plugins[0], DefaultGatherPlugin)
    assert isinstance(prescribe_plugins[0], DefaultPrescribePlugin)
    assert GATHER_HOOK_SPEC.owner == "doctor"
    assert PRESCRIBE_HOOK_SPEC.owner == "doctor"
    registry.register(DefaultGatherPlugin())
    registry.register(DefaultPrescribePlugin())
    assert len(registry.plugins) == 2


def test_pyproject_declares_default_plugins_on_canonical_core_hooks_group():
    data = tomllib.loads(_DOCTOR_PYPROJECT.read_text(encoding="utf-8"))
    groups = data["project"]["entry-points"]
    assert ENTRY_POINT_GROUP in groups
    assert "pyforge.doctor.hooks" not in groups
    assert "pyforge.doctor.plugins" not in groups
    declared = groups[ENTRY_POINT_GROUP]
    assert declared["doctor-gather"] == "pyforge.doctor.hooks:DefaultGatherPlugin"
    assert declared["doctor-prescribe"] == "pyforge.doctor.hooks:DefaultPrescribePlugin"


def test_gather_for_diagnose_matches_atlas_loop_when_directory_checks_are_off(
    monkeypatch,
):
    atlas_findings = (_finding(Source.STALENESS_REPORT, "pkg-a"),)
    _stub_atlas(monkeypatch, {"staleness": atlas_findings})
    monkeypatch.setattr(warden_source, "gather", _forbidden_directory_gather)
    monkeypatch.setattr(env_hygiene, "gather", _forbidden_directory_gather)

    target = "not-a-real-directory-xyz"
    expected: tuple[Finding, ...] = ()
    for axis in ("staleness", "cve"):
        expected += atlas.gather(axis, target=target)

    actual = gather_for_diagnose(target, directory_checks=False, axes=("staleness", "cve"))
    assert actual == expected == atlas_findings


def test_gather_for_diagnose_includes_warden_and_env_when_directory_checks_are_on(monkeypatch, tmp_path):
    atlas_findings = (_finding(Source.STALENESS_REPORT, "pkg-a"),)
    _stub_atlas(monkeypatch, {"staleness": atlas_findings})
    engine_finding = (_finding(Source.WARDEN_DOCTOR, "deptry", status=DoctorStatus.OK),)
    env_finding = (_finding(Source.ENV_HYGIENE, "credential-scan", status=DoctorStatus.OK),)
    monkeypatch.setattr(warden_source, "gather", lambda target: engine_finding)
    monkeypatch.setattr(env_hygiene, "gather", lambda target: env_finding)

    findings = gather_for_diagnose(str(tmp_path), directory_checks=True, axes=("staleness", "cve"))
    sources = {f.source for f in findings}
    assert Source.STALENESS_REPORT in sources
    assert Source.WARDEN_DOCTOR in sources
    assert Source.ENV_HYGIENE in sources
    assert atlas_findings[0] in findings


def test_build_prescriptions_matches_todays_pipeline():
    findings = (
        _finding(Source.STALENESS_REPORT, "pkg-a"),
        _finding(
            Source.CVE_WATCHER,
            "pkg-b",
            status=DoctorStatus.FAIL,
            evidence={"fix_available": False},
        ),
    )
    assert build_prescriptions(findings) == _expected_prescriptions(findings)


def test_prescribe_plugin_around_writes_prescriptions_from_findings():
    findings = (_finding(Source.CVE_WATCHER, "pkg-a", status=DoctorStatus.FAIL),)
    plugin = DefaultPrescribePlugin()
    context = {"findings": findings}
    plugin.call("around", context)
    assert context["prescriptions"] == _expected_prescriptions(findings)


def test_publish_verdict_on_warden_owned_spec_raises_second_verdict_error():
    plugin = DefaultGatherPlugin()
    warden_spec = HookSpec(name="pyforge.warden.pr-gate", owner="warden")
    with pytest.raises(SecondVerdictError):
        publish_verdict(warden_spec, plugin, {"gate": "fail"})
    prescribe_plugin = DefaultPrescribePlugin()
    with pytest.raises(SecondVerdictError):
        publish_verdict(warden_spec, prescribe_plugin, {"gate": "fail"})


def test_default_plugins_do_not_call_publish_verdict():
    source = Path(hooks.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    hits: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "publish_verdict":
            hits.append(node.lineno)
        elif isinstance(node, ast.Attribute) and node.attr == "publish_verdict":
            hits.append(node.lineno)
    assert not hits


def test_invoke_names_doctor_spec_so_core_dummy_is_never_run(monkeypatch):
    dummy = DummyPlugin()
    registry = default_registry()
    registry.register(dummy)
    monkeypatch.setattr(atlas, "gather", lambda axis, *, target=None, **kwargs: ())
    context = {
        "diagnose_target": "xyz",
        "directory_checks": False,
        "axes": ("staleness", "cve"),
        "findings": (),
    }
    registry.invoke("around", context, spec_name=GATHER_HOOK_SPEC.name)
    registry.invoke("around", context, spec_name=PRESCRIBE_HOOK_SPEC.name)
    assert dummy.calls == []
    registry.invoke("around", {}, spec_name="pyforge.core.example")
    assert dummy.calls == ["around"]


def test_gather_calls_atlas_gather_live_after_import(monkeypatch):
    """No import-time bind of ``gather`` -- a post-import monkeypatch applies."""
    seen: list[str] = []

    def fake_gather(axis, *, target=None, **kwargs):
        seen.append(axis)
        return ()

    monkeypatch.setattr(atlas, "gather", fake_gather)
    monkeypatch.setattr(warden_source, "gather", _forbidden_directory_gather)
    monkeypatch.setattr(env_hygiene, "gather", _forbidden_directory_gather)
    gather_for_diagnose("xyz", directory_checks=False, axes=("staleness", "cve"))
    assert seen == ["staleness", "cve"]
