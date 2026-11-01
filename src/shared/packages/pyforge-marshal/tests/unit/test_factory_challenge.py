"""Epic 113 (CAP-298..CAP-303): ``marshal factory challenge``, its six switches, the dispatch hook.

Every switch runs ON and OFF here (``flag_states`` + a flagd tree on ``PYFORGE_FLAGS_PATH``); the harness
session is a fake that writes the report the prompt names, so no model is ever called.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pyforge.core.flags import FlagOff
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.marshal.cli import challenge as cli
from pyforge.marshal.cli.main import main
from pyforge.marshal.core import challenge as core
from pyforge.marshal.core import policy

USAGE = 2
SLUG = "pyforge-marshal"
ALL = (
    cli.EGM_CHALLENGE_FLAG_KEY,
    cli.EGM_POLICY_BLOCK_FLAG_KEY,
    cli.EGM_DISPATCH_READINESS_FLAG_KEY,
    cli.EGM_RETRO_DRIFT_FLAG_KEY,
    cli.EGM_AUDIT_FLAG_KEY,
    cli.EGM_RESOLVE_BRIDGE_FLAG_KEY,
)
BLOCK = {"enabled": True, "stages": list(core.STAGES), "model": "claude-fable-5-1"}
CATALOG = {
    "providers": {"anthropic": {"models": {"claude-fable-5-1": {"input_per_million": 15, "output_per_million": 75}}}}
}
TIERS = {"medium": {"dev": {"harness": "cursor", "model": "composer-2.5-fast"}}}
NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)


def _flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **on: bool) -> None:
    states = {key: "off" for key in ALL}
    for name, value in on.items():
        states[f"pyforge.marshal.{name}"] = "on" if value else "off"
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, states, name="egm-flags.json")))


def _effective(block: object = BLOCK) -> policy.EffectivePolicy:
    project: dict[str, object] = {"model_cost_catalog": CATALOG, "model_tier_map": TIERS}
    if block is not None:
        project["challenge"] = block
    effective, _ = policy.compose(project_slug=SLUG, repo_defaults={}, project=project, flags={})
    return effective


def _adapter(persona: str, *, omit: bool = True, tools: str = "[Read, Grep, Glob]") -> str:
    return f"---\nname: egm-{persona}\ntools: {tools}\nmodel: inherit\nomitClaudeMd: {str(omit).lower()}\n---\nbody\n"


def _write(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    _write(root / ".claude/settings.json", json.dumps({"enabledPlugins": {"egm@egm": True}}))
    plugins = tmp_path / "plugins"
    _write(plugins / "cache/egm/egm/0.1.0/.claude-plugin/plugin.json", json.dumps({"version": "0.1.0"}))
    _write(
        plugins / "installed_plugins.json", json.dumps({"version": 2, "plugins": {"egm@egm": [{"version": "0.1.0"}]}})
    )
    for persona, filename in core.ADAPTER_FILES.items():
        _write(plugins / "cache/egm/egm/0.1.0/.claude-plugin/agents" / filename, _adapter(persona))
    monkeypatch.setenv(cli.PLUGINS_ROOT_ENV, str(plugins))
    for slug in ("pyforge-marshal", "pyforge-atlas"):
        _write(cli.glossary_path(root, slug), "# Glossary\n")
        _write(cli.spec_path(root, slug), "# Spec\n")
        _write(cli.dream_path(root, slug), "# Dream\n")
        _write(cli.epics_path(root, slug), "# Epics\n")
    _write(root / cli.CHAIN_STANDARD_RELPATH)
    _write(root / cli.STORY_SPEC_TEMPLATE_RELPATH)
    _write(root / cli.CHAIN_STANDARD_DREAM_RELPATH)
    _write(root / "AGENTS.md")
    _write(root / "src/pkg/mod.py")
    _write(
        cli.epics_path(root, SLUG),
        "## Epic 7: A thing\n\n### Story 7.1: x\n\n**Surface:** `src/pkg/mod.py`, `docs/x.md`\n"
        "**Spec:** `planning-artifacts/specs/spec-7-1-x.md`\n\n## Epic 8: Other\n**Spec:** `planning-artifacts/specs/spec-8-1.md`\n",
    )
    _write(cli.epics_path(root, SLUG).parent / "specs/spec-7-1-x.md", "# 7.1\n")
    monkeypatch.setattr(cli, "compose_effective", lambda slug: _effective())
    return root


class FakeRunner:
    def __init__(self, findings: int = 2, returncode: int = 0, write: bool = True) -> None:
        self.findings, self.returncode, self.write = findings, returncode, write
        self.prompts: list[str] = []

    def run(self, *, prompt: str, model: str | None, cwd: Path, log_path: Path) -> int:
        self.prompts.append(prompt)
        self.model = model
        report_path = Path(re.search(r"write ONE JSON file to (\S+report\.json)", prompt).group(1))
        stage = re.search(r"stage `(\w+)`", prompt).group(1)
        if self.write:
            report_path.write_text(
                json.dumps(
                    {
                        "stage": stage,
                        "target": "t",
                        "reviewers": ["egm:egm-zoom-out"],
                        "findings": [
                            {
                                "id": f"F{i}",
                                "reviewer": "egm:egm-zoom-out",
                                "severity": "high" if i == 1 else "low",
                                "claim": "c",
                                "evidence": "e",
                            }
                            for i in range(1, self.findings + 1)
                        ],
                    }
                ),
                encoding="utf-8",
            )
        return self.returncode


def _args(**values: object) -> argparse.Namespace:
    base: dict[str, object] = {
        "project": SLUG,
        "stage": None,
        "target": None,
        "epic": None,
        "audit": False,
        "force": False,
        "format": "json",
        "challenge_command": None,
    }
    base.update(values)
    return argparse.Namespace(**base)


def _journal(run_dir: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (run_dir / cli.JOURNAL_FILENAME).read_text(encoding="utf-8").splitlines()]


# --- 113.1: the verb (pyforge.marshal.egm_challenge) ------------------------------------------------


@flag_states("pyforge.marshal.egm_challenge")
def test_pyforge_marshal_egm_challenge(flag_provider, repo: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    on = flag_provider["pyforge.marshal.egm_challenge"]
    _flags(tmp_path, monkeypatch, egm_challenge=on, egm_policy_block=True)
    runner = FakeRunner()
    args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    if not on:
        with pytest.raises(FlagOff):
            cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW)
        assert runner.prompts == []
        assert not (repo / "_bmad-output/projects" / SLUG / "implementation-artifacts").exists()
        return
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["findings"] == 2 and out["error"] == ""
    run_dir = Path(out["report"]).parent
    assert run_dir.parent == repo / "_bmad-output/projects" / SLUG / "implementation-artifacts/egm"
    entries = _journal(run_dir)
    assert [e["phase"] for e in entries] == ["intent", "outcome"]
    assert entries[1]["payload"]["findings"] == 2
    report = json.loads(Path(out["report"]).read_text(encoding="utf-8"))
    assert report["project"] == SLUG and report["spec_workspace"].endswith(f"spec-{SLUG}")
    assert runner.model == "claude-fable-5-1"
    assert "egm:egm-zoom-out" in runner.prompts[0] and "AGENTS.md" not in runner.prompts[0]


def test_flag_off_verb_refuses_with_the_usage_code_through_main(tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch)
    assert main(["factory", "challenge", "--project", SLUG, "--stage", "mint", "--target", "x"]) == USAGE


def test_a_failed_session_is_unevaluable_never_a_finding(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    assert cli.run_challenge(args, runner=FakeRunner(write=False), root=repo, now=lambda: NOW) == 1
    assert cli.run_challenge(args, runner=FakeRunner(returncode=3), root=repo, now=lambda: NOW) == 1


def test_plugin_absent_or_unpinned_refuses_before_any_spawn(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    runner = FakeRunner()
    args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    monkeypatch.setenv(cli.PLUGINS_ROOT_ENV, str(tmp_path / "empty"))
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == USAGE
    _write(repo / ".claude/settings.json", json.dumps({"enabledPlugins": {}}))
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == USAGE
    assert runner.prompts == []


def test_a_refusal_is_journaled(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    monkeypatch.setenv(cli.PLUGINS_ROOT_ENV, str(tmp_path / "empty"))
    assert cli.run_challenge(_args(stage="mint", target="x"), runner=FakeRunner(), root=repo, now=lambda: NOW) == USAGE
    (run_dir,) = _egm_runs(repo)
    (entry,) = _journal(run_dir)
    assert entry["kind"] == cli.KIND_CHALLENGE_REFUSED and "installed plugins" in entry["payload"]["reason"]


@pytest.mark.parametrize(
    ("persona", "text", "needle"),
    [
        ("zoom-out", _adapter("zoom-out", omit=False), "omitClaudeMd"),
        ("design", _adapter("design", tools="[Read, Grep, Glob, Bash]"), "read-only"),
    ],
)
def test_an_adapter_that_loses_its_isolation_is_refused(
    persona: str, text: str, needle: str, repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    _write(tmp_path / "plugins/cache/egm/egm/0.1.0/.claude-plugin/agents" / core.ADAPTER_FILES[persona], text)
    runner = FakeRunner()
    assert cli.run_challenge(_args(stage="mint", target="x"), runner=runner, root=repo, now=lambda: NOW) == USAGE
    assert needle in capsys.readouterr().err and runner.prompts == []


def test_an_installed_version_other_than_the_pin_is_refused(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    _write(tmp_path / "plugins/installed_plugins.json", json.dumps({"plugins": {"egm@egm": [{"version": "0.2.0"}]}}))
    assert cli.run_challenge(_args(stage="mint", target="x"), runner=FakeRunner(), root=repo, now=lambda: NOW) == USAGE


def test_a_station_without_a_glossary_still_runs(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    cli.glossary_path(repo, SLUG).unlink()
    runner = FakeRunner()
    args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == 0
    assert "glossary:" not in runner.prompts[0]


def test_a_session_that_changes_the_tree_is_untrusted(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    states = iter(["", " M SPEC.md\n"])
    monkeypatch.setattr(cli, "tree_snapshot", lambda root: next(states))
    args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    assert cli.run_challenge(args, runner=FakeRunner(), root=repo, now=lambda: NOW) == 1
    (run_dir,) = _egm_runs(repo)
    assert _journal(run_dir)[1]["payload"]["tree_changed"] is True


def test_the_repo_pins_and_enables_the_plugin() -> None:
    root = Path(__file__).resolve().parents[6]
    settings = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"][core.EGM_PLUGIN_ID] is True
    assert settings["extraKnownMarketplaces"]["egm"]["source"]["repo"] == core.EGM_MARKETPLACE_REPO


# --- 113.2: the policy block (pyforge.marshal.egm_policy_block) ---------------------------------------


@flag_states("pyforge.marshal.egm_policy_block")
def test_pyforge_marshal_egm_policy_block(flag_provider, tmp_path: Path, monkeypatch) -> None:
    on = flag_provider["pyforge.marshal.egm_policy_block"]
    _flags(tmp_path, monkeypatch, egm_policy_block=on)
    config = cli.challenge_config(_effective())
    assert config.enabled is on
    if not on:
        assert config is core.OFF


def test_policy_block_off_makes_the_verb_refuse(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=False)
    with pytest.raises(FlagOff):
        cli.run_challenge(_args(stage="mint", target="x"), runner=FakeRunner(), root=repo, now=lambda: NOW)


def test_absent_block_means_off(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    monkeypatch.setattr(cli, "compose_effective", lambda slug: _effective(block=None))
    assert cli.challenge_config(_effective(block=None)) is core.OFF
    assert cli.run_challenge(_args(stage="mint", target="x"), runner=FakeRunner(), root=repo, now=lambda: NOW) == USAGE


def test_same_model_as_the_station_is_refused_at_render(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    block = {**BLOCK, "model": "composer-2.5-fast"}
    monkeypatch.setattr(cli, "compose_effective", lambda slug: _effective(block=block))
    runner = FakeRunner()
    assert cli.run_challenge(_args(stage="mint", target="x"), runner=runner, root=repo, now=lambda: NOW) == USAGE
    assert runner.prompts == []


def test_compose_carries_the_block_and_drops_a_malformed_one() -> None:
    assert dict(_effective().challenge.value)["enabled"] is True
    effective, findings = policy.compose(
        project_slug=SLUG, repo_defaults={}, project={"challenge": {"enabled": "yes"}}, flags={}
    )
    assert effective.challenge.value == {} and any(f.code == "MRS-POLICY-002" for f in findings)


# --- 113.3: the dispatch hook (pyforge.marshal.egm_dispatch_readiness) ---------------------------------


def _hook(repo: Path, runner: FakeRunner, effective: policy.EffectivePolicy | None = None) -> tuple[object, list]:
    from pyforge.marshal.cli.dispatch import _readiness_challenge_before_launch

    findings: list = []
    payload = _readiness_challenge_before_launch(
        repo_root=repo,
        slug=SLUG,
        spec_path=cli.epics_path(repo, SLUG).parent / "specs/spec-7-1-x.md",
        effective_policy=effective or _effective(),
        findings=findings,
        runner=runner,
    )
    return payload, findings


def _egm_runs(repo: Path) -> list[Path]:
    base = repo / "_bmad-output/projects" / SLUG / "implementation-artifacts/egm"
    return sorted(p for p in base.glob("pyforge-marshal-*") if p.is_dir()) if base.is_dir() else []


@flag_states("pyforge.marshal.egm_dispatch_readiness")
def test_pyforge_marshal_egm_dispatch_readiness(flag_provider, repo: Path, tmp_path: Path, monkeypatch) -> None:
    on = flag_provider["pyforge.marshal.egm_dispatch_readiness"]
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_dispatch_readiness=on)
    spec = cli.epics_path(repo, SLUG).parent / "specs/spec-7-1-x.md"
    before = spec.read_text(encoding="utf-8")
    runner = FakeRunner(findings=1)
    payload, findings = _hook(repo, runner)
    if not on:
        assert payload is None and findings == [] and runner.prompts == [] and _egm_runs(repo) == []
        return
    assert [f.code for f in findings] == ["MRS-DISP-067"]
    assert payload["findings"] == 1 and payload["report"].endswith("report.json")
    (run_dir,) = _egm_runs(repo)
    assert [e["phase"] for e in _journal(run_dir)] == ["intent", "outcome"]
    assert "implementation-readiness" in runner.prompts[0] and "zoom-out" not in runner.prompts[0]
    assert spec.read_text(encoding="utf-8") == before  # report only: no status move


def test_dispatch_hook_writes_nothing_without_a_readiness_stage(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_dispatch_readiness=True)
    runner = FakeRunner()
    payload, findings = _hook(repo, runner, _effective(block={**BLOCK, "stages": ["mint"]}))
    assert payload is None and findings == [] and runner.prompts == [] and _egm_runs(repo) == []
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=False, egm_dispatch_readiness=True)
    assert _hook(repo, runner) == (None, [])


def test_dispatch_hook_is_silent_on_a_clean_review_and_survives_a_refusal(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_dispatch_readiness=True)
    payload, findings = _hook(repo, FakeRunner(findings=0))
    assert findings == [] and payload["findings"] == 0
    monkeypatch.setenv(cli.PLUGINS_ROOT_ENV, str(tmp_path / "none"))
    payload, findings = _hook(repo, FakeRunner())
    assert [f.code for f in findings] == ["MRS-DISP-067"] and "refused" in payload["error"]


def test_dispatch_hook_never_raises(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_dispatch_readiness=True)

    def boom(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "readiness_for_dispatch", boom)
    payload, findings = _hook(repo, FakeRunner())
    assert "boom" in payload["error"] and [f.code for f in findings] == ["MRS-DISP-067"]


# --- 113.4: drift (pyforge.marshal.egm_retro_drift) -------------------------------------------------------


def test_epic_drift_paths_reads_one_epic() -> None:
    text = "## Epic 7: x\n**Surface:** `src/a.py`, `src/b.py`\n**Spec:** `planning-artifacts/specs/s.md`\n## Epic 8: y\n**Spec:** `z`\n"
    assert cli.epic_drift_paths(text, "7") == (["planning-artifacts/specs/s.md"], ["src/a.py", "src/b.py"])


@flag_states("pyforge.marshal.egm_retro_drift")
def test_pyforge_marshal_egm_retro_drift(flag_provider, repo: Path, tmp_path: Path, monkeypatch) -> None:
    on = flag_provider["pyforge.marshal.egm_retro_drift"]
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_retro_drift=on)
    runner = FakeRunner()
    args = _args(stage="drift", epic="7")
    if not on:
        with pytest.raises(FlagOff):
            cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW)
        return
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == 0
    target = repo / "_bmad-output/projects" / SLUG / "implementation-artifacts/egm/drift/drift-epic-7.md"
    assert "spec-7-1-x.md" in target.read_text(encoding="utf-8") and "src/pkg/mod.py" in target.read_text(
        encoding="utf-8"
    )
    assert "egm:egm-codebase-details" in runner.prompts[0] and str(cli.spec_path(repo, SLUG)) in runner.prompts[0]


def test_the_retrospective_override_names_the_drift_verb() -> None:
    root = Path(__file__).resolve().parents[6]
    text = (root / "_bmad/custom/bmad-retrospective.toml").read_text(encoding="utf-8")
    assert "marshal factory challenge --project pyforge-marshal --stage drift --epic" in text
    assert "pyforge.marshal.egm_retro_drift" in text


# --- 113.5: audit (pyforge.marshal.egm_audit) -----------------------------------------------------------


@flag_states("pyforge.marshal.egm_audit")
def test_pyforge_marshal_egm_audit(flag_provider, repo: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    on = flag_provider["pyforge.marshal.egm_audit"]
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_audit=on)
    monkeypatch.setattr(cli, "STATIONS", ("marshal", "atlas"))
    runner = FakeRunner(findings=1)
    args = _args(audit=True)
    if not on:
        with pytest.raises(FlagOff):
            cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW)
        return
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == 0
    out = json.loads(capsys.readouterr().out)
    audit_dir = Path(out["audit_dir"])
    assert audit_dir.name == "audit-2026-11-01" and out["stations"] == 2
    # 2 repo rules + (mint + decompose) x 2 stations; the stations have no SKILL.md in the fixture
    assert len(runner.prompts) == 6 and out["findings"] == 6
    assert "pyforge-atlas" in (audit_dir / "fleet.md").read_text(encoding="utf-8")
    assert (audit_dir / "pyforge-atlas.md").is_file() and (audit_dir / "pyforge-marshal.md").is_file()
    # resumable: a second sweep re-runs nothing
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == 0
    assert len(runner.prompts) == 6
    skips = [json.loads(line) for line in (audit_dir / cli.JOURNAL_FILENAME).read_text(encoding="utf-8").splitlines()]
    assert len(skips) == 6 and {e["kind"] for e in skips} == {cli.KIND_AUDIT_SKIP}
    # a corrupt marker is re-run, never a crash
    next(audit_dir.glob("pyforge-atlas.mint.*.json")).write_text("{broken", encoding="utf-8")
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == 0
    assert len(runner.prompts) == 7
    assert not list((repo / "_bmad-output").rglob("research/*"))  # nothing under planning-artifacts


# --- 113.6: resolve (pyforge.marshal.egm_resolve_bridge) --------------------------------------------------


@flag_states("pyforge.marshal.egm_resolve_bridge")
def test_pyforge_marshal_egm_resolve_bridge(flag_provider, repo: Path, tmp_path: Path, monkeypatch) -> None:
    on = flag_provider["pyforge.marshal.egm_resolve_bridge"]
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_resolve_bridge=on)
    report = core.ChallengeReport(
        stage="mint",
        target="t",
        reviewers=(),
        project=SLUG,
        spec_workspace=str(cli.spec_path(repo, SLUG).parent),
        findings=(
            core.ReportFinding(id="F1", reviewer="r", severity="high", claim="c1", evidence="e1"),
            core.ReportFinding(id="F2", reviewer="r", severity="low", claim="c2", evidence="e2"),
        ),
    )
    path = _write(tmp_path / "report.json", report.to_json())
    calls: list[tuple[str, str]] = []
    args = _args(challenge_command="resolve", report=str(path), accept=["F1:yes"], reject=["F2:no"])
    memlog = lambda root, ws, text: calls.append((ws, text))  # noqa: E731
    spec_before = cli.spec_path(repo, SLUG).read_text(encoding="utf-8")
    if not on:
        with pytest.raises(FlagOff):
            cli.run_challenge(args, root=repo, memlog=memlog)
        assert calls == []
        return
    assert cli.run_challenge(args, root=repo, memlog=memlog) == 0
    assert len(calls) == 1 and "F1 accepted" in calls[0][1] and calls[0][0].endswith(f"spec-{SLUG}")
    written = json.loads(path.read_text(encoding="utf-8"))
    assert {f["id"]: f.get("resolution") for f in written["findings"]} == {"F1": "accepted", "F2": "rejected"}
    assert cli.spec_path(repo, SLUG).read_text(encoding="utf-8") == spec_before


def test_resolve_refuses_an_already_resolved_id(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_resolve_bridge=True)
    report = core.ChallengeReport(
        stage="mint",
        target="t",
        reviewers=(),
        spec_workspace="/ws",
        findings=(
            core.ReportFinding(id="F1", reviewer="r", severity="low", claim="c", evidence="e", resolution="accepted"),
        ),
    )
    path = _write(tmp_path / "report.json", report.to_json())
    calls: list = []
    args = _args(challenge_command="resolve", report=str(path), accept=["F1"], reject=[])
    assert cli.run_challenge(args, root=repo, memlog=lambda *a: calls.append(a)) == USAGE and calls == []


def test_resolve_refuses_an_unknown_id(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_resolve_bridge=True)
    report = core.ChallengeReport(stage="mint", target="t", reviewers=(), findings=())
    path = _write(tmp_path / "report.json", report.to_json())
    args = _args(challenge_command="resolve", report=str(path), accept=["F9"], reject=[])
    assert cli.run_challenge(args, root=repo, memlog=lambda *a: None) == USAGE
