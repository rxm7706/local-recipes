"""Epic 113 (CAP-298..CAP-303): the EGM challenger's pure core."""

from __future__ import annotations

import json

import pytest

from pyforge.marshal.core import challenge as core

CATALOG = {"providers": {"anthropic": {"models": {"claude-fable-5-1": {}, "sonnet-5": {}}}}}


def _config(**overrides: object) -> core.ChallengeConfig:
    values: dict[str, object] = {"enabled": True, "stages": core.STAGES, "model": "claude-fable-5-1"}
    values.update(overrides)
    return core.ChallengeConfig(**values)  # type: ignore[arg-type]


def test_absent_or_empty_block_is_off() -> None:
    assert core.config_from_block(None) is core.OFF
    assert core.config_from_block({}) is core.OFF
    assert not core.OFF.stage_on("mint")


def test_enabled_false_turns_every_stage_off() -> None:
    config = core.config_from_block({"enabled": False, "stages": ["mint"], "model": "m"})
    assert not config.stage_on("mint")


def test_valid_block_round_trips() -> None:
    block = {
        "enabled": True,
        "stages": ["mint", "readiness"],
        "reviewers": {"readiness": ["implementation-readiness"]},
        "model": "claude-fable-5-1",
        "standards": {"mint": ["docs/x.md"]},
        "artifact_dir": "implementation-artifacts/egm",
        "plugin_version": "0.1.0",
    }
    validated = core.valid_challenge_block(block)
    assert validated is not None
    config = core.config_from_block(validated)
    assert config.stage_on("readiness") and not config.stage_on("drift")
    assert config.reviewers_for("readiness") == ("implementation-readiness",)
    assert config.reviewers_for("mint") == core.DEFAULT_REVIEWERS["mint"]


@pytest.mark.parametrize(
    "block",
    [
        {"enabled": "yes"},
        {"stages": ["mint", "nope"]},
        {"stages": "mint"},
        {"reviewers": {"nope": ["design"]}},
        {"model": ""},
        {"unknown": 1},
        "not a table",
    ],
)
def test_malformed_block_is_excluded(block: object) -> None:
    assert core.valid_challenge_block(block) is None


def test_render_refuses_the_session_model() -> None:
    reasons = core.render_refusals(_config(), session_models=["claude-fable-5-1"], model_cost_catalog=CATALOG)
    assert any("own model" in r for r in reasons)


def test_render_refuses_a_model_outside_the_catalog() -> None:
    reasons = core.render_refusals(_config(model="gpt-x"), session_models=[], model_cost_catalog=CATALOG)
    assert any("model_cost_catalog" in r for r in reasons)


def test_render_refuses_structure_and_style_personas_and_egm_standards() -> None:
    config = _config(
        reviewers={"mint": ("structural", "style")},
        standards={"mint": ("/x/egm/resources/document_standards/design.md",)},
    )
    reasons = " ".join(core.render_refusals(config, session_models=["composer-2.5-fast"], model_cost_catalog=CATALOG))
    assert "structure and style personas" in reasons
    assert "document_standards" in reasons


def test_render_passes_a_clean_block() -> None:
    assert core.render_refusals(_config(), session_models=["composer-2.5-fast"], model_cost_catalog=CATALOG) == []


def _context(**overrides: object) -> core.ChallengeContext:
    values: dict[str, object] = {
        "target": "/repo/SPEC.md",
        "glossary": "/repo/glossary.md",
        "dream": "/repo/docs/dreams/pyforge-marshal.md",
        "standards": ("/repo/CHAIN-STANDARD.md",),
    }
    values.update(overrides)
    return core.ChallengeContext(**values)  # type: ignore[arg-type]


def test_context_rule_allows_agents_md_only_as_a_target() -> None:
    assert core.context_violations(_context(target="/repo/AGENTS.md")) == []
    assert core.context_violations(_context(standards=("/repo/AGENTS.md",)))
    assert core.context_violations(_context(glossary="/repo/specs/x/.memlog.md"))
    assert core.context_violations(_context(dream="/repo/CLAUDE.md"))


def test_context_rule_refuses_urls_and_relative_paths() -> None:
    assert core.context_violations(_context(standards=("https://example.com/x.md",)))
    assert core.context_violations(_context(target="relative/SPEC.md"))


