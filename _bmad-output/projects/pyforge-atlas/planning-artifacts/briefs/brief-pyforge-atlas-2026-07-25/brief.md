---
title: 'Product Brief: Atlas (pyforge-atlas)'
status: complete
created: 2026-07-25
updated: 2026-07-25
inputs:
  - 'docs/dreams/pyforge-atlas.md'
  - 'docs/dreams/pyforge-charter.md § 3 Atlas'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/research/domain-dependency-intelligence-ecosystem-observability-research-2026-07-25.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/research/technical-kedro-dagster-duckdb-stack-currency-research-2026-07-25.md'
  - 'src/shared/packages/pyforge-atlas/ (shipped package — README.md, pyproject.toml, tests/)'
note: 'RETROSPECTIVE brief — Atlas shipped 2026-07-18 (32/32 stories, PRs #58-#105) before the factory adopted the research-first convention (2026-07-25 campaign). This brief backfills the missing product-brief tier and describes what was actually built and why it was worth building, grounded in the real, shipped evidence — it is not a pre-build planning input.'
---

# Product Brief: Atlas (pyforge-atlas)

## Executive Summary

Atlas is the pyforge Guild's intelligence station: the conda-forge packaging factory's
data layer, rebuilt from a ~10,000-line hand-rolled orchestrator into a declarative
Kedro + Dagster + DuckDB pipeline that any autonomous agent — not just the one
developer who wrote it — can safely extend. The migration shipped **2026-07-18**,
**32 of 32 stories complete** across Waves 0 and A–H, merged through **PRs #58–#105**,
driven end-to-end by the `bmad-loop` orchestrator (Marshal). It replaced 23 cataloged
pipeline phases and 28 bespoke CLIs with **seven modular Kedro pipelines**, one
DuckDB-backed compute engine, a Boring Semantic Layer translating raw datasets into
named metrics, a Vizro/Vizro-AI read surface, and MCP/A2A machine interfaces — all
over a **19,726-feedstock** conda-forge population as of the spec's full-population
run. This brief is retrospective: Atlas already exists, is in daily use feeding the
`conda-forge-expert` skill's atlas-intelligence layer (staleness, feedstock health,
CVE watch, release cadence, adoption stage, migration readiness), and this document
grounds *why the bet was worth making*, not whether to make it.

## The Problem (as it stood before the migration)

The legacy `cf_atlas` orchestrator worked — it shipped real signal for years — but its
cost was **chronic, not acute**: every new phase hand-rolled its own checkpointing, TTL
gating, and backoff; data lineage lived in one developer's head; execution was
observable only via stdout; and ad-hoc questions required hand-written SQL against a
single SQLite file. The load-bearing failure mode, named explicitly in the PRD's PRFAQ
kill-test (CONDITIONAL PASS, 2026-07-16): **autonomous agents cannot safely extend a
10,000-line procedural monolith.** As the factory's actual workforce shifted from "one
developer occasionally touching this code" to "loop-driven BMAD agents adding phase 24
unattended," the monolith became the single biggest risk to the whole packaging
factory's autonomy story — not a performance problem, an *agent-maintainability*
problem.

## The Solution (what shipped)

Atlas replaced procedural call-order with a declared DAG, in three structural moves
validated against comparable dependency-intelligence platforms (domain research,
2026-07-25):

- **Seven domain pipelines, one producer per dataset** (Core; PyPI Intelligence;
  Vulnerability; VCS & Health; Universal SBOM; Seed-Gaps; Read-Surface/Derived-
  Artifacts) — every source and output is a `conf/base/catalog.yml` entry, credentials
  scoped per destination host (fixing, not porting, the legacy `_http.py` global JFrog-
  header-injection defect). This decomposition independently matches how ecosyste.ms
  and deps.dev structure their own much-larger cross-ecosystem graphs (typed,
  independently-versioned data services rather than one monolith) — convergent
  validation, not a novel bet.
- **DuckDB + Parquet as the compute singularity** (Neo4j/Kùzu/LanceDB/Polars all
  rejected as separate engines) — one engine for analytical compute, recursive-CTE
  graph traversal, and `vss` vector search, reading partitioned Parquet natively.
  `IncrementalParquetDataset` carries per-dataset TTL semantics (Phase D 7d, Phase P
  30d, EPSS 1d, CWE 90d, …) in one reusable class, deleting the bespoke `phase_state`
  checkpoint table entirely.
