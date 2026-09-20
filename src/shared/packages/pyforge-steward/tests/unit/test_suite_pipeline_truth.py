"""Story 15.1 — CAP-1 suite pipeline-truth (whole-pipeline report)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.steward.cli import EXIT_OK, main
from pyforge.steward.suite import (
    BASELINE_2026_08_22,
    BASELINE_ID_2026_08_22,
    SUITE_PACKAGES,
    ProbeHooks,
    StageProbe,
    SuiteDuty,
    SuitePackageDef,
    build_pipeline_truth_report,
    hooks_from_baseline,
    name_drifts,
    PackageTruth,
    fetch_github_latest,
    read_recipe_version,
)


def test_suite_roster_is_exactly_thirteen():
    assert len(SUITE_PACKAGES) == 13
    assert len(BASELINE_2026_08_22) == 13
    assert {p.name for p in SUITE_PACKAGES} == set(BASELINE_2026_08_22)


def test_baseline_2026_08_22_reproduces_research_matrix_shape(tmp_path: Path):
    """Fixture/recorded baseline reproduces the 2026-08-22 research matrix."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")

    report = build_pipeline_truth_report(
        tmp_path,
        hooks=hooks_from_baseline(BASELINE_2026_08_22),
        baseline_id=BASELINE_ID_2026_08_22,
    )

    assert report.baseline_id == BASELINE_ID_2026_08_22
    assert len(report.packages) == 13

    by_name = {p.name: p for p in report.packages}

    # Every package's stage values must match the recorded baseline row.
    for name, expected in BASELINE_2026_08_22.items():
        row = by_name[name]
        assert row.upstream_npm.value == expected["upstream_npm"], name
        assert row.upstream_github.value == expected["upstream_github"], name
        assert row.recipe.value == expected["recipe"], name
        assert row.channel.value == expected["channel"], name
        assert row.installed.value == expected["installed"], name
        assert row.wired.value == expected["wired"], name

    # Shared-GitHub collision must not steal mybmad's recorded upstream.
    assert by_name["mybmad-dashboard"].upstream_github.value == "0.1.0"
    assert by_name["bmad-dashboard"].upstream_github.value == "1.2.2"

    # Channel relic that motivated CAP-1 / CAP-5.
    method = by_name["bmad-method"]
    assert "channel" in method.drifts

    # TEA: npm current, GitHub tag ahead (watch).
    tea = by_name["bmad-method-test-architecture-enterprise"]
    assert "upstream_npm_github_divergence" in tea.drifts
    assert "wired" in tea.drifts

    # npm-stale / GitHub-canonical.
    assert "upstream_npm_github_divergence" in by_name["bmad-builder"].drifts

    # npm-invisible package still reports GitHub (skipped npm, not failed).
    loop = by_name["bmad-loop"]
    assert loop.upstream_npm.value is None
    assert loop.upstream_npm.ok is True

    # eval-quality (joined 2026-09-05 in WDS's seat): bare CLI on PATH after the
    # same-day channel upload + pixi pin -> "runnable" settles the wired stage;
    # the 0.2.0.dev0 recipe is ahead of upstream's v0.1.0, not a recipe drift.
    eq = by_name["bmad-eval-quality"]
    assert eq.wired.value == "runnable"
    assert "wired" not in eq.drifts
    assert "recipe" not in eq.drifts
    assert eq.drifts == ()
    assert "bmad-method-wds-expansion" not in by_name

    # Unwired set from the Dream.
    for name in (
        "bmad-builder",
        "bmad-creative-intelligence-suite",
        "bmad-utility-skills",
        "bmad-manticore",
        "bmad-method-test-architecture-enterprise",
    ):
        assert by_name[name].wired.value == "unwired"


