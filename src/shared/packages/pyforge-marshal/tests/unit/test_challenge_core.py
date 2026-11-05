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
        "timeout_s": {"readiness": 120, "mint": 900.5},
    }
    validated = core.valid_challenge_block(block)
    assert validated is not None
    config = core.config_from_block(validated)
    assert config.stage_on("readiness") and not config.stage_on("drift")
    assert config.reviewers_for("readiness") == ("implementation-readiness",)
    assert config.reviewers_for("mint") == core.DEFAULT_REVIEWERS["mint"]
    # Story 113.14: the block's ceiling, else the per-stage default (readiness short).
    assert config.timeout_for("readiness") == 120.0 and config.timeout_for("mint") == 900.5
    assert config.timeout_for("rules") == core.STAGE_TIMEOUT_S == 3600.0
    assert core.OFF.timeout_for("readiness") == core.READINESS_TIMEOUT_S == 600.0


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
        {"timeout_s": 600},
        {"timeout_s": {"nope": 60}},
        {"timeout_s": {"mint": 0}},
        {"timeout_s": {"mint": -5}},
        {"timeout_s": {"mint": True}},
        {"timeout_s": {"mint": "60"}},
        {"timeout_s": {"mint": float("inf")}},
        {"timeout_s": {"mint": float("nan")}},
        {"timeout_s": {"mint": 10**400}},  # past float range: excluded, never an OverflowError
        {"artifact_dir": "implementation-artifacts/../planning-artifacts"},
        {"artifact_dir": "/tmp/egm"},
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


def _run(stage: str, choice: str) -> core.ChallengeReport:
    report = core.ChallengeReport(stage=stage, target="/repo/x.md", reviewers=("r",), findings=())
    return core.with_provenance(report, project="pyforge-atlas", spec_workspace="/w", dream_choice=choice)


def test_the_fleet_summary_names_each_run_s_dream_choice_and_counts_the_newest() -> None:
    """Story 113.19 AC4: a reader sees which rule chose each run's Dream entry, and how many runs took the weak one;
    a run that read no Dream entry shows none and does not count."""
    summary = core.fleet_summary(
        {
            "pyforge-atlas": [_run("rules", core.DREAM_NEWEST), _run("mint", core.DREAM_NEWEST)],
            "pyforge-doctor": [_run("mint", core.DREAM_CITED), _run("decompose", core.DREAM_NAMES_CAP)],
            "pyforge-marshal": [_run("rules", "")],
        }
    )
    assert "| Station | Stage | Findings | High | Dream choice |" in summary
    assert "| pyforge-atlas | mint | 0 | 0 | newest |" in summary
    assert "| pyforge-doctor | mint | 0 | 0 | cited |" in summary
    assert "| pyforge-doctor | decompose | 0 | 0 | names-cap |" in summary
    assert "| pyforge-marshal | rules | 0 | 0 | — |" in summary
    assert "2 of 4 runs that read a Dream entry took `newest`" in summary


def test_a_report_keeps_its_dream_choice_across_the_marker() -> None:
    """Story 113.19: the choice is the run's fact, so a resumed sweep reports the rule its kept report really ran under."""
    report = _run("mint", core.DREAM_NEWEST)
    assert core.parse_report(report.to_json()).dream_choice == core.DREAM_NEWEST
    assert "dream_choice" not in _run("mint", "").to_json()
    assert core.parse_report(_run("mint", "").to_json()).dream_choice == ""


def test_a_summary_with_no_recorded_choice_makes_no_count() -> None:
    assert "took `newest`" not in core.fleet_summary({"pyforge-atlas": [_run("rules", "")]})


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


# --- Story 113.14: the section selector --------------------------------------------------------------

