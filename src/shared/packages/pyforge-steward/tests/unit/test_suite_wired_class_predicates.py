"""Story 31.2 — pipeline-truth wired-or-not is class-correct (CAP-2)."""

from __future__ import annotations

from pathlib import Path

from pyforge.steward.provision import _SKIPPED_MODULES, _SUPPORTED_MODULES
from pyforge.steward.suite import (
    INSTALL_CLASS_CLI,
    INSTALL_CLASS_INSTALLER_TREE,
    INSTALL_CLASS_OWN_INSTALLER,
    INSTALL_CLASS_PLUGIN_PATH,
    INSTALL_CLASS_RUNNER_HOME,
    INSTALL_CLASS_SCAFFOLD_NA,
    INSTALL_CLASS_SKIP,
    INSTALL_CLASS_VSCODE_EXTENSION,
    SUITE_PACKAGES,
    SuitePackageDef,
    format_pipeline_truth,
    probe_wired,
    build_pipeline_truth_report,
    ProbeHooks,
    StageProbe,
)


_SIX_CLASSES = {
    "bmad-method": INSTALL_CLASS_INSTALLER_TREE,
    "bmad-loop": INSTALL_CLASS_RUNNER_HOME,
    "bmad-module-skill-forge": INSTALL_CLASS_OWN_INSTALLER,
    "bmad-labs-skills": INSTALL_CLASS_PLUGIN_PATH,
    "bmad-dashboard": INSTALL_CLASS_VSCODE_EXTENSION,
    "bmad-module-template": INSTALL_CLASS_SCAFFOLD_NA,
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pixi.toml").is_file() and (parent / "_bmad-output").is_dir():
            return parent
    raise AssertionError("could not locate repository root from test file")


def _by_name() -> dict[str, SuitePackageDef]:
    return {p.name: p for p in SUITE_PACKAGES}


def test_six_non_module_pieces_declare_playbook_classes():
    roster = _by_name()
    for name, install_class in _SIX_CLASSES.items():
        assert roster[name].install_class == install_class, name
    assert roster["mybmad-dashboard"].install_class == INSTALL_CLASS_VSCODE_EXTENSION
    assert roster["bmad-eval-quality"].install_class == INSTALL_CLASS_CLI


def test_template_never_reports_wired_even_with_module_census_hits(tmp_path: Path):
    (tmp_path / "_bmad" / "core").mkdir(parents=True)
    (tmp_path / "_bmad" / "bmm").mkdir(parents=True)
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "bmad-loop-setup").mkdir()
    (tmp_path / "docs" / "dashboard").mkdir(parents=True)
    pkg = _by_name()["bmad-module-template"]
    probe = probe_wired(tmp_path, pkg)
    assert probe.value == "n/a"
    assert probe.value != "wired"
    assert pkg.install_class == INSTALL_CLASS_SCAFFOLD_NA


def test_loop_skill_census_alone_is_not_wired(tmp_path: Path):
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "bmad-loop-setup").mkdir()
    probe = probe_wired(tmp_path, _by_name()["bmad-loop"])
    assert probe.value != "wired"
    assert probe.value == "missing"


def test_loop_runner_home_is_provisionable_when_locator_exists(tmp_path: Path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")
    probe = probe_wired(tmp_path, _by_name()["bmad-loop"])
    assert probe.value == "provisionable"


def test_labs_skill_census_alone_is_not_wired(tmp_path: Path):
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "ai-multimodal").mkdir()
    (skills / "ultrathink-protocol").mkdir()
    probe = probe_wired(tmp_path, _by_name()["bmad-labs-skills"])
    assert probe.value != "wired"
    assert probe.value == "missing"


def test_labs_plugin_path_documented_from_playbook(tmp_path: Path):
    playbook = (
        tmp_path
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
        / "spec-bmad-suite-install-class-wiring/install-class-playbook.md"
    )
    playbook.parent.mkdir(parents=True)
    playbook.write_text("npx skills add bmad-labs/skills\n", encoding="utf-8")
    probe = probe_wired(tmp_path, _by_name()["bmad-labs-skills"])
    assert probe.value == "documented"
    assert probe.value != "wired"


def test_dashboard_docs_surface_alone_is_not_wired(tmp_path: Path):
    (tmp_path / "docs" / "dashboard").mkdir(parents=True)
    (tmp_path / "presentations" / "agentic-sdlc").mkdir(parents=True)
    probe = probe_wired(tmp_path, _by_name()["bmad-dashboard"])
    assert probe.value != "wired"
    assert probe.value == "missing"


