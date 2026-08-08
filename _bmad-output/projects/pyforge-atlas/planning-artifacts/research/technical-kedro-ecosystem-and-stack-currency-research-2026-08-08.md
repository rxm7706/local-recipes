---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-atlas.md
  - docs/dreams/kedro-org-tooling-adoption.md
  - docs/specs/cfe-atlas-datapipeline-kedro-migration.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/technical-kedro-dagster-duckdb-stack-currency-research-2026-07-25.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/pixi.toml
research_type: 'technical'
research_topic: 'Kedro-ecosystem adoption gap (kedro-skills / publish-kedro-viz / vscode-kedro / kedro-builder) + full stack currency re-check + cross-station stack-adoption question, three weeks after the pyforge-atlas migration shipped'
research_goals: 'Refresh the 2026-07-25 stack-currency report with 2026-08-08 telemetry; enumerate what the Kedro organization ships beyond what Atlas adopted and assess each unadopted tool against the kedro-org-tooling-adoption Dream; answer whether the Kedro/Dagster/DuckDB stack generalizes to other PyForge stations or is genuinely Atlas-specific.'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: true
source_verification: true
supersedes: 'technical-kedro-dagster-duckdb-stack-currency-research-2026-07-25.md (the § 1–6 currency findings; that report stays as the 9-days-post-ship baseline)'
methodology_note: 'Every external currency claim is grounded in `gh api repos/<owner>/<repo>` + `/releases/latest` calls captured 2026-08-08 — the same primary-source repository-telemetry method the 2026-07-25 report validated (stars, license, archived flag, last-push timestamp, latest tagged release). Internal claims are grounded in file reads of the live working tree (branch research/pyforge-comprehensive-refresh-2026-08-08).'
---

# Research Report: Technical Research — Kedro Ecosystem Adoption Gap + Stack Currency (3 Weeks Post-Ship)

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Technical (refresh — supersedes the currency half of the 2026-07-25 report; adds the Kedro-org tooling sweep and the cross-station adoption question)

---

## Research Overview

Three questions, in descending order of novelty:

1. **The Kedro-org tooling gap** (`docs/dreams/kedro-org-tooling-adoption.md`, dreamt 2026-08-07): Atlas runs Kedro exclusively but adopts almost none of the Kedro organization's own surrounding tooling. What exists, how mature is each piece, and what does that imply for the Dream's next step (a `bmad-spec`)?
2. **Stack currency**: is every component of the shipped Kedro/Dagster/DuckDB/BSL/Vizro stack still live, three weeks post-ship — and did the Dagster-under-Prefect risk (PRD Q2) move?
3. **Cross-station generalization**: Marshal's parallel cross-cutting unification research may propose the Kedro/Dagster/DuckDB stack for other stations. Is Atlas's use case actually representative of what Doctor / Warden / Mason do?

---

## 1. The full kedro-org repository sweep (2026-08-08)

`gh search repos --owner kedro-org` (21 repos), plus the plugin monorepo. The load-bearing rows:

| Repo | Stars | Latest release | Last push | Atlas status |
|---|---|---|---|---|
| `kedro-org/kedro` | 10,950 | **1.5.0** (2026-06-29) | 2026-08-07 | **Adopted** (`kedro >=1.5.0` pinned, `src/shared/packages/pyforge-atlas/pixi.toml`) |
| `kedro-org/kedro-viz` | 754 | **v12.4.0** (2026-05-27) | 2026-08-08 (today) | **Adopted for manual capture only** — `kedro-viz-proto` / `capture-kedro-viz-proto` pixi tasks drive a stub-mirror prototype (`src/prototype/packages/pyforge-atlas-kedro-viz`, 77 stub nodes / 81 datasets); no CI publishing |
| `kedro-org/kedro-plugins` (monorepo; `kedro-datasets` lives here — the standalone `kedro-org/kedro-datasets` repo now 404s) | 118 | rolling | 2026-08-07 | **Adopted** (`kedro-datasets >=9.5.0`) |
| `kedro-org/kedro-skills` | 1 | **v0.1.1 (2026-08-07 — the day the Dream was captured)** | 2026-08-07 | **Unadopted** — Dream target 1 |
| `kedro-org/publish-kedro-viz` | 18 | v3 (2025-11-25) | **2025-11-25 — dormant ~8.5 months** | **Unadopted** — Dream target 2 |
| `kedro-org/vscode-kedro` | 21 | v0.8.0 (2026-06-03) | 2026-08-07 | **Unadopted** — Dream target 3 (decision required, not adoption) |
| `kedro-org/kedro-mcp` | 3 | none tagged | **2025-11-06 — dormant ~9 months** | **Adopted, deliberately non-load-bearing** (FR-7: wrapped in `pyforge.atlas.mcp.server`, graceful-degrade test `test_kedro_mcp_absent.py`) |
| `kedro-org/kedro-builder` | 4 | — | 2026-06-12 | Not evaluated before — see § 1.5 |
| `kedro-org/kedro-starters` | 85 | 1.5.0-line | 2026-06-29 | N/A — Atlas scaffolded via `nebi` (FR-15), not a starter |