SPEC = """# Spec

## Capabilities

- **CAP-1 — the first** ← Dream entry 2026-09-01
  - **intent:** one
- **CAP-2 — the second** ← Dream entry 2026-10-01 (The second dream); operator ruling
  - **intent:** two

  - **success:** two, after a blank line
- **CAP-3 — the third** ← Dream entry 2026-09-01, Dream entry 2026-10-01
  - **intent:** three

## Constraints

- **CAP-3 keeps its shape** -- a Constraint names a CAP without defining one.
"""
CAP_2 = "- **CAP-2 — the second** ← Dream entry 2026-10-01 (The second dream); operator ruling\n  - **intent:** two\n\n  - **success:** two, after a blank line\n"
CAP_3 = "- **CAP-3 — the third** ← Dream entry 2026-09-01, Dream entry 2026-10-01\n  - **intent:** three\n"

EPICS = """# Epics

## Epic 4: The second and third (CAP-2..CAP-3)

### Story 4.1: x

```
## Epic 99: inside a fence is no heading
```

## Epic 5: Another Spec's CAP (spec-one-chain-per-station:CAP-3; spec-x CAP-2, fnd:CAP-3)

## Epic 6: Own and qualified (fix under spec-pyforge-marshal CAP-1 and CAP-3)

# Appendix
"""
EPIC_4 = "## Epic 4: The second and third (CAP-2..CAP-3)\n\n### Story 4.1: x\n\n```\n## Epic 99: inside a fence is no heading\n```\n"
EPIC_6 = "## Epic 6: Own and qualified (fix under spec-pyforge-marshal CAP-1 and CAP-3)\n"

DREAM = """# Dream

## The Dream

intro

## 2026-09-01 — First

first

## 2026-10-01 — The second dream (folded from x)

## The second dream

### Body

two

## 2026-10-01 — Same day, another entry

another
"""
SECOND_ENTRY = "## 2026-10-01 — The second dream (folded from x)\n\n## The second dream\n\n### Body\n\ntwo\n"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CAP-298..CAP-303", core.Selector(kind="caps", ranges=((298, 303),))),
        ("CAP-7", core.Selector(kind="caps", ranges=((7, 7),))),
        ("epic:113", core.Selector(kind="epics", ranges=((113, 113),))),
        ("epic:112..113, 115", core.Selector(kind="epics", ranges=((112, 113), (115, 115)))),
        ("heading: 2026-11-01 — A stranger", core.Selector(kind="heading", heading="2026-11-01 — A stranger")),
    ],
)
def test_a_selector_parses(raw: str, expected: core.Selector) -> None:
    assert core.parse_selector(raw) == expected


@pytest.mark.parametrize("raw", ["CAP-3..CAP-1", "CAP-x", "epic:", "epic:3..1", "epic:a", "heading:", "Epic 113", ""])
def test_a_malformed_selector_is_refused(raw: str) -> None:
    with pytest.raises(core.SelectorError):
        core.parse_selector(raw)


def test_selector_slugs_are_filename_safe() -> None:
    assert core.parse_selector("CAP-298..CAP-303").slug == "CAP-298..CAP-303"
    assert core.parse_selector("CAP-7").slug == "CAP-7"
    assert core.parse_selector("epic:112..113,115").slug == "epic-112..113,115"
    assert core.parse_selector("heading:2026-11-01 — A: b/c").slug == "heading-2026-11-01-A-b-c"


def test_a_cap_range_selects_exactly_its_blocks() -> None:
    """AC3: each CAP block whole -- its indented lines, a blank line inside included -- and nothing else."""
    assert core.select_section(SPEC, core.parse_selector("CAP-2..CAP-3")) == CAP_2 + CAP_3
    assert core.select_section(SPEC, core.parse_selector("CAP-3")) == CAP_3
    with pytest.raises(core.SelectorError, match="CAP-9 defined nowhere"):
        core.select_section(SPEC, core.parse_selector("CAP-2..CAP-9"))


def test_an_epic_range_selects_exactly_its_sections() -> None:
    """AC3: a ``## Epic N`` section runs to the next level-1 or level-2 heading; a fenced line is no heading."""
    assert core.select_section(EPICS, core.parse_selector("epic:4")) == EPIC_4
    assert core.select_section(EPICS, core.parse_selector("epic:4,6")) == EPIC_4 + EPIC_6
    with pytest.raises(core.SelectorError, match="Epic 99"):
        core.select_section(EPICS, core.parse_selector("epic:99"))


