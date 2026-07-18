---
title: "PRFAQ: cfe-atlas-datapipeline Kedro Migration (premise kill-test)"
status: "complete"
created: "2026-07-16"
updated: "2026-07-16"
stage: 5
mode: "headless kill-test (existing spec v5.4 under attack; null alternative armed)"
inputs:
  - docs/specs/cfe-atlas-datapipeline-kedro-migration.md (v5.4)
  - _bmad-output/projects/local-recipes/planning-artifacts/research/domain-cf-atlas-domain-triad-research-2026-07-16.md
  - _bmad-output/projects/local-recipes/planning-artifacts/research/technical-agentic-sdlc-kedro-migration-execution-research-2026-07-16.md
  - _bmad-output/projects/local-recipes/planning-artifacts/research/corpus-gap-analysis-research-2026-07-16.md
  - docs/specs/cfe-shipped-releases.md (legacy engineering-contract evidence)
---

# The conda-forge factory's intelligence layer now explains itself — to humans and to the agents that run it

## For the operator and the AI agents who maintain 29,000-feedstock intelligence: every dataset has a declared lineage, every question has a queryable answer, and the pipeline that produces both can be safely modified by an unattended agent.

**Local factory, Q3 2027** — The cf_atlas intelligence layer today completed its migration from a 10,000-line hand-rolled orchestrator to a Kedro/Dagster/DuckDB pipeline with a semantic layer and an agent-facing dashboard. The system that tracks staleness, vulnerabilities, maintainership, and release readiness across the conda-forge ecosystem is no longer a procedural monolith only its author could safely change — it is a graph of small, contract-guarded nodes that BMAD agents extend, verify, and operate through the same machinery they use to write it.

Before the migration, the operator lived with three chronic taxes. Adding any new intelligence phase meant hand-wiring a registry, re-implementing checkpointing, TTLs, and backoff, and hoping nothing silently broke — one phase (per-version download history) ran for months as an unregistered side-effect, invisible to every operational flag. When a 3–4 hour rebuild misbehaved, the only observability was stdout — a hard-coded 1800-second cap silently dropped three phases on cold runs for weeks before anyone noticed. And every question the data could answer required either one of 28 fixed CLIs or hand-written SQL against an undocumented schema — agents asking anything novel got nothing.

Today the DAG is declared, so nothing can be invisible; every node carries its own budget, contract, and retry policy, so nothing fails silently; and the Boring Semantic Layer turns the 28 fixed questions into an open query surface that Vizro renders for humans and MCP exposes to agents — including a natural-language path. The whole intelligence surface also runs in a browser with no backend, from statically-hosted Parquet.

> "The point was never Kedro. The point is that the factory's intelligence layer is now made of the same stuff the agents are good at — small pure functions, declared inputs, machine-checkable contracts. That's what lets me hand the pipeline to the loop and go review recipes."
> — rxm7706, Operator

### How It Works

An agent (or the operator) asks a question — through a Vizro page, the NL field, or an MCP tool. The BSL translates it into governed queries over DuckDB-backed Parquet datasets whose lineage kedro-viz renders on demand. When upstream ecosystems move, Dagster schedules re-materialize exactly the affected nodes; when a contract is violated, the run halts and an A2A alert names the node and the violated expectation. When a new signal is worth ingesting, an agent adds a node with declared inputs/outputs and a fixture gate — the DAG re-resolves; no registry, no hand-wired cursor code.

> "I used to answer 'which of my feedstocks are behind AND vulnerable AND sole-maintained' by pasting three CLI outputs into a scratchpad. Now it's one question."
> — a CFE authoring agent, mid-remediation

### Getting Started

`pixi run viz` for the DAG; the Vizro dashboard for the questions; `run_*_pipeline` MCP tools for the agents. The legacy orchestrator was retired only after a recorded dataset-parity gate (B4) proved zero material drift.

---

## Customer FAQ

### Q: I'm the operator. The old pipeline already worked — 23 phases, ~10 releases in two months. Why did I spend 32 stories on plumbing instead of packaging recipes?

