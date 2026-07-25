---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-atlas.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - src/shared/packages/pyforge-atlas/pixi.toml
research_type: 'technical'
research_topic: 'Currency check on the Kedro + Dagster + DuckDB (+ BSL/Ibis, Vizro, duckdb-wasm) stack bets underpinning the SHIPPED pyforge-atlas migration'
research_goals: 'Verify — 9 days after the migration shipped (2026-07-18) — whether each stack component is still actively maintained, whether any pinned/adjacent bet has deprecated or destabilized, and specifically re-check the PRD''s own named risk (Dagster under Prefect acquisition, `kedro-dagster` bus-factor ≈ 1) against live repository evidence rather than repeating the PRD''s dated claim unverified.'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
scope_note: 'LIGHT + RETROSPECTIVE scope. The stack is not being chosen here — it already shipped. This report is a POST-HOC currency audit, structured around the PRD''s own Q2 re-verify checkpoint ("re-verify the Dagster bet at Wave C start... switch on concrete deterioration, not headlines") and the architecture spine''s AD-1 exit-ramp framing, not a greenfield technology evaluation.'
methodology_note: 'The session WebSearch budget was exhausted (200/200) before this report began. Per the task''s explicit fallback instruction, every currency claim below is grounded in `gh api`/`gh repo view` calls against each project''s live GitHub repository (stargazer count, license, last-push timestamp, latest tagged release) captured 2026-07-25, i.e. primary-source repository telemetry rather than search-engine summaries or blog posts. This is a narrower evidence base than a full web survey would give (no community-sentiment or roadmap-announcement signal), but it directly answers the load-bearing question — "is this still an actively shipping project, under what license, as of today" — with higher precision than a secondary source could.'
---

# Research Report: Technical Research — Kedro/Dagster/DuckDB Stack Currency Check

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Technical (light, retrospective — post-hoc currency audit)

---

## Research Overview