def test_a_heading_selects_its_section_and_a_dream_entry_runs_to_the_next_entry() -> None:
    """AC3: an exact heading, else a unique prefix; a dated Dream entry keeps its folded body."""
    assert core.select_section(DREAM, core.parse_selector("heading:2026-10-01 — The second")) == SECOND_ENTRY
    assert core.select_section(DREAM, core.parse_selector("heading:The second dream")) == (
        "## The second dream\n\n### Body\n\ntwo\n"
    )
    with pytest.raises(core.SelectorError, match="2 headings match"):
        core.select_section(DREAM, core.parse_selector("heading:2026-10-01"))
    with pytest.raises(core.SelectorError, match="no heading"):
        core.select_section(DREAM, core.parse_selector("heading:2027"))


def test_the_newest_cap_slice_is_the_run_citing_the_newest_dream_entry() -> None:
    """Operator ruling 2026-11-01: the highest CAP and the contiguous run below it citing the same newest Dream
    entry; a CAP with no Dream entry is a slice of one; no CAP is no slice."""
    assert core.newest_cap_slice(SPEC) == core.CapSlice(
        first=2, last=3, dream_date="2026-10-01", dream_title="The second dream"
    )
    lone = SPEC.replace(
        "- **CAP-3 — the third** ← Dream entry 2026-09-01, Dream entry 2026-10-01", "- **CAP-3 — x** ← Constraint"
    )
    assert core.newest_cap_slice(lone) == core.CapSlice(first=3, last=3)
    assert core.newest_cap_slice("# Spec\n") is None


def test_an_epic_heading_names_only_its_own_spec_s_caps() -> None:
    own = "spec-pyforge-marshal"
    assert core.caps_named_in("Epic 4: x (CAP-2..CAP-3)", own) == {2, 3}
    assert core.caps_named_in("Epic 5: (spec-one-chain-per-station:CAP-3; spec-x CAP-2, fnd:CAP-3)", own) == set()
    epic_6 = "Epic 6: (fix under spec-pyforge-marshal CAP-1 and CAP-3; relay of spec-y:CAP-2)"
    assert core.caps_named_in(epic_6, own) == {1, 3}


@pytest.mark.parametrize(
    ("heading", "named"),
    [
        # a qualifier binds only the mention it touches: after the comma, CAP-93 is the station's own
        ("Epic 55: (spec-pyforge-core CAP-3, CAP-93)", {93}),
        ("Epic 9: (fnd:CAP-12; pyforge-core:CAP-12; spec-pyforge-x:CAP-12)", set()),
        (
            "Epic 9: (doctor:CAP-12, pyforge-doctor:CAP-13, spec-pyforge-doctor:CAP-14, spec-pyforge-doctor CAP-15)",
            {12, 13, 14, 15},
        ),
        ("Epic 9: (CAP-90–CAP-93)", {90, 91, 92, 93}),  # en dash
        ("Epic 9: (CAP-90—CAP-92)", {90, 91, 92}),  # em dash
        # a hyphen joins a range only with CAP- on the right: CAP-90-93 is the one id CAP-90
        ("Epic 9: (CAP-90-93, CAP-95..CAP-96)", {90, 95, 96}),
        ("Epic 9: (CAP-90-CAP-93)", {90, 91, 92, 93}),
        ("Epic 9: (CAP-90..93; CAP-97–98)", {90, 91, 92, 93, 97, 98}),
        ("Dream: CAP-35—2026-10-31 shipped", {35}),  # a date after an em dash is no 1,992-CAP range
        ("Dream: CAP-35-2026", {35}),
        ("Story CAP-5-1", {5}),
        ("CAP-1-30000000", {1}),
        ("CAP-1..CAP-30000000", {1, 30000000}),  # past MAX_CAP_RANGE_SPAN: only the ids written as CAP-n
        ("CAP-93..CAP-90", {90, 93}),  # reversed: no range
        ("CAP-93..90", {93}),
        ("CAP-1..500", set(range(1, 501))),  # exactly MAX_CAP_RANGE_SPAN CAPs
        ("CAP-1..501", {1}),
        ("Epic 9: (CAP-350, XCAP-35)", {350}),
        ("Epic 9: (spec-pyforge-x CAP-90–CAP-93)", set()),
    ],
)
def test_epic_headings_and_dream_text_share_one_cap_rule(heading: str, named: set[int]) -> None:
    """Story 113.14 review: ``caps_named_in`` (epic headings) and ``names_cap`` (Dream entries) read a mention the
    same way -- a whole id or a ``..``/dash range, foreign when any other qualifier touches it."""
    own = "spec-pyforge-doctor"
    assert core.caps_named_in(heading, own) == named
    for cap in range(1, 400):
        assert core.names_cap(heading, {cap}, own) is (cap in named)


