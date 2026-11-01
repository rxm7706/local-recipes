"""Epic 113 (CAP-298..CAP-303): ``marshal factory challenge``, its six switches, the dispatch hook.

Every switch runs ON and OFF here (``flag_states`` + a flagd tree on ``PYFORGE_FLAGS_PATH``); the harness
session is a fake that writes the report the prompt names, so no model is ever called.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import shlex
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pyforge.core.flags import FlagOff
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.marshal.adapters import challenge_harness as harness
from pyforge.marshal.cli import challenge as cli
from pyforge.marshal.cli import config as config_cli
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
CLAUDE_AT_FLOOR = "2.1.271 (Claude Code)\n"  # `claude --version`'s shape; the seam is stubbed, never run


def _flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **on: bool) -> None:
    states = {key: "off" for key in ALL}
    for name, value in on.items():
        states[f"pyforge.marshal.{name}"] = "on" if value else "off"
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, states, name="egm-flags.json")))


def _effective(
    block: object = BLOCK, *, catalog: object = CATALOG, tiers: object = TIERS, slug: str = SLUG
) -> policy.EffectivePolicy:
    project: dict[str, object] = {"model_tier_map": tiers}
    if catalog is not None:
        project["model_cost_catalog"] = catalog
    if block is not None:
        project["challenge"] = block
    effective, _ = policy.compose(project_slug=slug, repo_defaults={}, project=project, flags={})
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
    monkeypatch.setattr(harness, "claude_version", lambda: CLAUDE_AT_FLOOR)  # Story 113.11: never shell to claude
    for slug in ("pyforge-marshal", "pyforge-atlas"):
        _write(cli.glossary_path(root, slug), "# Glossary\n")
        _write(cli.spec_path(root, slug), "# Spec\n")
        _write(cli.dream_path(root, slug), "# Dream\n")
        _write(cli.epics_path(root, slug), "# Epics\n")
    _write(root / cli.CHAIN_STANDARD_RELPATH)
    _write(root / cli.STORY_SPEC_TEMPLATE_RELPATH)
    _write(root / cli.SPEC_TEMPLATE_RELPATH)
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
    """Writes the report the prompt names. By default it lists every agent the prompt dispatched and the
    requested stage (a complete review); ``reviewers``/``stage`` override them, ``fail_on`` fails the
    session (exit 1, no report) whenever the prompt contains that text."""

    def __init__(
        self,
        findings: int = 2,
        returncode: int = 0,
        write: bool = True,
        *,
        reviewers: list[str] | None = None,
        stage: str | None = None,
        fail_on: str | None = None,
    ) -> None:
        self.findings, self.returncode, self.write = findings, returncode, write
        self.reviewers, self.stage, self.fail_on = reviewers, stage, fail_on
        self.prompts: list[str] = []

    def run(self, *, prompt: str, model: str | None, root: Path, target: Path | None, log_path: Path) -> int:
        self.prompts.append(prompt)
        self.model = model
        if self.fail_on is not None and self.fail_on in prompt:
            return 1
        report_path = Path(re.search(r"write ONE JSON file to (\S+report\.json)", prompt).group(1))
        stage = self.stage or re.search(r"stage `(\w+)`", prompt).group(1)
        spawned = re.findall(r"`(egm:egm-[\w-]+)`", prompt.split("Do not use the Skill tool")[0])
        if self.write:
            report_path.write_text(
                json.dumps(
                    {
                        "stage": stage,
                        "target": "t",
                        "reviewers": spawned if self.reviewers is None else self.reviewers,
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


# Story 113.8 (CAP-298, EGM audit MAR-M-D1): a report that did not fully run never reads as clean.
@pytest.mark.parametrize(
    ("runner", "needle"),
    [
        (FakeRunner(findings=0, reviewers=["egm:egm-zoom-out", "egm:egm-design"]), "egm:egm-comprehension"),
        (FakeRunner(findings=0, reviewers=[]), "no reviewers"),
        (FakeRunner(findings=1, stage="decompose"), "not the requested 'mint'"),
    ],
    ids=["omits-a-reviewer", "no-reviewers", "another-stage"],
)
def test_an_incomplete_report_is_unevaluable(
    runner: FakeRunner, needle: str, repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == 1
    out = json.loads(capsys.readouterr().out)
    assert "unevaluable" in out["error"] and needle in out["error"] and out["findings"] == 0
    (run_dir,) = _egm_runs(repo)
    outcome = _journal(run_dir)[1]["payload"]
    assert outcome["status"] == "error" and needle in outcome["error"] and outcome["findings"] == 0


@pytest.mark.parametrize("findings", [0, 2])
def test_a_complete_report_exits_0_whatever_its_findings(
    findings: int, repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC2: findings never change the exit code."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    assert cli.run_challenge(args, runner=FakeRunner(findings=findings), root=repo, now=lambda: NOW) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == "" and out["findings"] == findings
    report = json.loads(Path(out["report"]).read_text(encoding="utf-8"))
    assert report["reviewers"] == [core.agent_type(p) for p in core.DEFAULT_REVIEWERS["mint"]]


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


# Story 113.11 (CAP-298, EGM audit MAR-M-Z6): the reviewers' omitClaudeMd needs Claude Code >= 2.1.271.
@pytest.mark.parametrize(
    ("output", "expected", "needle"),
    [
        ("2.1.270 (Claude Code)\n", USAGE, "Claude Code 2.1.270 is below 2.1.271"),
        ("claude: command output changed\n", USAGE, "cannot read Claude Code's version"),
        (None, USAGE, "cannot read Claude Code's version"),
        (CLAUDE_AT_FLOOR, 0, ""),
        ("10.0.1 (Claude Code)\n", 0, ""),
    ],
    ids=["below-the-floor", "unreadable", "did-not-run", "at-the-floor", "above-the-floor"],
)
def test_claude_code_below_the_floor_or_unreadable_refuses_before_any_spawn(
    output: str | None, expected: int, needle: str, repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    """Story 113.11 AC1: ``claude --version`` is read through the stubbed seam; below the floor, or unreadable,
    the verb refuses with the usage code before any spawn and journals the refusal; at or above it, it runs."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    monkeypatch.setattr(harness, "claude_version", lambda: output)
    runner = FakeRunner()
    args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == expected
    if expected == USAGE:
        assert runner.prompts == [] and needle in capsys.readouterr().err
        (run_dir,) = _egm_runs(repo)
        (entry,) = _journal(run_dir)
        assert entry["kind"] == cli.KIND_CHALLENGE_REFUSED and needle in entry["payload"]["reason"]
    else:
        assert len(runner.prompts) == 1