def test_prompt_names_agents_and_paths_and_no_skill_tool() -> None:
    prompt = core.render_prompt(
        stage="mint", personas=("zoom-out", "design"), context=_context(), report_path="/out/report.json"
    )
    assert "`egm:egm-zoom-out`" in prompt and "`egm:egm-design`" in prompt
    assert "/repo/glossary.md" in prompt and "/out/report.json" in prompt
    assert "Do not use the Skill tool" in prompt
    assert "AGENTS.md" not in prompt


def _report(findings: list[dict[str, object]] | None = None) -> str:
    return json.dumps(
        {
            "stage": "mint",
            "target": "/repo/SPEC.md",
            "reviewers": ["egm:egm-zoom-out"],
            "findings": findings
            if findings is not None
            else [
                {"id": "F1", "reviewer": "egm:egm-zoom-out", "severity": "high", "claim": "c1", "evidence": "e1"},
                {"id": "F2", "reviewer": "egm:egm-zoom-out", "severity": "low", "claim": "c2", "evidence": "e2"},
            ],
        }
    )


def test_parse_report_reads_findings() -> None:
    report = core.parse_report(_report())
    assert [f.id for f in report.findings] == ["F1", "F2"]


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        json.dumps({"stage": "nope", "findings": []}),
        json.dumps({"stage": "mint"}),
        _report([{"id": "F1", "severity": "urgent"}]),
        _report([{"id": "F1", "severity": "low"}, {"id": "F1", "severity": "low"}]),
    ],
)
def test_parse_report_refuses_a_malformed_report(text: str) -> None:
    with pytest.raises(core.ReportError):
        core.parse_report(text)


def test_resolve_writes_memlog_lines_for_accepted_and_reasons_for_rejected() -> None:
    report = core.parse_report(_report())
    resolution = core.resolve(
        report, accept={"F1": "fix the CAP"}, reject={"F2": "out of scope"}, report_path="/r.json"
    )
    assert len(resolution.memlog_lines) == 1 and "F1 accepted" in resolution.memlog_lines[0]
    by_id = {f.id: f for f in resolution.report.findings}
    assert by_id["F1"].resolution == "accepted"
    assert (by_id["F2"].resolution, by_id["F2"].reason) == ("rejected", "out of scope")


def test_resolve_refuses_unknown_and_double_ids() -> None:
    report = core.parse_report(_report())
    with pytest.raises(core.ReportError):
        core.resolve(report, accept={"F9": ""}, reject={}, report_path="/r.json")
    with pytest.raises(core.ReportError):
        core.resolve(report, accept={"F1": ""}, reject={"F1": ""}, report_path="/r.json")


def test_parse_id_notes() -> None:
    assert core.parse_id_notes(["F1", "F2: reason: with colon"]) == {"F1": "", "F2": "reason: with colon"}
    with pytest.raises(core.ReportError):
        core.parse_id_notes([":x"])


def test_fleet_summary_counts_and_lists_highs() -> None:
    summary = core.fleet_summary({"pyforge-atlas": [core.parse_report(_report())]})
    assert "| pyforge-atlas | mint | 2 | 1 |" in summary
    assert "pyforge-atlas / mint / F1" in summary


def test_context_rule_keeps_the_memory_index_out() -> None:
    assert core.context_violations(_context(standards=("/repo/.claude/memory/MEMORY.md",)))
    assert core.context_violations(_context(standards=("/repo/.claude/memory/feedback/x.md",)))


def test_an_empty_catalog_refuses_the_model() -> None:
    assert core.render_refusals(_config(), session_models=[], model_cost_catalog={})


def test_adapter_isolation_reads_the_frontmatter() -> None:
    good = "---\nname: egm-zoom-out\ntools: [Read, Grep, Glob]\nomitClaudeMd: true\n---\n"
    assert core.adapter_isolation_violations("zoom-out", good) == []
    assert core.adapter_isolation_violations("zoom-out", good.replace("omitClaudeMd: true", "omitClaudeMd: false"))
    assert core.adapter_isolation_violations("zoom-out", good.replace("Glob]", "Glob, Write]"))
    assert core.adapter_isolation_violations("design", good)  # wrong agent for the persona


def test_installed_version_must_be_exactly_the_pin() -> None:
    ok = {"plugins": {"egm@egm": [{"version": "0.1.0"}]}}
    assert core.installed_version_refusal(ok, "egm@egm", "0.1.0") is None
    assert core.installed_version_refusal({"plugins": {}}, "egm@egm", "0.1.0")
    two = {"plugins": {"egm@egm": [{"version": "0.1.0"}, {"version": "0.2.0"}]}}
    assert core.installed_version_refusal(two, "egm@egm", "0.1.0")
