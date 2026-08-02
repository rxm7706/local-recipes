---
title: Atlas — the map that maintains itself
type: dream
owner: atlas
status: realized
---

# Atlas — the intelligence layer an agent workforce can maintain

## The Dream

Chart the dependencies, map the world, define the floor — and make the map
maintainable by agents, not heroes. The legacy `cf_atlas` orchestrator was a
~10,000-line hand-rolled monolith: 23 phases whose data lineage lived in one
developer's head, each hand-rolling its own checkpointing and backoff, a
coarse 1800-second timeout able to silently drop a phase and still score the
run green. The dream was its rebirth as declarative dataflow — a DAG small
enough, pure enough, and contract-guarded enough that an autonomous agent can
add phase 24 by writing a node and declaring its datasets, inheriting
checkpointing, TTL, validation, lineage, and scheduling for free.

## What is real

- **Kedro + Dagster + DuckDB migration SHIPPED, 38/38 stories, 100%
  code-complete** — Waves 0 + A–H (32 stories, PRs #58–#105, 2026-07-17/18)
  plus Epic 10's post-audit truth-up (Stories I0–I5, through PR #132,
  2026-07-29). 930 real collected tests across 78 pytest files
  (`src/shared/packages/pyforge-atlas/tests/`), documented story-by-story in
  `test-architecture.md` (2026-08-02).
- Boring Semantic Layer models, a Vizro dashboard (8 pages + factory-status
  live; the full 28-CLI page inventory is deliberately deferred, `DW-D2-1`),
  Vizro-AI as an MCP-exposed NL interface, A2A agent-to-agent interfaces,
  OpenLineage + OTel tracing, DuckDB VSS, a Pyodide/DuckDB-WASM no-backend
  build (G1), Dagster sensors (dry-run proven; live daemon bring-up is an
  attended operational event, not code debt — see § Remaining), and Wave H's
  Karpathy-wiki agno compile/lint/Q&A crews.
- The intelligence signals that feed [[packaging-factory]]: staleness,
  feedstock-health, CVE watch, conda-native vulnerability advisories
  (Basilisk, via prefix.dev), release cadence, adoption stage, packaging
  velocity, migration readiness.
- Every one of the 11 epics/waves carries its own retrospective — the last
  two (Wave H's epic-format retro, Wave I's post-audit retro) were written
  2026-08-02, closing a "code newer than retro" currency gap that had been
  this chain's last dashboard finding.
- **2026-08-02 exemplar closure**: retired a duplicate dream
  (`pyforge-atlas-intelligence-platform.md`, whose entire "Realization" list
  restated already-shipped waves), corrected CAP-8/Story-D2/Epic-5 language
  that hadn't caught up with the 2026-08-01 dashboard-page scope correction,
  and wrote the two missing retros above. Result: 0 dream-chain-check
  findings, 0 dashboard currency findings, 0 gaps — clean for the first time
  this session.

## Lineage

Atlas's stack directly descends from [[sentinel]] (§19 Kedro · §20 Dagster ·
§27 BSL · §24 OTel/OpenLineage · §26 La Suite) — the ancestor dreamed the
stack, Atlas built it against the conda-forge domain. It also realized two
2026-04-25 roadmap wishes: the unified DAG orchestrator and the interactive
dashboard.

## The estate Atlas hosts

Atlas's project directory (`_bmad-output/projects/pyforge-atlas/`) is also
the planning home for three separate, substantial initiatives. None is a
capability of Atlas's own `cf_atlas` pipeline — `spec-pyforge-atlas`'s own
CAP-1..CAP-17 (the shipped migration) are untouched by any of the three.
**Update (2026-08-02):** two of the three — Unity Data Stack and Wasm
Analytics Stack — had their own separate Spec/PRD/Architecture chains until
an explicit user decision this same day overrode this repo's default
dream-level-only consolidation convention: their full chains were folded
into Atlas's own single brief/PRD/Architecture/Spec as `## Satellite:`
sections (capabilities renumbered `CAP-18`..`CAP-31`, architecture
invariants renumbered `AD-24`..`AD-56`), and their standalone planning
folders moved intact to
`archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/{briefs,prds,architecture,specs}/`
(not deleted — see those paths for the original standalone documents).
Upstream-discovery, the third initiative below, remains genuinely untouched.

- **[[unity-data-stack]]** — an enterprise Python-first, air-gap-first
  innersource monorepo platform: one workspace lock across native and PyPI
  dependencies, domain-owned data products in a Raw → Curated → Consumption
  layering (one reference domain, `customer`), a named trusted-committer
  contribution model, a machine-classified governance Constitution, a
  single `check-all` quality gate mirroring CI, and compliance delivered by
  integrating `pyforge-warden` rather than reimplementing it. Seeded
  2026-07-23 from three stranded gists; planned to Spec → PRD → Architecture
  depth by 2026-07-25, then folded into Atlas's own chain 2026-08-02 (see
  above). No epics/stories and no code yet — planning-complete, unscheduled.