### 1.1 `kedro-skills` — the Dream's centerpiece is *younger than the Dream assumed*

The most consequential finding of this sweep: **`kedro-skills` v0.1.1 was released 2026-08-07 — the same day the Dream was captured — and the repo has exactly 1 star.** This is not a mature tool Atlas negligently skipped; it is a week-zero project ("Distribute AI coding skills to Kedro projects," Apache-2.0). Implications for the Dream's Spec:

- The Dream's "review before installing" constraint is even more load-bearing than written: at v0.1.1 the generated guidance content has essentially no field history, so an uncritical install into `.claude/skills/` would import unvetted, possibly generic advice into a repo whose Kedro usage is unusually constrained (AD-1 no-inline-IO AST scan, injected-fetcher seams, `kedro-catalog-check=38` invariant, credential-scoping allowlist — none of which generic Kedro guidance knows about).
- The **timing risk inverts**: rather than "we're late to adopt," the real risk is adopting guidance that contradicts Atlas's own architecture decisions. The Spec should frame the first story as an *audit of the generated content against the AD-invariants*, with adoption conditional, and should pin the tool's version.
- Conversely, this is the ideal moment to **contribute upstream**: Atlas is plausibly one of the most invariant-heavy Kedro deployments the kedro-skills authors could learn from, and the spec's standing posture ("contribute upstream where practical," § 4.5 re kedro-mcp) applies verbatim.

### 1.2 `publish-kedro-viz` — dormant, but the mechanism is trivial and Steward already owns its shape

Last push 2025-11-25 (~8.5 months quiet), pinned at major tag `v3`. A GitHub Action this thin (build `kedro viz --save-file` output, push to Pages) being quiet is not alarming — it is "done" software — but a dormancy note belongs in the Spec because the Action wraps kedro-viz's *build* interface, and kedro-viz itself is moving (v12.4.0, pushed today): a future kedro-viz major could strand a v3-pinned Action. Two adoption paths, per the Dream:

- **Path A (Dream-preferred)**: run the Action in CI on pushes touching `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**`, replacing the manual `capture-kedro-viz-proto` PNG/gallery tasks.
- **Path B (lower dependency risk)**: skip the dormant Action and have `steward deploy dashboard` (Epic 2, the mechanism the Dream itself names) publish the static `kedro viz build` output directly — same result, no third-party Action, consistent with how `docs/dashboard/` is already auto-published.

Given the dormancy telemetry, **Path B is the better-evidenced default** — the Dream asks for the *outcome* (always-current published DAG), not the specific Action.

- One repo-specific gotcha either path inherits: the published viz should be generated from the **real** `pyforge-atlas` package, not the stub prototype — the prototype exists only because the real DAG's viz needed dependency-free serving; a CI job running in the real `pyforge-atlas` pixi env removes that reason.

### 1.3 `vscode-kedro` — active, and the "agent-edited repo" deferral argument is factually sound

v0.8.0 (June 2026), pushed 2026-08-07 — this is a live, maintained extension (LSP, catalog validation, embedded viz, node debugging). The Dream requires a *recorded decision*, not adoption. Evidence for the deferral side: this repo's Kedro code was written ~entirely by bmad-loop agents (38/38 stories) and is maintained by agents; no `.vscode/extensions.json` exists anywhere in the repo today. Evidence for the adoption side: the extension's **catalog validation** duplicates a gate Atlas already has deterministically (`kedro-catalog-check`), so the marginal value is interactive-human-only. Recommendation for the Spec: **defer with the stated reason, plus a one-line `.vscode/extensions.json` recommendation as the zero-cost middle ground** (a recommendation file costs nothing and helps the rare human session).