def test_the_epic_range_takes_only_headings_naming_the_slice() -> None:
    own = "spec-pyforge-marshal"
    cap_slice = core.newest_cap_slice(SPEC)
    assert cap_slice is not None
    assert core.epics_naming(EPICS, cap_slice, own) == core.Selector(kind="epics", ranges=((4, 4), (6, 6)))
    assert core.epics_naming(EPICS, core.CapSlice(first=50, last=50), own) is None


def test_the_dream_entry_a_slice_cites_else_the_newest() -> None:
    assert core.dream_entry_section(DREAM, "2026-10-01", "The second dream") == (
        "2026-10-01 — The second dream (folded from x)",
        SECOND_ENTRY,
        core.DREAM_CITED,
    )
    newest = ("2026-10-01 — Same day, another entry", "## 2026-10-01 — Same day, another entry\n\nanother\n")
    assert core.dream_entry_section(DREAM) == (*newest, core.DREAM_NEWEST)
    assert core.dream_entry_section(DREAM, "2026-10-01") == (*newest, core.DREAM_CITED)
    with pytest.raises(core.SelectorError, match="2025-01-01"):
        core.dream_entry_section(DREAM, "2025-01-01")
    with pytest.raises(core.SelectorError, match="no dated"):
        core.dream_entry_section("# Dream\n\n## Not dated\n")


# Mason's Spec defines CAP-1..CAP-27 as bullets (some again as headings) and CAP-28 on as ``### CAP-n — `` headings.
MIXED_BULLETS = "".join(
    f"- **CAP-{n} — bullet {n}** ← spec-pyforge-mason CAP-{n} (shipped 2026-09-11)\n  - **intent:** b{n}\n"
    for n in range(1, 28)
)
CAP_30 = "### CAP-30 — no station caps pixi\n\n- **intent:** thirty\n- **success:** thirty ok\n"
CAP_31 = (
    "### CAP-31 — the intake toolchain\n\n- **intent:** thirty-one\n\n```\n### not a heading inside a fence\n```\n\n"
    "#### A sub-heading stays in the block\n\nmore\n"
)
MIXED_SPEC = (
    "# Spec\n\n## Capabilities\n\n"
    + MIXED_BULLETS
    + "\n### CAP-28 — the recipe CI ref\n\n- **intent:** twenty-eight\n\n"
    + "### CAP-29 — mason skills ← Dream entry 2026-09-26\n\n- **intent:** twenty-nine\n\n"
    + CAP_30
    + "\n"
    + CAP_31
    + "\n### CAP-32 — sentinel key ← Dream entry 2026-09-29\n\n- **intent:** thirty-two\n\n"
    + "### CAP-33 — the generator asks\n\n← Dream entry 2026-10-09 (The refresh campaign)\n\n- **intent:** x\n\n"
    + "### CAP-34 — host-gate tests ← Dream entry 2026-10-09\n\n- **intent:** y\n\n"
    + "### CAP-35 — the feedstock refresh campaign\n\n← operator ruling; Dream entry 2026-10-09\n\n"
    + "- **intent:** z\n- **success:** Dream entry 2026-11-30 in a success clause is no provenance\n\n"
    + "## Constraints\n\n- **CAP-35 keeps its scope**\n\n## Fold provenance\n\n"
    + "- **CAP-22 — bullet 22 again** ← spec-x CAP-2 (shipped 2026-09-17)\n"
)


