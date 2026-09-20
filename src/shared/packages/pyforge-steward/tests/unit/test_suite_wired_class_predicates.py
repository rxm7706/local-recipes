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
    ProbeHooks,
    StageProbe,
    SuitePackageDef,
    build_pipeline_truth_report,
    format_pipeline_truth,
    probe_wired,
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
        '[feature.bmad-ui.tasks.bmad-dashboard-install]\ncmd = "bmad-dashboard-install"\n',
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
    missing = probe_wired(tmp_path, eq)
    assert missing.value == "missing"
    assert missing.ok is True
    exe = tmp_path / "eval-quality"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(0o755)
    runnable = probe_wired(tmp_path, eq)
    assert runnable.value == "runnable"
    assert str(exe) in runnable.detail


def test_cli_class_falls_back_to_the_local_recipes_env_bin_dir(tmp_path: Path, monkeypatch):
    # A CLI-only bmad-suite tool (bmad-eval-quality) is pixi-pinned under
    # local-recipes's own env, never a station env -- a probe run under a
    # station env's own isolated PATH must still find it there before
    # declaring it missing.
    eq = _by_name()["bmad-eval-quality"]
    monkeypatch.setenv("PATH", str(tmp_path))
    guild_bin = tmp_path / ".pixi" / "envs" / "pyforge-guild" / "bin"
    guild_bin.mkdir(parents=True)
    exe = guild_bin / "eval-quality"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(0o755)
    runnable = probe_wired(tmp_path, eq)
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
        '[feature.bmad-ui.tasks.bmad-dashboard-install]\ncmd = "x"\n[feature.bmad-ui.tasks.mybmad]\ncmd = "y"\n',
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
    import json

    from pyforge.steward.cli import EXIT_OK, main

    rc = main(["suite", "pipeline-truth", "--baseline", "--json"])
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    by_name = {p["name"]: p for p in payload["packages"]}
    for name, install_class in _SIX_CLASSES.items():
        assert by_name[name]["install_class"] == install_class
    assert by_name["bmad-module-template"]["wired"]["value"] == "n/a"


# ── Story 46.9: wired fixes -- labs, bmb, tea/cis/utility-skills, manticore ─


def test_labs_wired_when_all_four_consented_skills_present(tmp_path: Path):
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    for name in ("mcp-builder", "slides-generator", "multi-repo-git-ops", "release-please"):
        (skills / name).mkdir()
    probe = probe_wired(tmp_path, _by_name()["bmad-labs-skills"])
    assert probe.value == "wired"


def test_bmb_wired_when_all_five_skill_dirs_present(tmp_path: Path):
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    for name in (
        "bmad-bmb-setup",
        "bmad-agent-builder",
        "bmad-workflow-builder",
        "bmad-module-builder",
        "bmad-eval-runner",
    ):
        (skills / name).mkdir()
    probe = probe_wired(tmp_path, _by_name()["bmad-builder"])
    assert probe.value == "wired"


def test_bmb_unwired_when_only_three_of_five_present(tmp_path: Path):
    """The genuine behavior IMPROVEMENT: the old prefix-based census
    (`bmad-bmb-`, `bmad-agent-builder`, `bmad-module-builder`) would have
    falsely reported `wired` on this partial-provision state; the new
    five-name-ALL census correctly does not."""
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    for name in ("bmad-bmb-setup", "bmad-agent-builder", "bmad-module-builder"):
        (skills / name).mkdir()
    probe = probe_wired(tmp_path, _by_name()["bmad-builder"])
    assert probe.value == "unwired"


def test_bmb_partial_dirs_stays_unwired_even_with_the_config_key_present(tmp_path: Path):
    """Review finding (HIGH), reproduced live against this repo's own real
    `_bmad/config.yaml`: an earlier draft's `wire_skill_names_all` check
    only ran FIRST, not EXCLUSIVELY -- a miss fell through to bmb's own
    auxiliary `wire_bmad_config_keys=("bmb",)` check, which independently
    reports a hit from the `bmb:` key `merge-config.py` writes regardless
    of whether all five skill dirs actually landed. This repo's own
    `_bmad/config.yaml` genuinely carries that key today, so this is not a
    hypothetical: the fixture below reproduces the exact live shape."""
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    for name in ("bmad-bmb-setup", "bmad-agent-builder", "bmad-module-builder"):
        (skills / name).mkdir()
    (tmp_path / "_bmad").mkdir()
    (tmp_path / "_bmad" / "config.yaml").write_text("bmb:\n  provisioned_by: steward\n", encoding="utf-8")
    probe = probe_wired(tmp_path, _by_name()["bmad-builder"])
    assert probe.value == "unwired"