A: Honest answer: if the old pipeline's *outputs* were the only product, you shouldn't have. The migration's value is that the pipeline's *maintenance* moves from you to the agents. The legacy monolith was hostile to unattended modification — every change touched shared procedural state, and the record shows what that costs (the silent Phase I, the 1800 s drops, the zombie-row class, a $500 BigQuery invoice caught by hand). Small contract-guarded nodes are the shape the loop can safely extend. The 32 stories are the price of never hand-wiring story 33.

### Q: I'm a CFE agent. I only ever call `behind-upstream`, `whodepends`, and `query-atlas`. What do I get?

A: Day one: the same answers, faster, plus join-anything ad-hoc queries you currently can't ask at all (the § 3.2 rigid-surface pain is yours). Honest caveat: your three CLIs keep working through parity (B4 gates retirement), so your *floor* doesn't move — the migration raises your ceiling.

### Q: I'm a BMAD agent asked to add a new signal (say, EUVD ingestion). What's different?

A: Legacy: register in `PHASES`, hand-write checkpoint/TTL/backoff/commit-batching, update the orchestrator loop, and hope the meta-tests catch what you missed. Migrated: write a node function + catalog entry + fixture gate; the DAG, retries, budgets, and lineage come from the framework. That difference is the whole premise — it's the § 15 evidence-gating pattern turned into a one-story operation.

### Q: Couldn't I have had the new signals (Basilisk, release velocity, migration readiness) without any of this?

A: Yes — and the spec never claims otherwise. Priced honestly: FR-19/20/21 as legacy Phases U/V/W ≈ 3–4 stories (the fetcher pattern exists; `cisa_kev_fetcher` is the precedent), and Q7 already holds the door open for an interim Phase U. **The signals are riders, not the justification.** Anyone selling this migration on the signals is overselling it.

---

## Internal FAQ

### Q: State the null alternative fairly. Why not take it?

A: The null: keep the legacy orchestrator; add Phases U/V/W (the three signals, ~3–4 stories); fix the 1800 s cap with per-sub-step timeouts (~0.5 story); add logging. Total ≈ 5 stories, zero parity risk, zero new dependencies. It fully resolves the *acute* defects. What it cannot resolve: (1) the chronic per-phase machinery tax (every future phase re-implements checkpoint/TTL/backoff — 23 phases of accreted evidence in the shipped-releases contracts); (2) agent-hostile maintenance (procedural monolith, shared state — the graduated-autonomy execution model has nothing safe to grip); (3) the rigid read surface; (4) declared lineage (the Phase-I class of invisibility). The null is the right choice **if** the factory's intelligence ambitions are frozen at today's 23 phases and 28 questions. Every § 12.1 candidate signal and every § 13.1 Candidate feed says they aren't.

### Q: The read surface (BSL + Vizro + Vizro-AI) is the customer-facing value. Ibis has a SQLite backend — couldn't Waves D and G be built on the *legacy* database, skipping the orchestration migration entirely?

A: Technically yes, and this kill-test insists the spec acknowledge it: **the migration bundles two products** — an orchestration replacement (Waves A–C, F: where the *risk* lives — kedro-dagster bus-factor-1, the Prefect acquisition, parity) and an agent-facing intelligence surface (Waves D, G: where the *value* concentrates). BSL-over-Ibis-over-SQLite would work as a decoupling ramp if the orchestration track stalls. The bundle is still justified — building the semantic layer against the legacy schema ossifies exactly the store you're retiring, and the write-side contracts (FR-10/18) need the node model — but the severability is real and should be recorded as the fallback ramp, not discovered in a crisis.

### Q: § 4.8 claims DuckDB "drastically reduces the 3–4 hour cold start." Does it?