def test_a_heading_form_spec_slices_its_newest_cap_run() -> None:
    """Story 113.14: a ``### CAP-n — `` heading defines a CAP as a bullet does; its provenance may sit on the lines
    before its first bullet. The newest slice is CAP-35's run, and a heading range cuts exactly its blocks."""
    numbers = [number for number, _block in core.cap_blocks(MIXED_SPEC)]
    assert numbers == [*range(1, 36), 22]
    assert core.newest_cap_slice(MIXED_SPEC) == core.CapSlice(
        first=33, last=35, dream_date="2026-10-09", dream_title="The refresh campaign"
    )
    assert core.select_section(MIXED_SPEC, core.parse_selector("CAP-30..CAP-31")) == CAP_30 + CAP_31
    cut = core.select_section(MIXED_SPEC, core.parse_selector("CAP-35"))
    assert cut.startswith("### CAP-35 — ") and cut.endswith("is no provenance\n") and "## Constraints" not in cut
    both = core.select_section(MIXED_SPEC, core.parse_selector("CAP-22"))
    assert both == (
        "- **CAP-22 — bullet 22** ← spec-pyforge-mason CAP-22 (shipped 2026-09-11)\n  - **intent:** b22\n"
        "- **CAP-22 — bullet 22 again** ← spec-x CAP-2 (shipped 2026-09-17)\n"
    )
    no_dream = MIXED_SPEC.replace("← operator ruling; Dream entry 2026-10-09", "(Operator ruling 2026-11-01.)")
    assert core.newest_cap_slice(no_dream) == core.CapSlice(first=35, last=35)
    assert core.epics_naming(
        "## Epic 25: The refresh campaign (spec-pyforge-mason CAP-35)\n", core.CapSlice(35, 35), "spec-pyforge-mason"
    ) == core.Selector(kind="epics", ranges=((25, 25),))


# Story 113.14: with no cited Dream entry, the newest dated entry that names a CAP of the slice wins over the newest.
NAMING_DREAM = """# Dream

## 2026-08-01 — Older, names it

Realizes CAP-35 (and CAP-3).

## 2026-09-29 — Names it too

The Spec's CAP-35, first cut.

## 2026-10-01 — Wrong tokens only

CAP-350, XCAP-35, spec-pyforge-x:CAP-35, `pyforge-core:CAP-35` and spec-pyforge-x CAP-35 name no mason CAP.

## 2026-10-26 — Newest, unrelated (folded from y)

## Unrelated

Nothing here.
"""


@pytest.mark.parametrize(
    ("text", "named"),
    [
        ("realizes CAP-35.", True),
        ("(CAP-34..CAP-35)", True),
        ("spec-pyforge-mason:CAP-35", True),
        ("spec-pyforge-mason CAP-35", True),
        ("pyforge-mason:CAP-35", True),
        ("mason:CAP-35", True),
        ("see: CAP-35", True),
        ("CAP-350", False),
        ("CAP-3", False),
        ("XCAP-35", False),
        ("spec-pyforge-x:CAP-35", False),
        ("`spec-pyforge-x:CAP-35`", False),
        ("spec-pyforge-x CAP-35", False),
        ("pyforge-core:CAP-35", False),
    ],
)
def test_a_dream_names_a_cap_only_as_a_whole_own_token(text: str, named: bool) -> None:
    assert core.names_cap(text, {34, 35}, "spec-pyforge-mason") is named