### 1.4 `kedro-mcp` — the Dream's "already resolved" claim re-verified

Confirmed still resolved and still correctly scoped: the repo is quiet since 2025-11-06 with 3 stars — which *vindicates* FR-7's 2026-07-16 decision to wrap it rather than depend on it. Had Atlas made kedro-mcp load-bearing, it would now be depending on a 9-months-dormant 3-star project for its agent surface. No action; recorded so the Spec doesn't reopen it.

### 1.5 `kedro-builder` — new sighting, not in the Dream

"Design Kedro pipelines without touching YAML or Python boilerplate" (4 stars, pushed 2026-06-12). Recorded for completeness only: Atlas's pipelines are authored by agents against contract-tested invariants; a visual pipeline builder solves the opposite problem (human boilerplate friction). **Not recommended for the Dream's scope** — naming it here prevents a future "was this considered?" pass.

---

## 2. Stack currency refresh (vs the 2026-07-25 baseline)

All repos re-checked 2026-08-08; none archived, no license changes.

| Component | 2026-07-25 baseline | 2026-08-08 | Verdict |
|---|---|---|---|
| Kedro | v1.5.0, 10,931★, pushed 07-24 | v1.5.0, 10,950★, pushed 08-07 | Current, unchanged |
| Dagster | v1.13.15, 15,900★, 3 releases/16 days | **v1.13.17 (released 2026-08-07)**, 15,944★ | **Cadence intact ~4 weeks post-acquisition** — Q2 risk still not materialized |
| Prefect (acquirer) | v3.8.0 | v3.8.2 (2026-08-07) | Both codebases still separately live; no merge/archival |
| `kedro-dagster` (stateful-y) | 23★, pushed 07-25 | 23★, **pushed 2026-08-08 (today)**, still v0.7.0 (2026-06-03) | Bus-factor ≈ 1 confirmed again; actively pushed but **no release in 9+ weeks** — watch the v0.7.0→Kedro 1.5/Dagster 1.13.17 compatibility lag as the concrete-deterioration tripwire the 07-25 report asked someone to define |
| DuckDB | v1.5.5, 39,706★ | v1.5.5, 40,086★, pushed 08-07 | Current |
| Ibis | 12.0.0, 6,609★ | 12.0.0, 6,622★, pushed 08-08 | Current |
| BSL | 469★, pushed 07-23 | **v0.3.16 (2026-07-20)**, 474★, pushed 07-30 | Current; still young-but-real |
| Vizro | vizro-core 0.1.59, 3,762★ | **0.1.60 (2026-07-30)**, 3,774★, pushed 08-07 | Current — released *since* the last check |
| kedro-viz | (not separately checked 07-25) | v12.4.0, 754★, pushed 08-08 | Current |