- **Dagster (via `kedro-dagster`) orchestrates; the Boring Semantic Layer (Ibis →
  DuckDB) is the one read-surface translation interface** — the 28 legacy CLIs became
  Vizro pages plus a Vizro-AI natural-language field and the `query_vizro_ai` MCP tool;
  23 of the 46 MCP tools in `conda_forge_server.py` were audited and re-authored over
  Kedro session/catalog APIs so agents trigger pipelines and read datasets without
  `kedro-mcp` ever being load-bearing.

Three new signal sources rode the migration as additive riders, never its
justification (PRFAQ discipline): **Basilisk** (conda-native vulnerabilities via
prefix.dev), **release-to-availability velocity** (median ≈ 8.9h, ~72.4% within 24h at
calibration), and **migration-readiness** classification (noarch / rebuild-done /
confirmed-pending / not-in-tracker) over conda-forge-bot-data's migration tracker.

## What Makes This Different

Atlas's "moat," to the extent an internal tool has one, is not novelty — the technical
research (2026-07-25) confirms every stack bet (Kedro, Dagster, DuckDB, Ibis/BSL,
Vizro, CycloneDX 1.7) remains actively maintained seven days after ship, with no
deprecations found. The one genuinely differentiated design choice is **scope
discipline**: unlike libraries.io, ecosyste.ms, or deps.dev — all general-purpose,
many-ecosystem platforms serving many outside consumers — Atlas is conda-forge-only,
by name in FR-15, serving exactly one operator and one agent workforce. That
narrowness is what let the whole migration ship as 32 stories in roughly a month
instead of an open-ended cross-ecosystem platform build, and it is a defensible choice
given Atlas's actual user base of one human plus the BMAD agent fleet — not a gap to
close later. The other genuine differentiator, validated against the domain research,
is that Atlas's **own freshness is a first-class, queryable signal**
(`staleness-report`/`behind-upstream` against per-dataset TTLs) — a property none of
the three external comparables expose about themselves to an outside observer.

## Who This Serves

- **The operator (rxm7706)** — maintains ~769-feedstock coverage without babysitting a
  monolith: watches a Dagster-rendered DAG instead of tailing stdout, re-runs only
  what's stale, and trusts that bad data halts (pandera contracts) instead of silently
  persisting.
- **`conda-forge-expert` authoring-agent sessions** — query package, vulnerability, and
  readiness intelligence through MCP tools with consistent semantics; receive
  structured signals via A2A (e.g., a Basilisk advisory hand-off to the recipe-
  authoring loop).
- **BMAD execution agents** (`bmad-loop` / `bmad-dev-auto`) — the load-bearing user:
  extend the pipeline by adding a node, declaring its datasets, and inheriting
  checkpoint/TTL/backoff/contract machinery for free, verified by deterministic
  fixture gates rather than tribal knowledge.
- **CI** — consumes one schema-validated artifact and one frozen exit-code gate
  (via the optional `pyforge-atlas[gate]` extra into pyforge-warden's
  `ComplianceReport`) instead of scraping 28 CLIs' text output.

This is explicitly an internal, non-commercial product — the PRD's own 2026-07-16
market research found "feeds > pages" demand (machine-consumable data over a public
dashboard), and the D2 "factory status" Vizro page is the intentionally narrow public-
facing surface, not a growth vector.

## Success Criteria (as delivered)

- **SM-1 (Parity before retirement):** the B4 attended parity gate reported zero
  material drift against the legacy `cf_atlas.db` on the `v_actionable_packages`-family
  views before the legacy orchestrator was retired.
- **SM-2 (Agent-maintainability — the load-bearing metric):** the three new-signal
  stories (Basilisk, velocity, migration-readiness) landed as nodes + catalog entries +
  pandera contracts with zero hand-written checkpoint/TTL/backoff code, and all
  loop-drivable stories executed under `bmad-loop` without any gate being weakened or
  removed to hit the target — the anti-metric (SM-C2) held.
- **SM-3 (Incremental re-materialization):** warm-incremental refresh re-runs only
  affected nodes; the F1 benchmark recorded both the warm-incremental win and the
  honest cold-full wall-clock against the network-bound 3–4h legacy baseline — the
  counter-metric (SM-C1) explicitly forbade over-claiming an engine-swap cold-start
  miracle, and the shipped evidence didn't chase one.