- **[[wasm-analytics-stack]]** — a WASI Preview 2-sandboxed Excel-upload
  validation step ahead of a `dlt` → `dbt-duckdb` pipeline, natively traced
  end-to-end (one W3C trace ID, OTel + OpenLineage to Marquez) rather than
  bolted on, for OpenShift Restricted SCC. Its sandbox claim is proven, not
  asserted: a non-hollow isolation-verification gate mechanically fails if
  the component's declared capability surface is ever widened without a
  matching WIT change. Same depth as Unity: seeded 2026-07-23, Spec → PRD →
  Architecture by 2026-07-25, then folded into Atlas's own chain 2026-08-02
  (see above), honestly narrowed in-Spec from its founding gist's broader
  claim (DuckDB itself has no WASI build). No epics/stories, no code —
  planning-complete, unscheduled. A v2 dashboard onto its Gold tables would
  reuse Atlas's own G1 DuckDB-WASM/Pyodide pattern rather than reinvent it.
- **[[upstream-discovery]]** — sense GitHub-trending momentum and
  high-yield org releases, and carry worthy candidates into conda-forge
  before anyone files an issue. Re-grounded 2026-07-25 in Atlas's shipped
  Kedro dataflow after the legacy phase-based design
  (`docs/specs/trendshift-conda-forge.md`) was superseded by the migration.
  Earliest-stage of the three: a Spec only (`status: draft`,
  `specs/spec-upstream-discovery/SPEC.md`), no PRD, no Architecture, zero
  implementation — six open questions remain, including which of Atlas's 7
  closed pipelines should host it.

## Remaining

- Three ATTENDED boundary events, not code debt — each deferred to an
  operator-present event rather than a story: the credentialed legacy-parity
  sign-off and retirement (`DW-B4-2`), the F1 cold/warm benchmark
  (`DW-F1-1`), and bringing the Dagster daemon live (`DW-C1-1`, `DW-G3`,
  `DW-H4`). Tracked in `deferred-work-ledger.md`.
- The full 28-CLI dashboard-page inventory beyond the 8 shipped + factory
  status — `DW-D2-1`.

## Realization log

- **2026-06-20 → 07-16** — spec authored and analyzed (v5.6).
- **2026-07-17 → 07-18** — planned and BUILT via bmad-loop; Waves 0 + A–H
  shipped (32 stories, PRs #58–#105).
- **2026-07-23** — Dream retro-seeded; chapter deck `presentations/pyforge-atlas/`;
  the three satellite dreams below seeded from the gist audit, `owner: atlas`.
- **2026-07-23 (gist audit)** — grounding: the Ecosystem Health Report v2
  (Basilisk §6) is atlas-intelligence output; LF AI & Data landscape kept as
  reference.
- **2026-07-25** — `unity-data-stack` and `wasm-analytics-stack` planned to
  PRD + Architecture depth; `upstream-discovery`'s Spec authored, superseding
  the legacy trendshift phase design.
- **2026-07-29** — Epic 10 (post-audit truth-up, Stories I0–I5) shipped via
  PR #132; 38/38 stories done.
- **2026-08-02** — exemplar closure: retired the duplicate
  `pyforge-atlas-intelligence-platform.md` dream, corrected stale CAP-8
  claims, wrote the two missing per-wave retros — 0 dream-chain-check
  findings, 0 dashboard currency findings, 0 gaps.
- **2026-08-02 (this pass)** — dream-level consolidation: folded the three
  satellites' narrative into § The estate Atlas hosts above. Each satellite
  dream now carries a superseding blockquote and `status: archived` /
  `archived-reason: absorbed`.
- **2026-08-02 (same day, explicit user override)** — full chain
  consolidation for two of the three: Unity Data Stack's and Wasm Analytics
  Stack's own Spec/PRD/Architecture were folded into Atlas's single
  brief/PRD/architecture/Spec (capabilities renumbered `CAP-18`..`CAP-31`,
  architecture invariants renumbered `AD-24`..`AD-56`); their standalone
  planning folders moved intact to `archive/` under this project's
  `planning-artifacts/` tree, not deleted. This supersedes the same-day
  dream-level-only note above for these two — upstream-discovery's own
  chain remains untouched and continues independently.
- **2026-08-02 (Dream-coverage audit, this pass)** — audited the just-merged
  brief/PRD/architecture/Spec chain against this Dream for content with
  execution weight (epics/sprint-status/code) or genuine unscheduled intent
  that this Dream didn't yet name, per the repo's Dream-first convention.
  Checked all 17 primary CAPs/23 ADs plus all 14 satellite CAPs
  (`CAP-18`..`CAP-31`) against `epics.md`, `sprint-status.yaml`, and
  `src/shared/packages/pyforge-atlas/` (grep for `unity`, `wasi`,
  `componentize-py`, `wasmtime`, `basilisk`): confirmed zero epics/stories/
  code for both satellites (matches this Dream's own "no epics/stories, no
  code" claim exactly) and confirmed one primary-chain shipped signal —
  Basilisk, the conda-native vulnerability source (FR-19/CAP-14, Story B8,
  `datasets/basilisk.py`) — was real but under-named here (only an unrelated
  "Basilisk §6" report-section reference existed); named it explicitly
  above. Enriched both satellite bullets with capabilities their full
  fold-in carries but this Dream's prior one-paragraph summaries didn't
  (Unity: air-gap-first, domain data products, trusted-committer model,
  unified `check-all` gate; Wasm: native OTel/OpenLineage tracing to
  Marquez, the non-hollow isolation-verification gate) — all judged genuine,
  researched, unscheduled scope, not speculative or superseded, so **no
  pruning**: nothing was cut from the merged brief/PRD/architecture/Spec.
