# Vocabulary map — whitepaper term → nearest PyForge surface → the gap

Spec-authored companion of `spec-intelligence-hub` (CAP-1's working table; CAP-2..5 each close
one or more gap cells). Lifted from `docs/dreams/intelligence-hub.md` § *Where this meets
PyForge* on 2026-09-05; each gap is a candidate, not a commitment, until the Spec chooses.

| Whitepaper | Nearest thing here today | Gap the paper would name |
|---|---|---|
| Intelligence Hub | The Foundry estate — `src/platform/`, the eight stations, the Unifying Strategy; air-gap by design (`enterprise-airgap`), OCP profile (`local-ocp-hybrid-environment`) | Nothing installable *into* the Hub as a Frame / Cog / Op / Guard object; the Hub is code, not a runtime for artifacts |
| Nebi | pixi + conda-forge + this recipe factory + the SelfExplainML channel + the `bmad-suite` metapackage — the lineage the paper cites (pixi on conda) | No package format for Frames / Cogs / Ops / Guards (Nebi ships no Frame support; its `nebi-integration` note is exploratory). `nebari` 2025.10.1 and `nebi` 0.15 are consumable from conda-forge today; `nebari-infrastructure-core` is not (RB-2, 2026-09-06) |
| Frames | `CLAUDE.md`, the verified `AGENTS.md` block, `docs/dreams/`, Specs and memlogs, `.claude/memory/` team memory (Scribe), each skill's `SKILL.md`, `docs/governance/` | Inheritance (repo → station → story) is real but informal and not yet expressed in the now-published Frame Spec v0.2.0 (single-file Markdown + frontmatter `inherits`; registries, identity and provenance out of scope — RB-1, 2026-09-06); no field-level sharing; no feedback channel to an accountable owner beyond git review |
| Cogs | Station skills and personas (`bmad-agent-*`), `conda-forge-expert`; the harness = Claude Code / bmad-loop; the bmad-suite conda packages are the closest "installable unit with declared tools" | Not versioned as a worker with declared permissions and governance parameters; harness choice is not hidden behind a Cog boundary |
| Ops | bmad-loop runs, `marshal factory spin`, the CFE lifecycle loop, pixi tasks, the legacy workflow specs (`feedstock-platform-expansion`, `feedstock-failure-remediation`) | No Op manifest; no *declared* validation strategy per run — the checks exist but are implicit in policy TOML and detectors (CAP-3) |
| Guards | ~30 `*-check` detectors, Warden (sole PR verdict), pyforge-doctor sources (advisory), `bmad-review` lenses, `bmad-eval-quality` (measuring the reviewer) | Present: algorithmic, consensus (parallel adversarial review), expert (operator gates), regression / drift (`bmad-drift-check`, spec-surface). Thin or absent: source-grounding of LLM output, outcome Guards (CAP-4) |
| Gates | bmad-loop `gate_mode`, `bmad-loop-resolve` escalation, the landing rules of `pr-lifecycle`, the operator-confirmation policies in `AGENTS.md` | Autonomy is a repo-wide setting, not granted per engagement — the same observation `risk-tiered-review-depth` makes |
| Tracks | `sprint-status-ledger.yaml`, `landing-evidence-grammar`, `durable-runs`, the deferred-work ledger, run `state.json`, memlogs | No single structured evidence record per run with an explicit retention policy; evidence is spread across several files with different shapes (CAP-3) |
| Organizational Memory | Scribe's GraphStore + `.claude/memory/` + per-user auto-memory + `_bmad-output/` | The paper's simplest tier (a versioned directory); no semantic retrieval over runs, no "ability to forget" policy |
| Desktop / Web Application | The `django-*` station portals, the factory console, the artifact console, Atlas's Vizro board (`secure-live-dashboards`) | No Frame composition UI, no in-workflow Gate prompts, no Track view for non-admins |
| Marketplace | conda-forge itself, plus the SelfExplainML channel (`bmad-suite-channel-product`) | Exchanges packages, not Frames / Guards with provenance attached |
| Intelligent Ops Factory | The "Dream to Code" pipeline — this repo *is* an ops factory for packaging and station software | The paper's factory produces an organisation's SOPs as installable Ops; ours produces code and recipes |

**The one honest tension (carried into CAP-1's recording document):** the paper lists Claude Code
among the rented black boxes, and this factory runs on it. In the paper's own terms PyForge rents
the model and the harness while owning the context, the workflows, the checks and the evidence —
exactly the split the paper says matters most, so it is stated, not assumed.