The Kedro + Dagster + DuckDB migration (Waves 0 + A–H, 32/32 stories, PRs #58–#105) shipped 2026-07-18 — seven days before this report runs. Rather than re-litigating the stack choice, this report does what the PRD itself scheduled: re-verify each named bet against live evidence at a checkpoint after the initial decision, specifically the Q2 Dagster/kedro-dagster re-check the PRD deferred to "Wave C start" (already passed during the shipped build) and now again post-ship. The question this report answers is narrow and falsifiable per component: **is it still an actively maintained, non-archived project, and has anything changed since the 2026-07-17 architecture spine was written?**

---

## 1. Kedro — the DAG substrate (AD-1)

`gh repo view kedro-org/kedro` (2026-07-25): **10,931 stars**, latest release **v1.5.0** (published 2026-06-29), last push 2026-07-24 — actively shipping within the last 24 hours of this report. No deprecation or maintenance-mode signal found. **Currency: confirmed current, no change from the architecture spine's assumption.**

## 2. Dagster + `kedro-dagster` — the orchestration layer (AD-1, AD-6) — the PRD's own named risk

This is the one component the PRD explicitly flagged as at-risk: *"Dagster under Prefect acquisition watch — Q2 re-verify at Wave C start"* and *"kedro-dagster bus factor ≈ 1."* Both halves re-checked independently:

- **Dagster itself:** `gh repo view dagster-io/dagster` shows **15,900 stars**, last push 2026-07-24, and the releases feed shows **three tagged releases in the sixteen days before this report** (v1.13.13 on 2026-07-09, v1.13.14 on 2026-07-16, v1.13.15 on 2026-07-23) — release cadence has **not** slowed since the acquisition the PRD dated to 2026-07-13. This is a meaningful finding: the PRD's risk framing was "acquisition watch," not "acquisition confirmed harmful" — and the release-cadence evidence twelve days post-acquisition shows no visible deceleration. The risk is not resolved (an acquired project's roadmap can still shift later), but it has **not yet materialized** as the "concrete deterioration" the PRD's own mitigation language conditions the exit ramp on.
- **Prefect (the acquirer), for context:** `gh repo view PrefectHQ/prefect` shows **23,480 stars**, latest release **v3.8.0** (2026-07-23), last push 2026-07-25 — also actively shipping, independently of the Dagster acquisition. Both codebases remain separately live as of this report; no repository-level merge or archival has occurred.
- **`kedro-dagster` (the glue plugin):** `gh search repos kedro-dagster` finds the actual maintained plugin at **`stateful-y/kedro-dagster`** — **23 stars**, last updated 2026-07-25 (today) — plus a `conda-forge/kedro-dagster-feedstock` (confirming it is available as a conda-forge package, relevant to Atlas's conda-forge-only provisioning constraint, FR-15) and a small scattering of forks/examples with zero stars. **This independently confirms the PRD's own "bus factor ≈ 1" characterization** — one primary maintainer org, a low star count, no visible second maintainer team — though the plugin is evidently still being actively pushed to (today's date), so "low bus factor" is a real, unresolved structural risk, not a currently-observed maintenance lapse.

**Net finding:** the PRD's Q2 risk framing holds up under a fresh, independent check — neither better nor worse than the PRD already assumed. The architecture spine's exit ramps (Dagster Components, Kedro's Prefect deployer) remain the correct mitigation; nothing in this pass changes that calculus. This is the report's one genuine "watch it, don't act on it yet" finding.

## 3. DuckDB + `vss` + `duckdb-wasm` — the compute singularity (AD-4)

- **DuckDB core:** `gh repo view duckdb/duckdb` shows **39,706 stars**, latest release **v1.5.5** (2026-07-22), last push 2026-07-24. Actively and rapidly shipping.
- **`duckdb-wasm`** (the Wave-G WASM portability target, FR-14): **2,082 stars**, last updated 2026-07-25 (today) — actively maintained, and a healthy surrounding ecosystem exists (`sqlrooms`, `duckdb-wasm-kit`) building on it, evidence the WASM path is not a dead end.
- **`vss` (vector similarity search extension, Story F3):** DuckDB's extension ecosystem itself remains actively developed as part of the core 1.5.x release cadence; no deprecation signal found for the `vss` extension specifically in this pass (flagged as a residual gap below — the extension-specific changelog was not independently fetched).

**Currency: confirmed current.** No changes to the AD-4 rationale (Neo4j/Kùzu/LanceDB/Polars rejection) are indicated by anything found here.

## 4. Boring Semantic Layer (BSL) + Ibis — the semantic translation interface (AD-8)

- **Ibis** (`ibis-project/ibis`): **6,609 stars**, last push 2026-07-24 — very actively maintained, the dataframe/SQL-translation substrate BSL is built on.
- **`boring-semantic-layer`** (`boringdata/boring-semantic-layer`): **469 stars**, last updated 2026-07-23 — a real, independently-maintained OSS project (not an Atlas-internal invention), with a visible surrounding demo ecosystem (`dlt-hub/boring-semantic-layer-demo`, a `conda-forge` feedstock, and third-party DuckDB-integration demos) that corroborates it is used beyond its own maintainers.

**Currency: confirmed current.** BSL is a young-but-real, actively-shipping project (469 stars is modest but the commit cadence and third-party demo ecosystem are healthy signals for a semantic-layer library at this stage of the category's maturity).

## 5. Vizro / Vizro-AI — the read surface (AD-8, FR-9)

`gh repo view mckinsey/vizro`: **3,762 stars**, latest release **vizro-core-0.1.59** (2026-06-18), last push 2026-07-24 — actively maintained by McKinsey's open-source team, healthy release cadence.

**Currency: confirmed current.** No deprecation signal; the 28-CLI-to-Vizro-page migration (Story D2) and the `query_vizro_ai` MCP tool (Story D3) rest on an actively-shipping project.

## 6. CycloneDX + purl — the SBOM/identity standards underpinning FR-13/FR-17/FR-18

`gh repo view CycloneDX/specification`: latest release **1.7.1** (2026-06-02) — directly confirms the PRD's own claim ("CycloneDX 1.7 = ECMA-424... in flight") is accurate and, in fact, the 1.7.x line has already shipped a point release since the architecture spine was written.

---

## Cross-Domain Synthesis: Is the Bet Still Current?

| Component | Architecture-spine assumption (2026-07-17) | 2026-07-25 live check | Verdict |
|---|---|---|---|
| Kedro | Source of truth, `[ADOPTED]` (AD-1) | v1.5.0, 10.9k★, pushed yesterday | **Unchanged — current** |
| Dagster | Acquired-by-Prefect risk, Q2 re-verify at Wave C (already passed during build) | 15.9k★, 3 releases in 16 days post-acquisition, no cadence slowdown | **Unchanged — risk noted, not materialized** |
| `kedro-dagster` | "Bus factor ≈ 1," replaceable glue | 23★, single maintainer org (`stateful-y`), still pushed today | **Confirmed — the PRD's own risk characterization is accurate, not overstated or understated** |
| DuckDB + `vss` | Compute singularity, AD-4 | 39.7k★, v1.5.5, pushed yesterday | **Unchanged — current** |
| `duckdb-wasm` | WASM portability target (FR-14) | 2.1k★, pushed today, healthy demo ecosystem | **Unchanged — current** |
| BSL / Ibis | Single semantic translation interface (AD-8) | Ibis 6.6k★ very active; BSL 469★ real+active | **Unchanged — current** |
| Vizro / Vizro-AI | Read surface (FR-9) | 3.8k★, June 2026 release, active | **Unchanged — current** |
| CycloneDX 1.7 / purl | "In flight" per PRD § 10 | 1.7.1 shipped 2026-06-02 | **Confirmed shipped, ahead of the PRD's "in flight" framing** |

**Overall finding: no deprecations, no archived repositories, no stack-bet reversals found anywhere in this pass.** The single live risk (Dagster/`kedro-dagster`) is exactly the one the PRD already named and already built exit ramps for — this report's contribution is independent, dated confirmation that the risk is real but not (yet) acute, seven days after ship.

---

## Assumptions

- This is a **currency check, not a re-architecture** — no component swap is recommended; the exit ramps named in the architecture spine (AD-1: Dagster Components, Kedro's Prefect deployer) remain the correct mitigation path if the Dagster/Prefect risk materializes further.
- `vss` extension-specific release notes were not independently fetched (residual gap, noted rather than papered over) — the finding above rests on DuckDB core's healthy overall cadence, not a `vss`-specific changelog read.
- Star counts and push timestamps are a coarse maintenance-liveness proxy, not a substitute for reading actual roadmap commitments — appropriate given this report's narrow, falsifiable question ("still shipping, as of today?") rather than a deep due-diligence pass.

## Open Questions

- The PRD's Q2 checkpoint says "switch on concrete deterioration, not headlines" — what would count as *concrete* deterioration for `kedro-dagster` specifically, given it is already single-maintainer? (E.g., a maintenance gap of N months, or an unresolved breaking-change issue against a new Kedro major version.) Not defined here; worth a follow-up threshold if this becomes operationally relevant again.
- Should Atlas's own `llms-full-check` drift gate (already in place per the PRD's provisioning discipline) be extended to periodically re-run this exact currency check (star/release/archived-status) for its pinned stack, rather than relying on an ad-hoc research pass? Flagged as a possible Doctor (`pyforge-doctor`) fleet-health check candidate, not an Atlas change.

## Sources

- `gh repo view kedro-org/kedro` (2026-07-25)
- `gh repo view dagster-io/dagster` + `gh api repos/dagster-io/dagster/releases` (2026-07-25)
- `gh repo view PrefectHQ/prefect` (2026-07-25)
- `gh search repos kedro-dagster` (2026-07-25) — resolves the maintained plugin to `stateful-y/kedro-dagster`
- `gh repo view duckdb/duckdb` (2026-07-25)
- `gh search repos duckdb-wasm` (2026-07-25) — resolves to `duckdb/duckdb-wasm`
- `gh repo view ibis-project/ibis` (2026-07-25)
- `gh search repos "boring semantic layer"` (2026-07-25) — resolves to `boringdata/boring-semantic-layer`
- `gh repo view mckinsey/vizro` (2026-07-25)
- `gh repo view CycloneDX/specification` (2026-07-25)
- Internal: `_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md` § 10 ("Why Now"), § 11 (Risks & Mitigations, Q2); `.../architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md` AD-1/AD-4/AD-6/AD-8 — the claims being re-verified, not new evidence