def test_an_uncited_slice_prefers_the_newest_entry_naming_one_of_its_caps() -> None:
    heading, section, choice = core.dream_entry_section(NAMING_DREAM, caps={35}, own_spec="spec-pyforge-mason")
    assert (heading, choice) == ("2026-09-29 — Names it too", core.DREAM_NAMES_CAP)
    assert section == "## 2026-09-29 — Names it too\n\nThe Spec's CAP-35, first cut.\n"
    # a CAP no entry names (whole token, own Spec) falls back to the newest dated entry
    heading, _section, choice = core.dream_entry_section(NAMING_DREAM, caps={36}, own_spec="spec-pyforge-mason")
    assert (heading, choice) == ("2026-10-26 — Newest, unrelated (folded from y)", core.DREAM_NEWEST)
    # an own-qualified mention in the newest entry wins; a cited date wins over any naming
    own = NAMING_DREAM.replace("Nothing here.", "Ships spec-pyforge-mason:CAP-35.")
    heading, _section, choice = core.dream_entry_section(own, caps={35}, own_spec="spec-pyforge-mason")
    assert heading.startswith("2026-10-26") and choice == core.DREAM_NAMES_CAP
    cited = core.dream_entry_section(NAMING_DREAM, "2026-10-01", caps={35}, own_spec="spec-pyforge-mason")
    assert (cited[0], cited[2]) == ("2026-10-01 — Wrong tokens only", core.DREAM_CITED)


# Story 113.19: every form a live Spec cites a Dream entry in, each read straight from a station's Spec.
@pytest.mark.parametrize(
    ("cited", "date", "title"),
    [
        ("Dream entry 2026-11-01", "2026-11-01", ""),
        ("Dream entry 2026-11-01 (A stranger reads the chain)", "2026-11-01", "A stranger reads the chain"),
        ("Dream 2026-10-13, *one registry orders the site*", "2026-10-13", "one registry orders the site"),
        ("Dream § 2026-09-29 *Every session knows the estate*", "2026-09-29", "Every session knows the estate"),
        ("the station Dream's 2026-10-26 entry *every requirement derives*", "2026-10-26", "every requirement derives"),
        (
            "Dream: `docs/dreams/x.md` § Realization log, the 2026-09-20 bullet *Claude reads `AGENTS.md` natively*",
            "2026-09-20",
            "Claude reads `AGENTS.md` natively",
        ),
        (
            "Dream: § Realization log, the bullet *2026-09-20 (evening) — The block carries no aspiration*",
            "2026-09-20",
            "The block carries no aspiration",
        ),
        (
            'minted 2026-09-19 from the Dream entry "Scribe serves every harness"',
            "2026-09-19",
            "Scribe serves every harness",
        ),
    ],
)
def test_a_slice_reads_every_citation_form_a_live_spec_uses(cited: str, date: str, title: str) -> None:
    spec = f"- **CAP-1 — one** ← {cited}\n  - **intent:** x\n"
    assert core.newest_cap_slice(spec) == core.CapSlice(first=1, last=1, dream_date=date, dream_title=title)


def test_a_cap_with_no_arrow_cites_from_what_follows_its_title() -> None:
    """doctor's CAP-93 carries no ``←``: its provenance is the parenthetical after the title, never the title."""
    spec = (
        "- **CAP-93 — Doctor holds the verdict** (minted 2026-10-26, and the station Dream's 2026-10-26 entry "
        "*every requirement derives*; realized by Story 6.1)\n  - **intent:** x\n"
    )
    assert core.newest_cap_slice(spec) == core.CapSlice(
        first=93, last=93, dream_date="2026-10-26", dream_title="every requirement derives"
    )
    titled = "- **CAP-1 — the Dream entry 2026-10-26 reader** (ready 2026-10-27)\n"
    assert core.newest_cap_slice(titled) == core.CapSlice(first=1, last=1)


def test_a_ready_date_is_no_dream_citation() -> None:
    spec = "- **CAP-61 — one generator** ← spec-pyforge-herald CAP-61 (ready 2026-10-14; works with CAP-60)\n"
    assert core.newest_cap_slice(spec) == core.CapSlice(first=61, last=61)


