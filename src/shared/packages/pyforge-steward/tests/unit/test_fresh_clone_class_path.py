"""Story 31.3 — fresh clone class-path is proven (install-class CAP-3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.steward.cli import EXIT_OK, build_parser, main
from pyforge.steward.fresh_clone import (
    _IMPROVISED_INSTALLER,
    FRESH_CLONE_HEADING,
    native_fragments_in_section,
    prove,
)
from pyforge.steward.provision import _SKIPPED_MODULES, _SUPPORTED_MODULES
from pyforge.steward.suite import SUITE_PACKAGES, probe_wired


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pixi.toml").is_file() and (parent / "_bmad-output").is_dir():
            return parent
    raise AssertionError("could not locate repository root from test file")


def _playbook() -> Path:
    return (
        _repo_root()
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
        / "spec-pyforge-steward/install-class-playbook.md"
    )


def _matrix() -> Path:
    return (
        _repo_root()
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
        / "spec-pyforge-steward/install-matrix.md"
    )


def _section() -> str:
    text = _playbook().read_text(encoding="utf-8")
    idx = text.find(FRESH_CLONE_HEADING)
    assert idx >= 0, "playbook missing CAP-3 fresh-clone heading"
    rest = text[idx:]
    nxt = rest.find("\n## ", 1)
    return rest if nxt < 0 else rest[:nxt]


def test_provision_help_names_prove_class_path_without_inventing_natives(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["provision", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--prove-class-path" in out
    assert "--runner" in out
    assert "install-class-playbook.md" in out
    assert "npx " not in out
    assert "uv tool install" not in out
    assert "skf" not in out


def test_fresh_clone_native_commands_are_cited_from_matrix():
    matrix = _matrix().read_text(encoding="utf-8")
    section = _section()
    fragments = native_fragments_in_section(section)
    assert fragments, "CAP-3 section must cite native commands"
    for fragment in fragments:
        assert fragment in matrix, f"invented native fragment {fragment!r}"
    assert "npx bmad-method install" in section
    assert "npx bmad-module-skill-forge install" in section
    assert "npx skills add bmad-labs/skills" in section
    assert "corepack prepare pnpm@10.26.2" in section
    assert "steward provision --runner bmad-loop" in section
    # Atlas Story 30.1: Kedro-Viz publishes as a workflow artifact, not through `steward deploy dashboard`.
    assert "kedro-viz-export" in section
    assert "viz-publish-stage" in section
    assert "steward deploy dashboard" not in section
    assert "/console/" in section
    assert "Use this template" in section


def test_fresh_clone_path_rejects_improvised_npm_installer():
    section = _section()
    assert _IMPROVISED_INSTALLER.search(section) is None
    poisoned = section + "\nThen run `node -e 'new Installer().run()'`\n"
    assert _IMPROVISED_INSTALLER.search(poisoned)


def test_fresh_clone_path_does_not_drive_module_skill_forge():
    section = _section()
    assert "provision --module skf" not in section
    assert "skf" not in _SUPPORTED_MODULES


def test_deleted_guildhall_pixi_tasks_stay_gone():
    pixi = (_repo_root() / "pixi.toml").read_text(encoding="utf-8")
    for task in (
        "dashboard-gen",
        "dashboard-watch",
        "dashboard-check",
        "dashboard-drift-check",
    ):
        assert f"[feature.local-recipes.tasks.{task}]" not in pixi
    section = _section()
    assert "`dashboard-gen`" not in section
    assert "`pixi run dashboard-gen`" not in section


def test_live_checkout_proves_six_class_outcomes():
    report = prove(_repo_root())
    assert report.ok, report.summary()
    by_name = {o.name: o for o in report.outcomes}
    assert by_name["bmad-method"].actual == "present"
    assert by_name["bmad-loop"].actual == "provisionable"
    assert by_name["bmad-module-skill-forge"].actual == "present"
    # Story 46.9: this repo's own live state has all four Story 46.5-
    # consented skills provisioned, so the corrected plugin-path probe
    # reports "wired", not the stale "documented".
    assert by_name["bmad-labs-skills"].actual == "wired"
    assert by_name["bmad-dashboard"].actual == "runnable"
    assert by_name["bmad-module-template"].actual == "n/a"
    assert by_name["bmad-module-template"].actual != "wired"


def _dashboard_repo(tmp_path: Path, *, task: bool = True, upload: str | None = "kedro-viz-export") -> Path:
    """A checkout with only what the bmad-dashboard class reads: playbook, pixi.toml, the producer."""
    playbook = (
        tmp_path
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
        / "spec-pyforge-steward/install-class-playbook.md"
    )
    playbook.parent.mkdir(parents=True)
    playbook.write_text("Kedro-Viz: `viz-publish-stage`, `kedro-viz-export`; Lane 1 `/console/`.\n", encoding="utf-8")
    pixi = "[workspace]\n" + ("[feature.pyforge-atlas.tasks.viz-publish-stage]\ncmd = 'true'\n" if task else "")
    (tmp_path / "pixi.toml").write_text(pixi, encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "kedro-viz-publish.yml"
    workflow.parent.mkdir(parents=True)
    steps = [{"run": "pixi run -e pyforge-atlas viz-publish-stage"}]
    if upload is not None:
        steps.append(
            {"uses": "actions/upload-artifact@v4", "with": {"name": upload, "path": "docs/dashboard/kedro-viz/"}}
        )
    workflow.write_text(json.dumps({"jobs": {"publish": {"steps": steps}}}), encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({}, None),
        ({"task": False}, "viz-publish-stage] missing (the Kedro-Viz producer)"),
        ({"upload": None}, "uploads no kedro-viz-export artifact"),
        ({"upload": "something-else"}, "uploads no kedro-viz-export artifact"),
    ],
    ids=["wired", "no-stage-task", "no-upload", "wrong-artifact"],
)
def test_dashboard_runnable_reads_the_kedro_viz_producer_not_a_tracked_export(tmp_path: Path, kwargs, reason):
    """Atlas Story 30.1: runnable means the producer is wired; no docs/dashboard/kedro-viz/ is ever asked for."""
    from pyforge.steward.fresh_clone import _dashboard_runnable

    repo = _dashboard_repo(tmp_path, **kwargs)
    assert not (repo / "docs" / "dashboard" / "kedro-viz").exists()
    playbook = next(repo.rglob("install-class-playbook.md")).read_text(encoding="utf-8")
    outcome = _dashboard_runnable(repo, playbook, (repo / "pixi.toml").read_text(encoding="utf-8"))
    if reason is None:
        assert outcome.ok and outcome.actual == "runnable", outcome.detail
        return
    assert not outcome.ok
    assert outcome.actual == "not-runnable"
    assert reason in outcome.detail


def test_template_into_repo_never_wired():
    pkg = next(p for p in SUITE_PACKAGES if p.name == "bmad-module-template")
    probe = probe_wired(_repo_root(), pkg)
    assert probe.value == "n/a"


def test_prove_fails_when_playbook_improvises_installer(tmp_path: Path):
    playbook = (
        tmp_path
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
        / "spec-pyforge-steward/install-class-playbook.md"
    )
    playbook.parent.mkdir(parents=True)
    matrix = (
        tmp_path
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
        / "spec-pyforge-steward/install-matrix.md"
    )
    matrix.parent.mkdir(parents=True, exist_ok=True)  # same folder as the playbook since CAP-11
    matrix.write_text("npx bmad-method install\n", encoding="utf-8")
    playbook.write_text(
        "## Fresh-clone class-path (CAP-3)\n\nDrive `new Installer()` from the transcript.\n",
        encoding="utf-8",
    )
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")
    report = prove(tmp_path)
    assert not report.ok
    assert any("Installer" in f for f in report.failures)


def test_cap3_five_and_wds_untouched():
    assert set(_SUPPORTED_MODULES) == {
        "bmb",
        "tea",
        "cis",
        "utility-skills",
        "manticore",
    }
    assert "wds" in _SKIPPED_MODULES
    assert "skf" not in _SUPPORTED_MODULES


def test_cli_prove_class_path_on_live_checkout(capsys):
    rc = main(["provision", "--prove-class-path"])
    out = capsys.readouterr().out
    assert rc == EXIT_OK, out
    assert "PASS" in out
    rc_json = main(["provision", "--prove-class-path", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc_json == EXIT_OK
    assert payload["ok"] is True
    names = {row["name"] for row in payload["outcomes"]}
    assert names >= {
        "bmad-method",
        "bmad-loop",
        "bmad-module-skill-forge",
        "bmad-labs-skills",
        "bmad-dashboard",
        "bmad-module-template",
    }
