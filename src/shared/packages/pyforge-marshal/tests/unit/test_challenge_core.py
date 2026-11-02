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


# Story 113.9: marshal's catalog shape, every provider declared (marshal-policy.toml's model_cost_catalog).
FLEET_CATALOG = {
    "providers": {
        "cursor": {"models": {"composer-2.5": {}, "composer-2.5-fast": {}}},
        "anthropic": {"models": {"sonnet-5": {}, "claude-fable-5-1": {}, "opus-5": {}}},
        "openai": {"models": {"gpt-5.6-terra": {}}},
        "google": {"models": {"gemini-3.7-flash": {}}},
    }
}
ALIASES = ("sonnet", "opus", "haiku", "default")


@pytest.mark.parametrize(
    ("model", "provider"),
    [("gemini-3.7-flash", "google"), ("gpt-5.6-terra", "openai"), ("composer-2.5-fast", "cursor")],
)
def test_render_refuses_a_catalog_entry_of_another_provider(model: str, provider: str) -> None:
    """Story 113.9 AC1: the claude profile passes the id verbatim to ``claude --model``."""
    reasons = core.render_refusals(_config(model=model), session_models=[], model_cost_catalog=FLEET_CATALOG)
    assert reasons == [
        f"[challenge].model {model!r} is catalogued under {provider!r}; the challenger runs on "
        "the claude profile and takes only an 'anthropic' entry"
    ]


def test_render_refuses_an_id_absent_from_the_catalog_and_an_alias() -> None:
    for model in ("claude-unknown-9", "sonnet"):
        reasons = core.render_refusals(
            _config(model=model), session_models=[], model_cost_catalog=FLEET_CATALOG, aliases=ALIASES
        )
        assert reasons == [f"[challenge].model {model!r} is not a model_cost_catalog entry"]


def test_render_passes_an_anthropic_catalog_entry() -> None:
    for model in ("sonnet-5", "claude-fable-5-1", "opus-5"):
        config = _config(model=model)
        assert core.render_refusals(config, session_models=[], model_cost_catalog=FLEET_CATALOG, aliases=ALIASES) == []


@pytest.mark.parametrize(
    ("challenger", "station", "same"),
    [
        ("sonnet-5", "sonnet", True),  # the station runs the alias of the challenger's family
        ("sonnet", "claude-sonnet-4-5", True),  # the challenger names the alias of the station's family
        ("opus-5", "opus", True),
        ("claude-fable-5-1", "claude-fable-5-1", True),
        ("sonnet-5", "claude-sonnet-4-5", False),  # two pinned ids of one family are two models
        ("claude-fable-5-1", "sonnet", False),
        ("opus-5", "sonnet", False),
        ("sonnet-5", "default", False),  # the account default names no family
    ],
)
def test_same_model_normalises_aliases(challenger: str, station: str, same: bool) -> None:
    assert core.same_model(challenger, station, aliases=ALIASES) is same


def test_render_refuses_an_alias_of_a_station_model() -> None:
    """Story 113.9 AC3: an alias that normalises to a station model is the station model."""
    reasons = core.render_refusals(
        _config(model="opus-5"),
        session_models=["composer-2.5", "opus"],
        model_cost_catalog=FLEET_CATALOG,
        aliases=ALIASES,
    )
    assert reasons == [
        "[challenge].model 'opus-5' is the dispatching session's own model (opus); "
        "the challenger must be a different model"
    ]
    assert (
        core.render_refusals(
            _config(model="opus-5"),
            session_models=["composer-2.5", "sonnet"],
            model_cost_catalog=FLEET_CATALOG,
            aliases=ALIASES,
        )
        == []
    )


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


# --- Story 113.8 (CAP-298, CAP-300): a review that did not fully run is unevaluable; readiness on screen ---------


def _parsed(*, stage: str = "mint", reviewers: list[str] | None = None) -> core.ChallengeReport:
    data = json.loads(_report())
    data["stage"] = stage
    if reviewers is not None:
        data["reviewers"] = reviewers
    return core.parse_report(json.dumps(data))


MINT_AGENTS = [core.agent_type(p) for p in core.DEFAULT_REVIEWERS["mint"]]


def test_a_report_naming_every_dispatched_reviewer_and_the_stage_is_evaluable() -> None:
    report = _parsed(reviewers=MINT_AGENTS)
    assert core.unevaluable_reason(report, stage="mint", personas=core.DEFAULT_REVIEWERS["mint"]) is None
    # order and surrounding whitespace do not matter; an extra name does not either
    shuffled = _parsed(reviewers=[" egm:egm-comprehension ", *MINT_AGENTS[:2], "egm:egm-extra"])
    assert core.unevaluable_reason(shuffled, stage="mint", personas=core.DEFAULT_REVIEWERS["mint"]) is None


def test_a_report_that_omits_a_dispatched_reviewer_is_unevaluable() -> None:
    report = _parsed(reviewers=MINT_AGENTS[:2])
    reason = core.unevaluable_reason(report, stage="mint", personas=core.DEFAULT_REVIEWERS["mint"])
    assert reason is not None and "egm:egm-comprehension" in reason and "egm:egm-zoom-out" not in reason


@pytest.mark.parametrize("reviewers", [[], [""], ["  "]])
def test_a_report_with_no_reviewers_is_unevaluable_even_with_no_findings(reviewers: list[str]) -> None:
    data = json.loads(_report([]))
    data["reviewers"] = reviewers
    report = core.parse_report(json.dumps(data))
    assert core.unevaluable_reason(report, stage="mint", personas=core.DEFAULT_REVIEWERS["mint"]) == (
        "report lists no reviewers"
    )


def test_a_report_for_another_stage_is_unevaluable() -> None:
    report = _parsed(stage="decompose", reviewers=MINT_AGENTS)
    reason = core.unevaluable_reason(report, stage="mint", personas=core.DEFAULT_REVIEWERS["mint"])
    assert reason == "report stage 'decompose' is not the requested 'mint'"


def test_readiness_view_clean_red_and_error() -> None:
    clean = core.readiness_view({"report": "/r.json", "findings": 0, "high": 0, "error": ""})
    assert clean == {"report": "/r.json", "findings": 0, "high": 0, "error": "", "red": False}
    assert core.readiness_text(clean) == "clean, report /r.json"
    red = core.readiness_view({"report": "/r.json", "findings": 2, "high": 1, "error": ""})
    assert red["red"] is True and red["code"] == core.READINESS_RED_CODE == "MRS-DISP-067"
    assert core.readiness_text(red) == "red MRS-DISP-067: 2 finding(s), 1 high; report /r.json"
    # the launch hook's own failure payload carries only an error
    failed = core.readiness_view({"error": "readiness challenge failed:\n boom"})
    assert failed["red"] is True and failed["report"] == "" and failed["findings"] == 0
    assert core.readiness_text(failed) == "red MRS-DISP-067: readiness challenge failed: boom; report (none)"
    # idempotent, and junk counts never fabricate a red
    assert core.readiness_view(red) == red
    assert core.readiness_view({"findings": "3", "high": True})["red"] is False