BULLET_DREAM = """# Dream

## Realization log

- **2026-10-26 (another bullet)** — the same day, no such title.
- **2026-09-14 (only a bullet carries this date) — Found:** one line.
- **2026-07 (through 07-18)** — a month is no date. → CAP-93
- **2026-11-05 (the audit) — Found:** read CAP-93 and Epic 50, with no arrow.
- plain bullet

```text
- **2026-12-01 (fenced) — Found:** a fence holds no bullet. → CAP-93
```

Prose at column 0 ends a bullet.

## Fold — one chain (2026-09-17)

- **2026-10-26 (every requirement derives from a capability) — Found:** the fold wrote
  arrows by counting.

  **Constraints:** a paragraph after a blank line stays in its bullet. → CAP-93 / Epic 50 / Story 50.1.

## 2026-10-26 — A folded entry on the same date

## The folded body

Nothing about CAP-7.

## 2026-11-02 — Newest heading, unrelated

Nothing here.
"""
FIRST_BULLET = """- **2026-10-26 (every requirement derives from a capability) — Found:** the fold wrote
  arrows by counting.

  **Constraints:** a paragraph after a blank line stays in its bullet. → CAP-93 / Epic 50 / Story 50.1.
"""
DOCTOR = {"own_spec": "spec-pyforge-doctor"}


def test_a_title_selects_the_entry_among_those_sharing_the_date() -> None:
    """Story 113.19 AC1: the title decides among headings and bullets of one date, and a date alone keeps today's
    rule, the last heading of that date."""
    title = "every requirement derives from a capability"
    label, section, choice = core.dream_entry_section(BULLET_DREAM, "2026-10-26", title)
    assert (section, choice) == (FIRST_BULLET, core.DREAM_CITED)
    assert label[:10] == "2026-10-26"  # write_dream_entry names the slice file by it
    wrapped = BULLET_DREAM.replace(
        "derives from a capability) — Found:** the fold", "derives from\n  a capability) — Found:**"
    )
    assert core.dream_entry_section(wrapped, "2026-10-26", title)[1].startswith("- **2026-10-26 (every requirement")
    assert core.dream_entry_section(BULLET_DREAM, "2026-10-26", "A folded entry")[0].startswith("2026-10-26 — A folded")
    for missing in ("", "no such title"):
        assert core.dream_entry_section(BULLET_DREAM, "2026-10-26", missing)[0].startswith("2026-10-26 — A folded")


def test_a_cited_date_only_a_bullet_carries_yields_that_bullet() -> None:
    """Story 113.19 AC2, in a Realization log or a fold section; a date neither a heading nor a bullet carries still
    refuses."""
    label, section, choice = core.dream_entry_section(BULLET_DREAM, "2026-09-14")
    assert (section, choice) == (
        "- **2026-09-14 (only a bullet carries this date) — Found:** one line.\n",
        core.DREAM_CITED,
    )
    assert label[:10] == "2026-09-14"
    same_day = BULLET_DREAM.replace("## 2026-10-26 — A folded", "## 2026-10-27 — A folded")
    assert core.dream_entry_section(same_day, "2026-10-26")[1] == FIRST_BULLET  # no heading: the last bullet of it
    for absent in ("2025-01-01", "2026-12-01", "2026-07-18"):
        with pytest.raises(core.SelectorError, match=absent):
            core.dream_entry_section(BULLET_DREAM, absent)