**Proposed answer to the 07-25 report's open question ("what counts as concrete deterioration for kedro-dagster?"):** adopt a two-condition tripwire — (a) a Kedro or Dagster minor release that breaks `kedro-test`'s import smoke of the glue (AD-16 already exercises exactly this) **and** (b) no upstream `kedro-dagster` fix or acknowledged issue within 60 days. Either alone is noise; both together is the exit-ramp trigger (Dagster Components / Kedro's Prefect deployer, AD-1). This makes the standing "watch" operational instead of vibes-based, and the detector already exists in CI.

---

## 3. Should other stations adopt Kedro/Dagster/DuckDB? (the cross-station question)

Marshal's parallel unification research may propose stack convergence. Grounded in what the other stations' code actually does, the answer is: **Atlas's use case is genuinely distinct, and wholesale stack adoption by other stations would be cargo-culting — with two narrow, real exceptions.**

What earns Kedro/Dagster/DuckDB for Atlas (spec § 3.2/§ 4): **15+ phases of scheduled, TTL-gated, checkpoint-resumable ETL over ~20 external feeds**, producing typed datasets consumed by dozens of read surfaces — the exact workload the Data Catalog / DAG / incremental-materialization machinery amortizes. Compare:

- **Doctor** (`src/shared/packages/pyforge-doctor/`): a thin *gather-normalize-degrade* layer — per-invocation MCP/CLI calls into Atlas's own read surface, normalized into `Finding` tuples (`sources/atlas.py`). No persistent datasets, no schedules, no lineage. A Data Catalog would model nothing. **No case.**
- **Warden** (`docs/specs/pyforge-warden.md`): per-invocation compliance gating over a supplied manifest — stateless request/response with an exit code. Its axes *consume* pipeline-refreshed stores (vdb, KEV, EPSS) but those stores are **already Atlas's job** (B5 refresh assets). Moving Warden onto Kedro would relocate, not remove, complexity. **No case.**
- **Mason / Steward / Marshal / Herald / Scribe**: recipe validation, feedstock maintenance actuation, loop orchestration, deck rendering, memory capture — event-driven or interactive, none dataset-shaped. **No case.**
- **Exception 1 — upstream-discovery** (`specs/spec-upstream-discovery/SPEC.md`, draft): genuinely pipeline-shaped (trending snapshots, periodic classification) — and it is *already planned as nodes inside Atlas's own Kedro project* (its open question is which of the 7 pipelines hosts it), which is the correct resolution: one Kedro deployment, not a second one.
- **Exception 2 — DuckDB alone (not the stack)**: any station needing local analytical queries over Parquet (e.g., a future Doctor fleet-history trend store) should reach for DuckDB the *library* — that requires no Kedro, no Dagster, and is already in the shared env.

**Recommendation to feed Marshal's unification research:** the unifiable asset is not the stack, it is **Atlas as the fleet's single data platform** — stations integrate by *consuming Atlas datasets/MCP tools* (as Doctor already does), never by standing up sibling Kedro deployments. The real cross-station integration debt is on the consumption side, documented in the companion report (`technical-atlas-post-ship-debt-and-cross-station-integration-research-2026-08-08.md` § 3: every consumer today hits the **legacy** surface, not the migrated one).

---

## Assumptions

- `gh` repo telemetry (stars/push/release/archived) remains a currency proxy, not a roadmap read — same limitation as the 2026-07-25 report, same justification (the question is "still shipping?", which telemetry answers precisely).
- The cross-station assessment reads each station's shipped code and specs as of this branch; Marshal's parallel research was **not** read (it is running concurrently) — this report supplies Atlas's side of that conversation, not a rebuttal to a document that doesn't exist yet.

## Open Questions

- Should the kedro-skills upstream-contribution angle (§ 1.1) be a story in the Dream's Spec, or a separate goodwill task? (Leaning: one AC on the audit story — "file upstream issues for any guidance the audit finds wrong.")
- publish-kedro-viz Path B (§ 1.2) makes Steward the executor of an Atlas-owned outcome — the Dream already blesses exactly this split (owner ≠ mechanism), but the Spec must name which station's backlog carries the story.
- Does the § 2 kedro-dagster tripwire belong in Doctor's fleet-health checks (the 07-25 report's suggestion) now that Doctor's watch axes are live? A `stack-currency` axis over `gh api` telemetry would generalize this whole report into a scheduled check.

## Sources

- `gh api repos/{kedro-org/kedro, kedro-org/kedro-viz, kedro-org/kedro-plugins, kedro-org/kedro-skills, kedro-org/publish-kedro-viz, kedro-org/vscode-kedro, kedro-org/kedro-mcp, stateful-y/kedro-dagster, dagster-io/dagster, PrefectHQ/prefect, duckdb/duckdb, mckinsey/vizro, boringdata/boring-semantic-layer, ibis-project/ibis}` + `/releases/latest` (2026-08-08)
- `gh search repos --owner kedro-org` (2026-08-08) — the 21-repo org sweep, incl. the `kedro-builder` and `kedro-datasets`-404 findings
- Internal: `docs/dreams/kedro-org-tooling-adoption.md` (the Dream being evidenced); `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` §§ 3.2, 4.4–4.5, 13.2; `src/shared/packages/pyforge-atlas/pixi.toml` (live pins); `pixi.toml` (`kedro-viz-proto` / `capture-kedro-viz-proto` / `regenerate-kedro-viz-proto` task definitions); `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py`; `_bmad-output/projects/pyforge-atlas/planning-artifacts/research/technical-kedro-dagster-duckdb-stack-currency-research-2026-07-25.md` (the superseded baseline)