def test_dashboard_pixi_task_is_runnable(tmp_path: Path):
    (tmp_path / "pixi.toml").write_text(
        "[feature.bmad-ui.tasks.bmad-dashboard-install]\ncmd = \"bmad-dashboard-install\"\n",
        encoding="utf-8",
    )
    probe = probe_wired(tmp_path, _by_name()["bmad-dashboard"])
    assert probe.value == "runnable"


def test_method_installer_tree_present(tmp_path: Path):
    (tmp_path / "_bmad" / "core").mkdir(parents=True)
    (tmp_path / "_bmad" / "bmm").mkdir(parents=True)
    probe = probe_wired(tmp_path, _by_name()["bmad-method"])
    assert probe.value == "present"
    assert probe.value != "wired"


def test_cap3_five_and_skip_class_untouched():
    assert set(_SUPPORTED_MODULES) == {
        "bmb",
        "tea",
        "cis",
        "utility-skills",
        "manticore",
    }
    assert "wds" in _SKIPPED_MODULES
    # WDS left the roster 2026-09-05 (Story 45.1); the skip class itself stays.
    assert "bmad-method-wds-expansion" not in _by_name()
    retired = SuitePackageDef(name="retired-module", install_class=INSTALL_CLASS_SKIP)
    assert probe_wired(Path("."), retired).value == "skip"
    assert "skf" not in _SUPPORTED_MODULES


def test_cli_class_is_runnable_only_when_bin_on_path(tmp_path: Path, monkeypatch):
    eq = _by_name()["bmad-eval-quality"]
    monkeypatch.setenv("PATH", str(tmp_path))
    missing = probe_wired(Path("."), eq)
    assert missing.value == "missing"
    assert missing.ok is True
    exe = tmp_path / "eval-quality"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(0o755)
    runnable = probe_wired(Path("."), eq)
    assert runnable.value == "runnable"
    assert str(exe) in runnable.detail


def test_report_names_each_of_the_six_by_class(tmp_path: Path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / "_bmad" / "core").mkdir(parents=True)
    (tmp_path / "_bmad" / "bmm").mkdir(parents=True)
    playbook = (
        tmp_path
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
        / "spec-bmad-suite-install-class-wiring/install-class-playbook.md"
    )
    playbook.parent.mkdir(parents=True)
    playbook.write_text("npx skills add bmad-labs/skills\n", encoding="utf-8")
    (tmp_path / "pixi.toml").write_text(
        "[feature.bmad-ui.tasks.bmad-dashboard-install]\ncmd = \"x\"\n"
        "[feature.bmad-ui.tasks.mybmad]\ncmd = \"y\"\n",
        encoding="utf-8",
    )

    def _wired(repo: Path, pkg: SuitePackageDef) -> StageProbe:
        return probe_wired(repo, pkg)

    hooks = ProbeHooks(
        npm=lambda _n: "1.0.0",
        github=lambda *_a: "1.0.0",
        channel=lambda _p: "1.0.0",
        recipe=lambda _r, _p: "1.0.0",
        installed=lambda _r, _p: "1.0.0",
        wired=_wired,
    )
    report = build_pipeline_truth_report(tmp_path, hooks=hooks)
    by_name = {p.name: p for p in report.packages}
    for name, install_class in _SIX_CLASSES.items():
        row = by_name[name]
        assert row.install_class == install_class
        assert row.wired.value != "wired"
    assert by_name["bmad-module-template"].wired.value == "n/a"
    text = format_pipeline_truth(report, as_json=False)
    for token in _SIX_CLASSES.values():
        assert token in text


def test_baseline_json_names_install_class_for_the_six(capsys):
    from pyforge.steward.cli import EXIT_OK, main
    import json

    rc = main(["suite", "pipeline-truth", "--baseline", "--json"])
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    by_name = {p["name"]: p for p in payload["packages"]}
    for name, install_class in _SIX_CLASSES.items():
        assert by_name[name]["install_class"] == install_class
    assert by_name["bmad-module-template"]["wired"]["value"] == "n/a"


def test_live_repo_names_six_and_template_is_n_a():
    repo = _repo_root()
    roster = _by_name()
    for name, install_class in _SIX_CLASSES.items():
        probe = probe_wired(repo, roster[name])
        assert probe.value != "wired", name
        if name == "bmad-module-template":
            assert probe.value == "n/a"
        assert roster[name].install_class == install_class