def test_fail_open_probe_never_aborts_whole_report(tmp_path: Path):
    """One probe raising / returning None must not stop the other 12 packages."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")

    def boom_npm(name: str) -> str | None:
        if name == "bmad-method":
            raise RuntimeError("npm down")
        return "9.9.9"

    def none_github(_owner_repo: str, _package: str | None = None) -> str | None:
        return None

    hooks = ProbeHooks(
        npm=boom_npm,
        github=none_github,
        channel=lambda _p: None,
        recipe=lambda _r, _p: "1.0.0",
        installed=lambda _r, _p: None,
        wired=lambda _r, pkg: StageProbe(value="unwired", ok=True),
    )
    report = build_pipeline_truth_report(tmp_path, hooks=hooks)
    assert len(report.packages) == 13
    method = next(p for p in report.packages if p.name == "bmad-method")
    assert method.upstream_npm.ok is False
    # Sibling package still present with a successful npm probe.
    forge = next(p for p in report.packages if p.name == "bmad-module-skill-forge")
    assert forge.upstream_npm.value == "9.9.9"
    assert forge.upstream_npm.ok is True


def test_cli_pipeline_truth_baseline_json(capsys):
    rc = main(["suite", "pipeline-truth", "--baseline", "--json"])
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["package_count"] == 13
    assert payload["baseline_id"] == BASELINE_ID_2026_08_22
    names = [p["name"] for p in payload["packages"]]
    assert names == [p.name for p in SUITE_PACKAGES]
    method = next(p for p in payload["packages"] if p["name"] == "bmad-method")
    assert method["channel"]["value"] == "6.3.0"
    assert "channel" in method["drifts"]
    mybmad = next(p for p in payload["packages"] if p["name"] == "mybmad-dashboard")
    assert mybmad["upstream_github"]["value"] == "0.1.0"


def test_suite_duty_lists_verb_when_bare():
    result = SuiteDuty().run(type("NS", (), {"suite_verb": None})())
    assert result.ok is True
    assert "pipeline-truth" in result.summary


def test_name_drifts_channel_and_wired():
    pkg = PackageTruth(
        name="x",
        upstream_npm=StageProbe("6.11.0", True),
        upstream_github=StageProbe("6.11.0", True),
        recipe=StageProbe("6.11.0", True),
        channel=StageProbe("6.3.0", True),
        installed=StageProbe("6.11.0", True),
        wired=StageProbe("unwired", True),
    )
    assert name_drifts(pkg) == ("channel", "wired")


def test_name_drifts_recipe_when_behind_upstream():
    pkg = PackageTruth(
        name="x",
        upstream_npm=StageProbe("2.0.0", True),
        upstream_github=StageProbe("2.0.0", True),
        recipe=StageProbe("1.0.0", True),
        channel=StageProbe("1.0.0", True),
        installed=StageProbe("1.0.0", True),
        wired=StageProbe("wired", True),
    )
    assert "recipe" in name_drifts(pkg)


def test_name_drifts_installed_when_behind_recipe():
    pkg = PackageTruth(
        name="x",
        upstream_npm=StageProbe("2.0.0", True),
        upstream_github=StageProbe("2.0.0", True),
        recipe=StageProbe("2.0.0", True),
        channel=StageProbe("2.0.0", True),
        installed=StageProbe("1.0.0", True),
        wired=StageProbe("wired", True),
    )
    assert "installed" in name_drifts(pkg)


def test_name_drifts_wired_when_probe_failed():
    pkg = PackageTruth(
        name="x",
        upstream_npm=StageProbe("1.0.0", True),
        upstream_github=StageProbe("1.0.0", True),
        recipe=StageProbe("1.0.0", True),
        channel=StageProbe("1.0.0", True),
        installed=StageProbe("1.0.0", True),
        wired=StageProbe(None, False, detail="boom"),
    )
    assert "wired" in name_drifts(pkg)


def test_wired_census_detects_bmad_dirs(tmp_path: Path):
    from pyforge.steward.suite import probe_wired

    (tmp_path / "_bmad" / "core").mkdir(parents=True)
    (tmp_path / "_bmad" / "bmm").mkdir(parents=True)
    pkg = SuitePackageDef(name="bmad-method", wire_bmad_dirs=("core", "bmm"))
    assert probe_wired(tmp_path, pkg).value == "wired"


def test_wired_census_detects_skill_prefix(tmp_path: Path):
    from pyforge.steward.suite import probe_wired

    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "bmad-loop-setup").mkdir()
    pkg = SuitePackageDef(name="bmad-loop", wire_skill_prefixes=("bmad-loop-",))
    assert probe_wired(tmp_path, pkg).value == "wired"


def test_read_recipe_version_rejects_yaml_float(tmp_path: Path):
    recipe = tmp_path / "recipes" / "pkg"
    recipe.mkdir(parents=True)
    (recipe / "recipe.yaml").write_text(
        "context:\n  version: 1.2\n", encoding="utf-8"
    )
    assert read_recipe_version(tmp_path, "pkg") is None


def test_read_recipe_version_accepts_int(tmp_path: Path):
    recipe = tmp_path / "recipes" / "pkg"
    recipe.mkdir(parents=True)
    (recipe / "recipe.yaml").write_text(
        "context:\n  version: 2\n", encoding="utf-8"
    )
    assert read_recipe_version(tmp_path, "pkg") == "2"


def test_fetch_github_latest_non_dict_body_fail_open(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'["not", "a", "mapping"]'

    monkeypatch.setattr(
        "pyforge.steward.suite.urllib.request.urlopen",
        lambda *a, **k: _Resp(),
    )
    assert fetch_github_latest("owner/repo", "some-pkg") is None


# ── Story 46.9: installer-tree `installed` stage reads the APPLIED core ────


def _write_manifest(repo: Path, version: str) -> None:
    manifest = repo / "_bmad" / "_config" / "manifest.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f"installation:\n  version: {version}\n", encoding="utf-8"
    )


def _write_conda_meta(repo: Path, version: str) -> None:
    meta_dir = repo / ".pixi" / "envs" / "pyforge-guild" / "conda-meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / f"bmad-method-{version}-h98f672e_0.json").write_text("{}", encoding="utf-8")


def test_read_applied_core_version_reads_manifest(tmp_path: Path):
    from pyforge.steward.suite import read_applied_core_version

    _write_manifest(tmp_path, "6.11.0")
    assert read_applied_core_version(tmp_path) == "6.11.0"


def test_read_applied_core_version_absent_manifest_fails_open(tmp_path: Path):
    from pyforge.steward.suite import read_applied_core_version

    assert read_applied_core_version(tmp_path) is None


def test_read_applied_core_version_malformed_yaml_fails_open(tmp_path: Path):
    from pyforge.steward.suite import read_applied_core_version

    manifest = tmp_path / "_bmad" / "_config" / "manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("installation: [this is not a mapping\n", encoding="utf-8")
    assert read_applied_core_version(tmp_path) is None


def test_installer_tree_installed_stage_manifest_only_no_conda_meta(tmp_path: Path):
    """AC: manifest-only, no conda-meta -> installed = 6.11.0, ok=True, no drift."""
    from pyforge.steward.suite import ProbeHooks, _installer_tree_installed_stage

    _write_manifest(tmp_path, "6.11.0")
    stage = _installer_tree_installed_stage(tmp_path, "bmad-method", hooks=ProbeHooks())
    assert stage.value == "6.11.0"
    assert stage.ok is True
    assert stage.detail is None


def test_installer_tree_installed_stage_applied_wins_on_disagreement(tmp_path: Path):
    """AC: the exact 2026-09-05 replay -- manifest 6.11.0, conda-meta 6.12.0 ->
    applied (6.11.0) wins, detail names both, name_drifts gains
    core_applied_env_drift."""
    from pyforge.steward.suite import (
        PackageTruth,
        ProbeHooks,
        StageProbe,
        _installer_tree_installed_stage,
        name_drifts,
    )

    _write_manifest(tmp_path, "6.11.0")
    _write_conda_meta(tmp_path, "6.12.0")
    stage = _installer_tree_installed_stage(tmp_path, "bmad-method", hooks=ProbeHooks())
    assert stage.value == "6.11.0"
    assert stage.ok is True
    assert "6.11.0" in stage.detail
    assert "6.12.0" in stage.detail
    assert "core-applied-env-drift" in stage.detail

    pkg = PackageTruth(
        name="bmad-method",
        upstream_npm=StageProbe("6.11.0", True),
        upstream_github=StageProbe("6.11.0", True),
        recipe=StageProbe("6.11.0", True),
        channel=StageProbe("6.11.0", True),
        installed=stage,
        wired=StageProbe("present", True),
    )
    assert "core_applied_env_drift" in name_drifts(pkg)


def test_installer_tree_installed_stage_falls_back_when_manifest_absent(tmp_path: Path):
    """AC: manifest absent -> unchanged conda-meta fallback, no new drift."""
    from pyforge.steward.suite import (
        PackageTruth,
        ProbeHooks,
        StageProbe,
        _installer_tree_installed_stage,
        name_drifts,
    )

    _write_conda_meta(tmp_path, "6.12.0")
    stage = _installer_tree_installed_stage(tmp_path, "bmad-method", hooks=ProbeHooks())
    assert stage.value == "6.12.0"
    assert stage.ok is True
    assert stage.detail is None

    pkg = PackageTruth(
        name="bmad-method",
        upstream_npm=StageProbe("6.12.0", True),
        upstream_github=StageProbe("6.12.0", True),
        recipe=StageProbe("6.12.0", True),
        channel=StageProbe("6.12.0", True),
        installed=stage,
        wired=StageProbe("present", True),
    )
    assert "core_applied_env_drift" not in name_drifts(pkg)


def test_installer_tree_installed_stage_live_repo_is_a_noop_today():
    """AC: this repo's OWN real state (both present, currently agreeing) ->
    the installed stage reports the agreed version, no drift -- a live,
    non-fixture confirmation that today's fix changes nothing for the
    currently healthy state."""
    from pyforge.steward.suite import ProbeHooks, _installer_tree_installed_stage, repo_root

    repo = repo_root()
    stage = _installer_tree_installed_stage(repo, "bmad-method", hooks=ProbeHooks())
    assert stage.ok is True
    assert stage.value is not None
    assert stage.detail is None


def test_build_package_truth_installer_tree_class_uses_new_helper(tmp_path: Path):
    """`build_package_truth` branches the installed-stage computation on
    `install_class == INSTALL_CLASS_INSTALLER_TREE` -- every other class's
    computation is byte-for-byte unchanged."""
    from pyforge.steward.suite import (
        INSTALL_CLASS_INSTALLER_TREE,
        ProbeHooks,
        SuitePackageDef,
        build_package_truth,
    )

    _write_manifest(tmp_path, "6.11.0")
    _write_conda_meta(tmp_path, "6.12.0")
    pkg = SuitePackageDef(
        name="bmad-method",
        wire_bmad_dirs=("core", "bmm"),
        install_class=INSTALL_CLASS_INSTALLER_TREE,
    )
    offline_hooks = ProbeHooks(
        npm=lambda _n: None,
        github=lambda *_a: None,
        channel=lambda _p: None,
    )
    truth = build_package_truth(tmp_path, pkg, hooks=offline_hooks)
    assert truth.installed.value == "6.11.0"
    assert "core_applied_env_drift" in truth.drifts
