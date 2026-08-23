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

    # WDS explicit skip — wired stage is skip, not a wired drift.
    wds = by_name["bmad-method-wds-expansion"]
    assert wds.wired.value == "skip"
    assert "wired" not in wds.drifts

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
