# Addendum — cf_atlas Kedro/Dagster/DuckDB Migration PRD

Depth that belongs in downstream documents (architecture, epics, execution
planning) rather than the PRD body. Sources: spec v5.6 §§ 4, 13, 15; PRFAQ
kill-test; the four 2026-07-16 research artifacts.

## 1. Rejected alternatives (with rationale)

| Alternative | Verdict | Rationale |
|---|---|---|
| **Null alternative** — keep legacy + Phases U/V/W (the three new signals) + per-sub-step timeouts + logging | Rejected (fairly priced: ~5 stories, zero parity risk, zero new deps) | Fully fixes the acute defects but not the chronic per-phase machinery tax, agent-hostility, rigid read surface, or lineage invisibility. Right choice IFF intelligence ambitions freeze at 23 phases / 28 questions — the § 12.1 + § 13.1 candidate backlogs say they don't. |
| Neo4j / Kùzu / LanceDB / Polars | Rejected | DuckDB singularity: one engine for compute (Parquet-native), graph (recursive CTEs), vector (`vss`). |
| `spec-kit` agent framework | Rejected | `bmad-method` governs the agent workforce (spec § 7.3). |
| prefix.dev GraphQL as metadata backend | Evaluated, not promoted | No vulnerability types; duplicates repodata; per-package model unfit for bulk. Hook retained: `variants.yankedReason` for Phase B.6 full yanked detection. |
| `kedro-great-expectations` / `kedro-pandera` plugins | Banned | Outdated; validator-agnostic custom `AfterNodeRunHook` instead. |
| `litellm` LLM router | Excluded | Proxy stack breaks on the repo Python 3.14 floor (Q3 bounds). |
| Legacy-first Phase U for Basilisk | Default-declined (Q7) | Build once as Kedro nodes; interim legacy port only if a pre-migration window matters. |

## 2. Tool bets, glue policy, exit ramps (architecture input)

- Pillars healthy: Kedro (LF AI & Data Graduate), DuckDB, Vizro. **Risk
  concentrates in the glue**: `kedro-dagster` (bus factor ≈ 1, `dagster <2.0`
  pin), `kedro-mcp` (0.1.2, guidance-scoped), boring-semantic-layer
  (two-person 0.x), Dagster under the Prefect acquisition (2026-07-13).
- Doctrine: **glue stays thin and replaceable; the Kedro DAG is the source of
  truth**; MCP tools authored over Kedro session/catalog APIs directly;
  ingest methods over artifacts.
- Exit ramps: Dagster Components or Kedro's Prefect deployer (orchestration);
  Ibis-over-SQLite severability ramp for the D/G read surface (fallback, not
  plan — building BSL on the legacy schema would ossify the retired store).
- GX version ceiling: conda-forge 1.18.2 imports on py3.14 (live-verified);
  upstream `<3.14` from 1.19.0. Lesson encoded: verify constraints against
  the conda-forge build in the live env, not PyPI declarations.

## 3. Verify-task inventory (loop gates — named story deliverables)

| Task | Story | Proves |
|---|---|---|
| `kedro-test` | A1 | Scaffold + lean env + unit suite runs `--frozen` |
| `kedro-catalog-check` | A2 | Catalog resolves; no inline IO |
| `parity-diff` | B1–B3 (build), B4 (consume + sign-off) | Fixture-based legacy-vs-Kedro dataset diff (full credentialed run = attended B4 event; spec § 2.5 "B1–B4" vs B4-AC "B1–B3" read as build-vs-consume) |
| `dagster-dryrun` | C1 | Definitions load, schedules enumerate, no live execution |
| `bsl-metric-check` | D1 | BSL answers match legacy CLI outputs on core metrics |
| `wasm-smoke` | G1 | Playwright headless load-and-query of the built WASM artifact |

All fixture-based, non-credentialed, tracked in the test tree (never
`.claude/data/`), run `--frozen`.

## 4. Execution economics (from the technical research + pyforge pilot)

- bmad-loop v0.8.1 is sequential (`max_parallel = 1`); dashboards observe
  artifacts, not sessions; no PR lifecycle (PR-per-wave wraps local squash-merge).
- Keystone budget pre-raises: B1, B2, F1 (pilot burned 25.8M tokens on a
  keystone story). Worktree pixi-env materialization cost is why A1 ships a
  lean dedicated env; A3 is the worktree/symlink smoke.
- Upstream bmad-loop feature requests to file (not this effort's scope):
  resume-on-timeout, retry-from-preserved-attempt, PR-lifecycle hook.

## 5. Market/domain intelligence retained for later triage

- Scenario B (community conda-CVE-mapping OSV feed): HIGH, time-sensitive
  demand (SIG unconstituted; CRA clock 2026-09-11; Trivy #1856 / Syft #932 /
  osv-scanner #1129 / Dependabot #2227 blocked on it; Alpha-Omega lane
  unclaimed). Everything it needs is already in scope; the OSV-export surface
  is the § 12.1 candidate, activation-gated on SIG constitution. The
  time-sensitive move is operator engagement with the SIG — an operator
  action, not a migration story.
- Scenario C (open PSM alternative): narrative-only (curation-parity trap).
  Scenario A (public dashboard): weakest; D2 factory-status page suffices.
- Watch items: Dependabot conda GA is version-only/security-blind (re-check at
  wave gates); OpenAI acquired Astral (uv/Ruff) Mar 2026; Snyk Advisor
  shutdown single-sourced; NVD enrichment retreat (Apr 2026) — audit vdb's
  NVD-derived fields; CISA BOD 26-04 four-variable matrix = FR-18's recorded
  future threshold mode.
- Regulatory posture: the pipeline is a consumer/steward-support tool, not a
  manufacturer — no CE obligations; CRA alignment nearly free.
- Sustainability grades + full source/feed slot matrix: spec § 13.1 (the
  one-row-edit governance surface).

## 6. Config values used by this run (pixi unavailable)

- `planning_artifacts` = `_bmad-output/planning-artifacts` (symlinked to
  `projects/pyforge-atlas/planning-artifacts`).
- Run folder: `prds/prd-pyforge-atlas-2026-07-17/` (project
  slug substituted for global `project_name` — see PRD § 9.6).
- `user_name` Rxm7706; languages English; date 2026-07-17.