def test_an_uncited_slice_keeps_names_cap_then_newest() -> None:
    """Story 113.19 AC3: a heading naming a CAP wins, a bullet whose ``→`` names it comes next (a bullet that only
    mentions it, such as an audit's own log line, does not), and the newest stays the newest heading."""
    heading, section, choice = core.dream_entry_section(BULLET_DREAM, caps={93}, **DOCTOR)
    assert (section, choice) == (FIRST_BULLET, core.DREAM_NAMES_CAP)
    named = BULLET_DREAM.replace("Nothing about CAP-7.", "Realizes CAP-93.")
    heading, _section, choice = core.dream_entry_section(named, caps={93}, **DOCTOR)
    assert heading.startswith("2026-10-26 — A folded") and choice == core.DREAM_NAMES_CAP
    heading, _section, choice = core.dream_entry_section(BULLET_DREAM, caps={94}, **DOCTOR)
    assert heading.startswith("2026-11-02 — Newest heading") and choice == core.DREAM_NEWEST
    foreign = BULLET_DREAM.replace("→ CAP-93 / Epic 50", "→ spec-pyforge-x:CAP-93 / Epic 50")
    heading, _section, choice = core.dream_entry_section(foreign, caps={93}, **DOCTOR)
    assert heading.startswith("2026-11-02") and choice == core.DREAM_NEWEST


def test_a_dream_of_bullets_alone_still_has_a_newest() -> None:
    bullets = "# Dream\n\n## Realization log\n\n- **2026-01-02 (a) — Found:** a.\n- **2026-03-04 (b) — Found:** b.\n"
    assert core.dream_entry_section(bullets)[1:] == ("- **2026-03-04 (b) — Found:** b.\n", core.DREAM_NEWEST)


def test_a_fenced_cap_defines_nothing() -> None:
    """Story 113.14 review: neither form defines a CAP inside a fenced code block, so an example never becomes the
    newest slice."""
    spec = (
        "- **CAP-1 — real** ← Dream entry 2026-09-01\n  - **intent:** one\n\n"
        "```markdown\n- **CAP-999 — example** ← Dream entry 2026-12-01\n### CAP-998 — example heading\n```\n\n"
        "~~~\n- **CAP-997 — another example**\n~~~\n"
    )
    assert [number for number, _block in core.cap_blocks(spec)] == [1]
    assert core.newest_cap_slice(spec) == core.CapSlice(first=1, last=1, dream_date="2026-09-01")


def test_a_heading_occurrence_picks_one_of_several_matches() -> None:
    """Story 113.14 review: ``heading:<text>#N`` picks the Nth matching heading (1-based); the ambiguity error says
    so; a ``#`` after whitespace is heading text."""
    text = "# D\n\n## Realization log\n\none\n\n## Realization log\n\ntwo\n\n## Issue #3\n\nthree\n"
    assert core.parse_selector("heading:Realization log#2") == core.Selector(
        kind="heading", heading="Realization log", occurrence=2
    )
    assert core.parse_selector("heading:Realization log#2").slug == "heading-Realization-log--2"
    assert core.select_section(text, core.parse_selector("heading:Realization log#2")) == "## Realization log\n\ntwo\n"
    assert core.select_section(text, core.parse_selector("heading:Realization log#1")) == "## Realization log\n\none\n"
    with pytest.raises(core.SelectorError, match=r"heading:Realization log#N \(1-based\)"):
        core.select_section(text, core.parse_selector("heading:Realization log"))
    with pytest.raises(core.SelectorError, match="only 2 heading"):
        core.select_section(text, core.parse_selector("heading:Realization log#3"))
    with pytest.raises(core.SelectorError, match="count from 1"):
        core.parse_selector("heading:Realization log#0")
    assert core.parse_selector("heading:Issue #3") == core.Selector(kind="heading", heading="Issue #3")
    assert core.select_section(text, core.parse_selector("heading:Issue #3")) == "## Issue #3\n\nthree\n"


def test_a_context_without_a_dream_names_none() -> None:
    """Story 113.14 review: an audit rules run whose station has no slice gets no Dream line, never the whole Dream."""
    context = core.ChallengeContext(target="/r/SKILL.md", glossary="", dream="", standards=("/r/CHAIN-STANDARD.md",))
    prompt = core.render_prompt(stage="rules", personas=("zoom-out",), context=context, report_path="/r/report.json")
    assert "Dream" not in prompt and context.context_paths() == ("/r/CHAIN-STANDARD.md",)