def test_module_code_roster_wires_tea_cis_utility_skills(tmp_path: Path):
    """`tea`/`utility-skills` via `_bmad/custom/config.toml` (AD-9); `cis`
    via the still-unmigrated legacy `_bmad/config.yaml` fallback -- exactly
    the two-location read `module_install_states` already implements."""
    config_toml = tmp_path / "_bmad" / "custom" / "config.toml"
    config_toml.parent.mkdir(parents=True)
    config_toml.write_text(
        '[modules.tea]\nprovisioned_by = "steward"\n\n[modules.utility-skills]\nprovisioned_by = "steward"\n',
        encoding="utf-8",
    )
    config_yaml = tmp_path / "_bmad" / "config.yaml"
    config_yaml.write_text("cis:\n  provisioned_by: steward\n", encoding="utf-8")

    by_name = _by_name()
    assert probe_wired(tmp_path, by_name["bmad-method-test-architecture-enterprise"]).value == "wired"
    assert probe_wired(tmp_path, by_name["bmad-creative-intelligence-suite"]).value == "wired"
    assert probe_wired(tmp_path, by_name["bmad-utility-skills"]).value == "wired"


def test_module_code_roster_absent_is_unwired_even_with_stray_skill_dirs(tmp_path: Path):
    """The new, stricter, correct-per-AD-9 behavior: a stray skill directory
    with no roster entry no longer reports `wired` (the old prefix/dir
    census would have)."""
    skills = tmp_path / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "bmad-testarch-fixture").mkdir()
    probe = probe_wired(tmp_path, _by_name()["bmad-method-test-architecture-enterprise"])
    assert probe.value != "wired"
    assert probe.value == "unwired"


def test_manticore_unwired_when_studio_root_absent(tmp_path: Path, monkeypatch):
    studio_root = tmp_path / "pyforge-studio"
    monkeypatch.setenv("PYFORGE_STUDIO_ROOT", str(studio_root))
    probe = probe_wired(tmp_path, _by_name()["bmad-manticore"])
    assert probe.value == "unwired"


def test_manticore_unwired_when_studio_root_exists_but_empty(tmp_path: Path, monkeypatch):
    studio_root = tmp_path / "pyforge-studio"
    studio_root.mkdir()
    monkeypatch.setenv("PYFORGE_STUDIO_ROOT", str(studio_root))
    probe = probe_wired(tmp_path, _by_name()["bmad-manticore"])
    assert probe.value == "unwired"


def test_manticore_wired_when_studio_has_bmad_and_mc_skill(tmp_path: Path, monkeypatch):
    studio_root = tmp_path / "pyforge-studio"
    (studio_root / "_bmad").mkdir(parents=True)
    (studio_root / ".claude" / "skills" / "mc-fixture-skill").mkdir(parents=True)
    monkeypatch.setenv("PYFORGE_STUDIO_ROOT", str(studio_root))
    probe = probe_wired(tmp_path, _by_name()["bmad-manticore"])
    assert probe.value == "wired"