A: Weakest technical claim in the spec. The cold start is dominated by *network fetches* (Phase R's first pull alone is ~15 min; F/K/N are API-bound), not by SQLite compute. DuckDB genuinely accelerates query-time analytics, Phase-F parquet reads, and the derived-artifact sweeps — but AC-7's "materially faster cold start" will not come from the engine swap alone; it comes from incremental re-materialization (not re-running unaffected nodes). Re-scope the claim before F1's benchmark is asked to prove something the architecture doesn't promise.

### Q: What's the opportunity cost, and who pays it?

A: ~32 stories of loop/agent/operator time not spent on the factory's actual mission (recipes, feedstocks — the 769-feedstock refresh backlog is live). Mitigations that make this acceptable: graduated autonomy pushes most stories to unattended execution; the wave structure is severable (value lands at B4, at D2, at each boundary — this is not a two-year tunnel); and B4 is a genuine abort ramp: if parity fails economically, the legacy path is still running and the sunk cost is Waves 0–B only.

### Q: What kills this project?

A: Three scenarios, all with tripwires already in the spec: (1) Dagster-under-Prefect deteriorates and kedro-dagster (bus factor ≈1) breaks against it — tripwire: Q2's Wave-C re-verify; ramp: Dagster Components / Prefect deployer. (2) B4 parity proves economically unreachable (data drift swamps signal) — tripwire: the attended parity gate itself; ramp: keep legacy, salvage D-wave on the severability path. (3) The loop's verify gates never get built (verify-first sequencing slips) and the migration devolves into attended hand-work — tripwire: Wave-A exit criteria (the six verify tasks are story deliverables).

### Q: Is the timing right?

A: The research says the *ecosystem* timing is favorable (standards just formalized: ECMA-424/427; duckdb-wasm at parity; CRA makes the signal classes regulatory-relevant by Sep 2026) and the *execution* timing is deliberately staged (bmad-loop pilot learnings pre-paid on pyforge-warden; per-story gates until the harness proves out). The one timing risk is orchestrator-market churn (acquisition three days old) — addressed by the exit ramps, not by waiting: waiting doesn't reduce that uncertainty, it only defers the read-surface value.

---

## The Verdict

**Concept strength: CONDITIONAL PASS — the premise survives its kill-test, but only on its strongest leg, and the spec should stop leaning on the weak ones.**

**Forged in steel**
- The **agent-maintainability thesis**: the factory's stated operating model (§ 2.1, graduated autonomy, the loop) requires a pipeline made of small contract-guarded nodes. This is the one justification the null alternative structurally cannot match, and today's execution research makes it concrete rather than aspirational.
- The **severable wave structure with the B4 abort ramp**: sunk-cost exposure is bounded and value lands incrementally. This is what makes a 32-story bet on an internal tool responsible.
- The honest pricing of the signals: FR-19/20/21 are riders (~3–4 stories on either path); the spec never sells them as the justification, and Q7 documents the interim option.

**Needs more heat**
- **AC-7 / § 4.8's cold-start claim**: network-bound, not compute-bound — re-scope to "incremental re-materialization + query-time analytics" or quantify before F1's benchmark is asked to prove it.
- **Opportunity-cost accounting**: the spec should say, in one sentence, what the migration displaces (feedstock-refresh throughput) and why the § 2.5 unattended execution model makes that acceptable.

**Cracks in the foundation (address deliberately, none fatal)**
- **The two-products bundle**: orchestration risk and read-surface value are packaged as one decision. Record the severability ramp (BSL/Vizro can survive an orchestration stall) so a Wave-C crisis doesn't kill the D-wave value by association.
- **§ 3.2 overclaims urgency**: "maintainability bottleneck" is a chronic tax, not a fire — the legacy shipped 23 phases and ~10 releases in two months. The honest framing is compounding-cost avoidance plus agent-maintainability, and the spec is stronger when it says so.

**Disposition**: PROCEED to Tier-2 intake, with three spec touches carried as intake notes: (1) re-scope AC-7's performance claim; (2) add the severability/fallback ramp note; (3) reframe § 3.2's first bullet from acute to chronic. The decision to run this kill-test — and its outcome — is now on the record: the migration was chosen over the null alternative *with the alternative fairly priced*, not by momentum.

<!-- coaching-notes-stage-1 -->
<!-- Concept type: internal tool (operator + agent customers). Mode: headless kill-test on an existing v5.4 spec at user direction; null alternative armed in the prompt. Contextual gathering satisfied by the three same-day research artifacts (subagent fan-out waived — the artifacts ARE the gathered context; noted per graceful-degradation clause). Key challenge outcomes: signals-as-riders confirmed; severability of Waves D/G surfaced; AC-7 cold-start claim identified as network-bound overclaim; § 3.2 urgency downgraded to chronic tax; agent-maintainability isolated as the load-bearing justification. -->