- **SM-4/SM-5 (Read-surface + agent-surface completeness):** every read-only legacy
  CLI question is answerable from a Vizro page or its FR-9-named exception artifact;
  `query_vizro_ai` is callable via MCP; the MCP trigger/read surface and the A2A
  payload hand-off both work end-to-end from a BMAD agent session.
- **All 8 per-epic retrospectives remain optional** (recorded in sprint-status, not
  gating) — the only formally open item against the shipped scope.

## Scope (what actually shipped, Waves 0 + A–H)

| Wave | Delivered |
|---|---|
| 0 | SKF legacy-translation skill (execution scaffolding) |
| A | nebi scaffold, data catalog (20 override points + credential scoping), `IncrementalParquetDataset` |
| B | Node ports (conda-side + PyPI/vuln), MCP audit, B4 parity sign-off, external-refresh assets, seed-gaps, SBOM intake, **Basilisk**, **velocity**, **migration-readiness** |
| C | Dagster compilation + schedules (`kedro-dagster`), `kedro-viz` |
| D | BSL models, Vizro dashboard (28 CLIs ported), Vizro-AI + MCP tool |
| E | A2A interface, OpenLineage + OpenTelemetry |
| F | DuckDB consolidation + benchmark, pandera validation hooks, `vss` similarity search, hygiene + policy gate |
| G | WASM/Pyodide portability, static Parquet host, Dagster sensors |
| H | Karpathy wiki scaffold + personas, agno crews, Wagtail/La Suite CMS sync, Dagster-triggered crews |

**Explicitly out of scope (spec § 12, held):** Neo4j/Kùzu/LanceDB/Polars as separate
engines; continued SQLite/`phase_state` orchestration; `spec-kit` as agent framework;
standalone binaries/JVM; new external data sources beyond the committed set (legacy
GitHub/PyPI/Anaconda + Basilisk + conda-forge-bot-data); a public OSV-format export
feed or public dashboard productization; rewriting the recipe-authoring skill itself.

## Vision (where it points next)

The PyForge Charter names Atlas's mandate as durable — "chart the dependencies, map
the world, define the floor" — and the shipped migration is the substrate the rest of
the Guild now builds on: Warden consumes Atlas's KEV/EPSS/Basilisk/velocity/mapping
data as one input to its compliance axes (one-directional data dependency, no code
import back), and any future PyForge Doctor fleet-health verb would query Atlas's
`feedstock-health`/`staleness-report`/`behind-upstream` surfaces directly rather than
re-deriving them. The domain research's one open question — whether an
OpenSSF-Scorecard-style maintenance signal (named as a vision-tier axis in the
Charter's Warden entry) belongs in Atlas as a joined feed or in Warden as a gate — is
recorded as a future-scope question, not a v1 gap: Atlas's own precedent (KEV/EPSS
joined, never re-scored) already answers *how* it would be built if evidence ever
gates it in.

## Open Questions (carried forward, none v1-blocking)

- Should Atlas ever expose a public, versioned API tier (deps.dev-style stable/alpha
  split) beyond today's MCP-tool-mediated agent access? Deferred — no evidence gates
  it yet, and the PRD's own promotion discipline requires measured evidence before any
  such FR is written.
- The 8 optional per-epic retrospectives remain the only recorded open item against
  the shipped 32/32 scope.
- `kedro-dagster`'s single-maintainer bus-factor risk (confirmed live by the
  2026-07-25 technical research, not just assumed) remains a watch item, not an
  active problem — the architecture's named exit ramps (Dagster Components, Kedro's
  Prefect deployer) are the standing mitigation if it deteriorates further.

## Assumptions

- No market-facing sections (TAM/pricing/GTM/competitive-share) — Atlas is an internal
  data platform with one human operator and an agent workforce as its only consumers,
  never sold, marketed, or positioned against libraries.io/ecosyste.ms/deps.dev, which
  this brief and its supporting domain research treat strictly as architectural
  reference points.
- **Retrospective grounding, not speculative planning**: every claim above is sourced
  from the shipped PRD/architecture/epics artifacts, the shipped package at
  `src/shared/packages/pyforge-atlas/`, and the two 2026-07-25 research reports — this
  brief backfills a missing tier for a project that shipped seven days before the
  research-first convention existed; it does not propose new work.
- Headless/express drafting: produced without an interactive discovery conversation,
  consistent with the other backfilled briefs in this campaign (Doctor, Herald, Mason,
  Scribe, Steward).