def test_manticore_studio_root_env_set_but_empty_falls_back_to_default_not_cwd(tmp_path: Path, monkeypatch):
    """Review finding (medium): `os.environ.get(key, default)` only falls
    back to `default` when the key is ABSENT, not when it is
    present-but-empty (`PYFORGE_STUDIO_ROOT=""`). An earlier draft would
    have resolved `Path("").expanduser()` -- the process's cwd -- instead
    of the documented default (`~/pyforge-studio`), silently reintroducing
    the in-repo signal AD-3 retired whenever this duty happens to run from
    a directory that has its own `_bmad/`/`mc-*` content (this repo's own
    root, for instance).

    Hermetic against the real machine's actual home directory: `HOME` is
    monkeypatched to a fresh, definitely-empty `tmp_path` subdirectory, so
    the DEFAULT resolves to a known, controlled, nonexistent path -- never
    the real `~/pyforge-studio` this test suite otherwise shares with a
    live, ambient (and currently coincidentally empty, but not a test
    concern either way) machine directory. `chdir`s into a SEPARATE cwd
    that DOES have `_bmad/` + an `mc-*` skill -- the shape that would
    wrongly read `wired` if the empty-string fallback bug used cwd instead
    of the (here, controlled-empty) default.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    cwd_with_content = tmp_path / "cwd"
    (cwd_with_content / "_bmad").mkdir(parents=True)
    (cwd_with_content / ".claude" / "skills" / "mc-fixture-skill").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PYFORGE_STUDIO_ROOT", "")
    monkeypatch.chdir(cwd_with_content)
    probe = probe_wired(cwd_with_content, _by_name()["bmad-manticore"])
    assert probe.value == "unwired"
    assert str(cwd_with_content) not in (probe.detail or "")


def test_live_repo_wired_predicates_ad9_and_five_name_and_studio(monkeypatch):
    """Task 2 AC (live, this repo): labs/bmb/tea/cis/utility-skills are all
    real-wired via their respective corrected mechanisms -- all five are
    backed by git-tracked `.claude/skills/` content, so these five
    assertions hold on any clone, not just this machine.

    manticore is different in kind (review finding, Story 46.6): its
    backing state is `$PYFORGE_STUDIO_ROOT` (default `~/pyforge-studio`),
    a directory AD-3 deliberately keeps OUTSIDE git -- never portable
    across machines or clones the way the other five are. An earlier draft
    hardcoded `== "wired"` here because Story 46.6 happened to complete its
    real studio install on THIS machine, which would fail on any other
    machine (or a fresh clone) where that install never ran. The fix:
    derive the expected value the same way `probe_wired`'s own
    `INSTALL_CLASS_STUDIO_MODULE` branch does, so this assertion is correct
    on every machine -- including one where the studio was never
    installed -- rather than asserting a fact that is true only here,
    only today."""
    monkeypatch.delenv("PYFORGE_STUDIO_ROOT", raising=False)
    repo = _repo_root()
    roster = _by_name()
    assert probe_wired(repo, roster["bmad-labs-skills"]).value == "wired"
    assert probe_wired(repo, roster["bmad-builder"]).value == "wired"
    assert probe_wired(repo, roster["bmad-method-test-architecture-enterprise"]).value == "wired"
    assert probe_wired(repo, roster["bmad-creative-intelligence-suite"]).value == "wired"
    assert probe_wired(repo, roster["bmad-utility-skills"]).value == "wired"

    studio_root = Path("~/pyforge-studio").expanduser()
    studio_skills = studio_root / ".claude" / "skills"
    studio_has_mc_skill = (
        (studio_root / "_bmad").is_dir()
        and studio_skills.is_dir()
        and any(p.is_dir() and p.name.startswith("mc-") for p in studio_skills.iterdir())
    )
    expected_manticore = "wired" if studio_has_mc_skill else "unwired"
    assert probe_wired(repo, roster["bmad-manticore"]).value == expected_manticore


def test_live_repo_names_six_and_template_is_n_a():
    """Story 46.9: `bmad-labs-skills` is the one exception to "the six
    non-module classes never report wired" -- this repo's own live state has
    all four Story 46.5-consented skills actually provisioned under
    `.claude/skills/`, so the plugin-path class's fixed probe correctly
    reports `wired`, not the stale `documented`."""
    repo = _repo_root()
    roster = _by_name()
    for name, install_class in _SIX_CLASSES.items():
        probe = probe_wired(repo, roster[name])
        if name == "bmad-module-template":
            assert probe.value == "n/a"
        elif name == "bmad-labs-skills":
            assert probe.value == "wired"
        else:
            assert probe.value != "wired", name
        assert roster[name].install_class == install_class