def test_dispatch_hook_below_the_claude_code_floor_warns_and_spawns_nothing(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    """Story 113.11 (CAP-300): the floor refuses the readiness hook like an absent plugin -- an MRS-DISP-067 WARN,
    no spawn, and the dispatch proceeds."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_dispatch_readiness=True)
    monkeypatch.setattr(harness, "claude_version", lambda: "2.1.270 (Claude Code)\n")
    runner = FakeRunner()
    payload, findings = _hook(repo, runner)
    assert runner.prompts == [] and [f.code for f in findings] == ["MRS-DISP-067"]
    assert "refused" in payload["error"] and "below 2.1.271" in payload["error"]


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


def test_a_repo_default_challenge_block_composes_at_its_own_layer() -> None:
    """Story 113.11 AC3 (EGM audit MAR-D-R6): a ``[challenge]`` block at the repo-default layer
    (``_bmad-output/policy-defaults.toml``) composes with ``REPO_DEFAULTS`` provenance. The layer is passed as a
    value, so no file is read; a project block still wins over it."""
    effective, findings = policy.compose(project_slug=SLUG, repo_defaults={"challenge": BLOCK}, project={}, flags={})
    assert effective.challenge.layer is policy.PolicyLayer.REPO_DEFAULTS
    assert not [f for f in findings if f.code == "MRS-POLICY-002"]
    config = core.config_from_block(effective.challenge.value)
    assert config.enabled and config.stages == core.STAGES and config.model == BLOCK["model"]
    effective, _ = policy.compose(
        project_slug=SLUG, repo_defaults={"challenge": BLOCK}, project={"challenge": {"enabled": False}}, flags={}
    )
    assert effective.challenge.layer is policy.PolicyLayer.PROJECT
    assert core.config_from_block(effective.challenge.value).enabled is False


# --- 113.12: each stage names its standard; decompose reads its Spec (CAP-299) ---------------------------


def test_each_stage_names_its_own_default_standard(repo: Path) -> None:
    """Story 113.12 AC1-AC3 (EGM audit MAR-E2, MAR-D-R1): decompose reads the station Spec whose capability
    range its stories claim, mint the bmad-spec five-field template; readiness, drift and rules are unchanged."""
    chain, template = repo / cli.CHAIN_STANDARD_RELPATH, repo / cli.SPEC_TEMPLATE_RELPATH
    assert template == repo / ".claude/skills/bmad-spec/assets/spec-template.md"
    assert {stage: cli.default_standards(repo, SLUG, stage) for stage in core.STAGES} == {
        "mint": (chain, template),
        "decompose": (chain, cli.spec_path(repo, SLUG)),
        "readiness": (repo / cli.STORY_SPEC_TEMPLATE_RELPATH,),
        "drift": (cli.spec_path(repo, SLUG),),
        "rules": (chain,),
    }


def test_a_decompose_run_reads_the_station_spec_and_never_the_mint_template(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    """Story 113.12 AC1/AC2: the Spec reaches a decompose reviewer as a standard; the template reaches mint only."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    runner = FakeRunner()
    decompose = _args(stage="decompose", target=str(cli.epics_path(repo, SLUG)))
    assert cli.run_challenge(decompose, runner=runner, root=repo, now=lambda: NOW) == 0
    standards = runner.prompts[0].split("standard(s):\n", 1)[1].split("\n\n", 1)[0]
    assert str(cli.spec_path(repo, SLUG)) in standards and cli.SPEC_TEMPLATE_RELPATH not in runner.prompts[0]
    mint = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
    assert cli.run_challenge(mint, runner=runner, root=repo, now=lambda: NOW) == 0
    assert str(repo / cli.SPEC_TEMPLATE_RELPATH) in runner.prompts[1].split("standard(s):\n", 1)[1]


def test_a_challenge_block_standard_overrides_the_default(repo: Path) -> None:
    """Story 113.12 Boundary: ``default_standards`` stays a fallback a ``[challenge]`` block overrides."""
    config = core.config_from_block({**BLOCK, "standards": {"decompose": ["docs/other.md"]}})
    context = cli.build_context(repo, SLUG, "decompose", cli.epics_path(repo, SLUG), config)
    assert context.standards == (str(repo / "docs/other.md"),)
    context = cli.build_context(repo, SLUG, "mint", cli.spec_path(repo, SLUG), config)
    assert context.standards == tuple(str(p) for p in cli.default_standards(repo, SLUG, "mint"))


# --- 113.9: the challenger model is a Claude entry of marshal's own catalog -----------------------------

# marshal-policy.toml's catalog shape: every provider declared (compose drops an entry without its prices).
_PRICE = {"input_per_million": 1, "output_per_million": 2}
FLEET_CATALOG = {
    "providers": {
        "cursor": {"models": {"composer-2.5": _PRICE, "composer-2.5-fast": _PRICE}},
        "anthropic": {"models": {"claude-fable-5-1": _PRICE, "sonnet-5": _PRICE, "opus-5": _PRICE, "haiku-5": _PRICE}},
        "openai": {"models": {"gpt-5.6-terra": _PRICE}},
        "google": {"models": {"gemini-3.7-flash": _PRICE}},
    }
}
FRONTIER_TIERS = {
    **TIERS,
    "frontier": {
        "dev": {"harness": "claude", "model": "claude-fable-5-1"},
        "review": {"harness": "claude", "model": "claude-fable-5-1"},
    },
}


def test_session_models_carry_the_adapter_models_and_the_launch_model() -> None:
    """Story 113.9: 'session model' is the tier map's models plus the [adapter] and [adapter.review] models."""
    effective = _effective(tiers=FRONTIER_TIERS)
    assert cli.adapter_models(effective) == ["sonnet", "opus"]
    assert cli.session_models(effective) == [
        "composer-2.5-fast",
        "claude-fable-5-1",
        "claude-fable-5-1",
        "sonnet",
        "opus",
    ]
    assert cli.session_models(effective, launch_model="composer-2.5")[-1] == "composer-2.5"
    assert cli.challenger_aliases() == ("sonnet", "opus", "haiku", "default")


@pytest.mark.parametrize(
    ("model", "reason"),
    [
        ("gemini-3.7-flash", "is catalogued under 'google'"),
        ("gpt-5.6-terra", "is catalogued under 'openai'"),
        ("composer-2.5", "is catalogued under 'cursor'"),
        ("claude-unknown-9", "is not a model_cost_catalog entry"),
    ],
)
def test_a_model_that_is_no_anthropic_catalog_entry_refuses_at_render(
    model: str, reason: str, repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    """Story 113.9 AC1: the challenger runs on the claude profile, so a Gemini, OpenAI or Cursor entry -- or an id
    absent from the catalog -- refuses with the usage code before any spawn."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    block = {**BLOCK, "model": model}
    monkeypatch.setattr(cli, "compose_effective", lambda slug: _effective(block, catalog=FLEET_CATALOG))
    assert cli.compose_effective(SLUG).model_cost_catalog.value  # the catalog composed whole
    runner = FakeRunner()
    assert cli.run_challenge(_args(stage="mint", target="x"), runner=runner, root=repo, now=lambda: NOW) == USAGE
    assert runner.prompts == []
    assert f"[challenge].model {model!r} {reason}" in capsys.readouterr().err


@pytest.mark.parametrize("model", ["claude-fable-5-1", "sonnet-5", "opus-5"])
def test_a_station_model_or_an_alias_of_one_refuses_at_render(
    model: str, repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    """Story 113.9 AC3: the frontier model, and the [adapter] (``sonnet``) and [adapter.review] (``opus``) models
    through their aliases, are each the station's own model; ``haiku-5`` (no station model) renders."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    for candidate, expected in ((model, USAGE), ("haiku-5", 0)):
        block = {**BLOCK, "model": candidate}
        monkeypatch.setattr(
            cli, "compose_effective", lambda slug, b=block: _effective(b, catalog=FLEET_CATALOG, tiers=FRONTIER_TIERS)
        )
        runner = FakeRunner()
        args = _args(stage="mint", target=str(cli.spec_path(repo, SLUG)))
        assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == expected
        if expected == USAGE:
            assert runner.prompts == [] and "own model" in capsys.readouterr().err
        else:
            assert runner.model == "haiku-5"


def test_another_station_reads_marshal_s_catalog(repo: Path, tmp_path: Path, monkeypatch) -> None:
    """Story 113.9 AC2: atlas's own policy declares no catalog; its challenger renders with an Anthropic entry of
    marshal's catalog (operator ruling 2026-11-01)."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True)
    composed: list[str] = []

    def compose(slug: str) -> policy.EffectivePolicy:
        composed.append(slug)
        return _effective(slug=slug) if slug == SLUG else _effective(catalog=None, slug=slug)

    monkeypatch.setattr(cli, "compose_effective", compose)
    atlas = "pyforge-atlas"
    assert cli.compose_effective(atlas).model_cost_catalog.value == {}
    runner = FakeRunner()
    args = _args(project=atlas, stage="mint", target=str(cli.spec_path(repo, atlas)))
    assert cli.run_challenge(args, runner=runner, root=repo, now=lambda: NOW) == 0
    assert runner.model == "claude-fable-5-1" and SLUG in composed


def test_dispatch_hook_refuses_the_run_s_launch_model(repo: Path, tmp_path: Path, monkeypatch) -> None:
    """Story 113.9 AC3: in a dispatch, the challenger is never the run's resolved launch model."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_dispatch_readiness=True)
    runner = FakeRunner(findings=0)
    payload, findings = _hook(repo, runner, launch_model="claude-fable-5-1")
    assert runner.prompts == [] and [f.code for f in findings] == ["MRS-DISP-067"]
    assert "refused" in payload["error"] and "own model" in payload["error"]
    payload, findings = _hook(repo, FakeRunner(findings=0), launch_model="composer-2.5")
    assert findings == [] and payload["error"] == ""


def _documented_example_model(text: str) -> str:
    """The ``model`` of the commented ``[challenge]`` shape in marshal-policy.toml."""
    lines = text.splitlines()
    start = lines.index("#   [challenge]")
    block = itertools.takewhile(lambda line: line.startswith("#"), lines[start + 1 :])
    (model,) = (m.group(1) for line in block if (m := re.match(r'#\s+model = "([^"]+)"', line)))
    return model


def test_the_documented_example_renders_off_marshal_and_refuses_on_marshal() -> None:
    """Story 113.9 AC4 (amended 2026-11-01): the marshal-policy.toml comment example names ``claude-fable-5-1``,
    marshal's own frontier model. Against the live policies it renders on another station (atlas) and refuses on
    marshal with a reason naming that frontier model; neither marshal-policy.toml nor the repo default declares
    ``[challenge]``."""
    path = config_cli.conventional_project_policy_path(SLUG)
    text = path.read_text(encoding="utf-8")
    assert "challenge" not in tomllib.loads(text)
    repo_defaults, _ = config_cli.read_repo_policy_defaults()
    assert "challenge" not in repo_defaults
    example = _documented_example_model(text)
    assert example == "claude-fable-5-1"
    example_config = core.config_from_block({"enabled": True, "stages": list(core.STAGES), "model": example})

    atlas = "pyforge-atlas"
    assert cli.model_refusals(example_config, slug=atlas, effective=cli.compose_effective(atlas)) == []

    marshal = cli.compose_effective(SLUG)
    frontier = dict(marshal.model_tier_map.value)["frontier"]
    assert frontier["dev"]["model"] == frontier["review"]["model"] == example
    (reason,) = cli.model_refusals(example_config, slug=SLUG, effective=marshal)
    assert reason.startswith(f"[challenge].model {example!r} is the dispatching session's own model ({example})")


# --- 113.3: the dispatch hook (pyforge.marshal.egm_dispatch_readiness) ---------------------------------


def _hook(
    repo: Path, runner: FakeRunner, effective: policy.EffectivePolicy | None = None, *, launch_model: str | None = None
) -> tuple[object, list]:
    from pyforge.marshal.cli.dispatch import _readiness_challenge_before_launch

    findings: list = []
    payload = _readiness_challenge_before_launch(
        repo_root=repo,
        slug=SLUG,
        spec_path=cli.epics_path(repo, SLUG).parent / "specs/spec-7-1-x.md",
        effective_policy=effective or _effective(),
        findings=findings,
        runner=runner,
        launch_model=launch_model,
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


def test_dispatch_hook_reports_an_incomplete_report_as_red(repo: Path, tmp_path: Path, monkeypatch) -> None:
    """Story 113.8: a readiness report that lists no reviewer is unevaluable -- MRS-DISP-067, never clean."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_dispatch_readiness=True)
    payload, findings = _hook(repo, FakeRunner(findings=0, reviewers=[]))
    assert [f.code for f in findings] == ["MRS-DISP-067"]
    assert "unevaluable" in payload["error"] and payload["report"].endswith("report.json")
    assert core.readiness_view(payload)["red"] is True


def test_the_status_view_reads_red_exactly_when_the_hook_raises_mrs_disp_067(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    """Story 113.8 (CAP-300): ``marshal status``/``marshal watch`` and the launch hook share one red rule."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_dispatch_readiness=True)
    for runner in (FakeRunner(findings=0), FakeRunner(findings=1), FakeRunner(findings=0, reviewers=[])):
        payload, findings = _hook(repo, runner)
        view = core.readiness_view(payload)
        assert view["red"] is bool(findings)
        assert view.get("code") == (findings[0].code if findings else None)


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


def test_a_partly_errored_audit_is_unevaluable(repo: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    """Story 113.8 (CAP-302): one station's session fails, the rest report -- the sweep exits 1."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_audit=True)
    monkeypatch.setattr(cli, "STATIONS", ("marshal", "atlas"))
    args = _args(audit=True)
    # atlas's epics.md is the target of its decompose run alone (its SPEC.md is also decompose's standard)
    failing = FakeRunner(findings=1, fail_on=str(cli.epics_path(repo, "pyforge-atlas")))
    assert cli.run_challenge(args, runner=failing, root=repo, now=lambda: NOW) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["stations"] == 2 and len(out["errors"]) == 1 and "pyforge-atlas decompose" in out["errors"][0]
    # the failed station alone re-runs; once it reports, the sweep exits 0
    assert cli.run_challenge(args, runner=FakeRunner(findings=1), root=repo, now=lambda: NOW) == 0
    assert json.loads(capsys.readouterr().out)["errors"] == []


def test_an_incomplete_audit_marker_is_re_run(repo: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    """Story 113.8: a marker that omits a dispatched reviewer (written before the check) never reads as done."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_audit=True)
    monkeypatch.setattr(cli, "STATIONS", ("marshal",))
    runner = FakeRunner(findings=0)
    assert cli.run_challenge(_args(audit=True), runner=runner, root=repo, now=lambda: NOW) == 0
    audit_dir = Path(json.loads(capsys.readouterr().out)["audit_dir"])
    marker = next(audit_dir.glob("pyforge-marshal.mint.*.json"))
    data = json.loads(marker.read_text(encoding="utf-8"))
    marker.write_text(json.dumps({**data, "reviewers": data["reviewers"][:1]}), encoding="utf-8")
    ran = len(runner.prompts)
    assert cli.run_challenge(_args(audit=True), runner=runner, root=repo, now=lambda: NOW) == 0
    assert len(runner.prompts) == ran + 1


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
        spec_workspace=str(cli.spec_path(repo, SLUG).parent),
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
    report = core.ChallengeReport(
        stage="mint", target="t", reviewers=(), spec_workspace=str(cli.spec_path(repo, SLUG).parent), findings=()
    )
    path = _write(tmp_path / "report.json", report.to_json())
    args = _args(challenge_command="resolve", report=str(path), accept=["F9"], reject=[])
    assert cli.run_challenge(args, root=repo, memlog=lambda *a: None) == USAGE


# --- 113.13: resolve writes only marshal's Spec and prints the memlog command for any other ---------------

SCRIBE_WS = "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe"
CHAIN_WS = "docs/governance/spec-one-chain-per-station"
ATLAS_WS = "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas"


def _finding(fid: str, claim: str = "c") -> core.ReportFinding:
    return core.ReportFinding(id=fid, reviewer="egm:egm-zoom-out", severity="high", claim=claim, evidence="e")


def _report_file(tmp_path: Path, *, stage: str = "mint", spec_workspace: str, owner_override: str = "") -> Path:
    report = core.ChallengeReport(
        stage=stage,
        target="t",
        reviewers=("egm:egm-zoom-out",),
        project=SLUG,
        spec_workspace=spec_workspace,
        owner_override=owner_override,
        findings=(
            _finding("F1", "the CAP's success line is untested"),
            _finding("F2", "it's 'quoted' $HOME"),
            _finding("F3"),
        ),
    )
    return _write(tmp_path / "report.json", report.to_json())


def test_resolve_refuses_a_report_another_project_owns_and_writes_nothing(
    repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    """Story 113.13 AC1: the report never names its own write target."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_resolve_bridge=True)
    path = _report_file(tmp_path, spec_workspace=str(cli.spec_path(repo, "pyforge-atlas").parent))
    before = path.read_bytes()
    calls: list = []
    args = _args(challenge_command="resolve", report=str(path), accept=["F1"], reject=["F2:no"])
    assert cli.run_challenge(args, root=repo, memlog=lambda *a: calls.append(a)) == USAGE
    captured = capsys.readouterr()
    assert calls == [] and path.read_bytes() == before and captured.out == ""
    assert "spec-pyforge-atlas" in captured.err and "nothing was written" in captured.err
    # no --project at all: refused the same way
    no_project = argparse.Namespace(**{k: v for k, v in vars(args).items() if k != "project"})
    assert cli.run_challenge(no_project, root=repo, memlog=lambda *a: calls.append(a)) == USAGE
    assert calls == [] and path.read_bytes() == before


def test_resolve_on_marshal_s_own_spec_runs_memlog_with_the_derived_folder(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    """Story 113.13 AC2: marshal's Spec is written through memlog.py as before; a report written in another
    checkout of the repo still names it, and the write goes to this root's folder, never the report's."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_resolve_bridge=True)
    elsewhere = f"/elsewhere/checkout/_bmad-output/projects/{SLUG}/planning-artifacts/specs/spec-{SLUG}"
    path = _report_file(tmp_path, spec_workspace=elsewhere)
    calls: list[tuple[Path, str, str]] = []
    args = _args(challenge_command="resolve", report=str(path), accept=["F1:yes"], reject=[])
    assert cli.run_challenge(args, root=repo, memlog=lambda *a: calls.append(a)) == 0
    assert [(ws, "F1 accepted" in text) for _root, ws, text in calls] == [(str(cli.spec_path(repo, SLUG).parent), True)]


@pytest.mark.parametrize(
    ("project", "stage", "workspace", "override"),
    [
        ("pyforge-atlas", "mint", ATLAS_WS, ""),
        (SLUG, "rules", SCRIBE_WS, SCRIBE_WS),
        (SLUG, "rules", CHAIN_WS, CHAIN_WS),
    ],
)
def test_resolve_prints_the_memlog_command_for_any_other_spec_and_writes_none(
    repo: Path, tmp_path: Path, monkeypatch, capsys, project: str, stage: str, workspace: str, override: str
) -> None:
    """Story 113.13 AC3 + AC5: another station's Spec, or a rules finding's governor, is never written; stdout
    carries one pasteable command per accepted finding; rejections still go back into the report."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_resolve_bridge=True)
    recorded = str(repo / override) if override else ""
    path = _report_file(tmp_path, stage=stage, spec_workspace=str(repo / workspace), owner_override=recorded)
    accept, reject = ["F1:fix it", "F2"], ["F3:out of scope"]
    expected = core.resolve(
        core.parse_report(path.read_text(encoding="utf-8")),
        accept=core.parse_id_notes(accept),
        reject={},
        report_path=str(path),
    ).memlog_lines
    calls: list = []
    args = _args(challenge_command="resolve", project=project, report=str(path), accept=accept, reject=reject)
    assert cli.run_challenge(args, root=repo, memlog=lambda *a: calls.append(a)) == 0
    assert calls == []
    commands = [line for line in capsys.readouterr().out.splitlines() if line.startswith("uv run ")]
    assert len(commands) == len(expected) == 2
    head = ["uv", "run", "_bmad/scripts/memlog.py", "append", "--workspace", workspace, "--type", "event", "--text"]
    for command, text in zip(commands, expected, strict=True):
        assert command.startswith(" ".join(head) + " ")
        assert shlex.split(command) == [*head, text]
    written = json.loads(path.read_text(encoding="utf-8"))
    assert {f["id"]: (f.get("resolution"), f.get("reason")) for f in written["findings"]} == {
        "F1": ("accepted", "fix it"),
        "F2": ("accepted", None),
        "F3": ("rejected", "out of scope"),
    }
    assert written.get("owner_override", "") == recorded


@pytest.mark.parametrize(
    "override",
    ["", ATLAS_WS],
)
def test_a_rules_report_names_only_a_governor_the_code_lists(
    repo: Path, tmp_path: Path, monkeypatch, override: str
) -> None:
    """Story 113.13: a rules report's spec_workspace that is neither --project's Spec nor a recorded override
    from RULES_OWNER_OVERRIDES is refused, whatever the report claims."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_resolve_bridge=True)
    path = _report_file(
        tmp_path, stage="rules", spec_workspace=str(repo / (override or SCRIBE_WS)), owner_override=override
    )
    calls: list = []
    args = _args(challenge_command="resolve", report=str(path), accept=["F1"], reject=[])
    assert cli.run_challenge(args, root=repo, memlog=lambda *a: calls.append(a)) == USAGE and calls == []


def test_resolve_takes_project_before_or_after_the_subverb() -> None:
    parser = argparse.ArgumentParser()
    cli.add_factory_challenge_subparser(parser.add_subparsers())
    after = parser.parse_args(["challenge", "resolve", "--project", "pyforge-atlas", "--report", "r.json"])
    before = parser.parse_args(["challenge", "--project", "pyforge-atlas", "resolve", "--report", "r.json"])
    assert after.project == before.project == "pyforge-atlas"


def test_audit_plan_gives_each_rules_file_its_governor(repo: Path, monkeypatch) -> None:
    """Story 113.13 AC4: AGENTS.md is scribe's, CHAIN-STANDARD.md the chain standard's; a station skill and
    every mint and decompose target keep their station Spec."""
    monkeypatch.setattr(cli, "STATIONS", ("marshal", "atlas"))
    _write(repo / ".claude/skills/pyforge-atlas/SKILL.md")
    owners = {(slug, stage, target): owner for slug, stage, target, _dream, owner in cli.audit_plan(repo)}
    assert owners[(SLUG, "rules", repo / "AGENTS.md")] == repo / SCRIBE_WS
    assert owners[(SLUG, "rules", repo / cli.CHAIN_STANDARD_RELPATH)] == repo / CHAIN_WS
    station = {key: owner for key, owner in owners.items() if key[2].name not in ("AGENTS.md", "CHAIN-STANDARD.md")}
    assert len(station) == 5  # atlas's skill + (mint + decompose) x 2
    assert all(owner == cli.spec_path(repo, slug).parent for (slug, _s, _t), owner in station.items())


def test_an_audit_rules_report_records_its_governor(repo: Path, tmp_path: Path, monkeypatch, capsys) -> None:
    """Story 113.13 AC4: the override is recorded on the report; a station's own report carries none."""
    _flags(tmp_path, monkeypatch, egm_challenge=True, egm_policy_block=True, egm_audit=True)
    monkeypatch.setattr(cli, "STATIONS", ("marshal",))
    assert cli.run_challenge(_args(audit=True), runner=FakeRunner(findings=1), root=repo, now=lambda: NOW) == 0
    audit_dir = Path(json.loads(capsys.readouterr().out)["audit_dir"])
    agents = json.loads(next(audit_dir.glob(f"{SLUG}.rules.AGENTS.md.json")).read_text(encoding="utf-8"))
    assert agents["spec_workspace"] == agents["owner_override"] == str(repo / SCRIBE_WS)
    chain = json.loads(next(audit_dir.glob(f"{SLUG}.rules.CHAIN-STANDARD.md.json")).read_text(encoding="utf-8"))
    assert chain["spec_workspace"] == chain["owner_override"] == str(repo / CHAIN_WS)
    mint = json.loads(next(audit_dir.glob(f"{SLUG}.mint.*.json")).read_text(encoding="utf-8"))
    assert mint["spec_workspace"] == str(cli.spec_path(repo, SLUG).parent) and "owner_override" not in mint
