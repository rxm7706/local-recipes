---
doc_type: research-distillation
research_type: 'corpus gap analysis'
research_topic: 'Docs-corpus sweep: what the 17 sibling specs + docs/ know that the cfe-atlas-datapipeline Kedro migration spec must incorporate'
date: 2026-07-16
status: complete
provenance: >
  Backfilled distillation (written 2026-07-16, same day). This research was
  executed as a 4-agent parallel sweep whose findings were folded DIRECTLY
  into the migration spec as v5.1 (commit 479d6be) without a standalone
  artifact; this document preserves the evidence trail retroactively. It did
  NOT run through a BMAD research workflow — it is a faithful distillation of
  the agent findings as reported in-session.
outcome: 'All actionable findings folded: spec v5.1 (479d6be); GX verdict later corrected at the v5.2 correction (see spec § 15).'
---

# Research Distillation: Docs-Corpus Gap Analysis for the Kedro Migration Spec

**Method**: four parallel read agents over ~24k lines — (1) `docs/` + execution-tooling specs, (2) atlas-adjacent intelligence specs (trendshift / cyclonedx / pyforge-warden / seed-gaps / lts-registry), (3) feedstock & packaging-effort specs (as atlas *consumers*), (4) the 7,764-line `cfe-shipped-releases.md` archive — each briefed with the migration spec's then-current (v5) coverage so it reported only deltas, with file:line evidence.

**Disposition**: every Tier-1/2 finding was folded into the spec the same day (v5.1); Tier-3/4 landed as one-liners and the § 12.1 candidate-signals table. One finding was later corrected (GX — see Errata).

## Tier 1 — Corrections (the spec stated something wrong or stale)

| Finding | Evidence source | Landed as |
|---|---|---|
| § 2 execution stack fiction: spec said "BMAD v6.8.0 + BAD module"; adopted reality = bmad-method 6.10.0 (core+bmm, 46 skills) + bmad-loop v0.8.1 + bmad-dev-auto; `bmad-create-prd`/`-architecture` deprecated | `bmad-loop-adoption.md` W1–W4; `library-llms-full.md` | v5.1 § 2.2/2.5/§ 14 rewrite |
| FR-18 exit-code collision: shipped `inventory-match --policy` uses 0=pass/**2=policy/1=error** — inverted vs pyforge-warden's frozen enum FR-18 targets | `cyclonedx-universe-inventory.md` (reconciliation note); `pyforge-warden.md` (frozen lattice) | v5.1 FR-18 reconciliation obligation + `INVENTORY_MATCH_LEGACY_EXIT` window |
| `ComplianceReport` is four-axis (hygiene+security+license+currency, per-axis `gating`; D12 re-baseline 2026-07-16) — spec described two axes | `pyforge-warden.md` D12 | v5.1 FR-16/FR-18/F4 update |
| Phase P misdescribed: BigQuery is the only implemented source (ClickHouse = documented fallback, not code); opt-in `PHASE_P_ENABLED=1`, admin-only | `cfe-shipped-releases.md` Phase-P release notes | v5.1 § 3.3/§ 5.4/B2 |
| Story A1 half-done: the entire Kedro/Dagster/DuckDB/Ibis/BSL/Vizro stack already resolved in-env; real gates = py3.14 floor + pins + `llms-full-check` | `library-llms-full.md` §§ 7–8 | v5.1 FR-15/A1 reframe |

## Tier 2 — Missing binding constraints

| Finding | Evidence source | Landed as |
|---|---|---|
| Per-phase engineering contracts: Phase P two-layer cost gate (+`test_no_thirty_gb_lie`, a real $500+ invoice), Phase K secondary-rate-limit token bucket (3 RPS single worker), Phase F provenance discipline (`downloads_source` non-interchangeable; s3-only breakdown tables; DELETE-by-scope-key; calendar-month `downloads_30d`), Phase H serial gate (pypi-only denominator bug), post-v25 schema shape (dropped tables stay dropped), EPSS 0–100, notes survive Phase S, per-phase TTLs (D 7d / P 30d / EPSS 1d / CWE 90d) | `cfe-shipped-releases.md` (agent 4, per-phase notes) | v5.1 § 3.3 engineering-contracts bullet + B1/B2 ACs + FR-3 |
| JFrog credential leak: `_http.py` injects `X-JFrog-Art-Api` on every outbound request regardless of host | `enterprise-deployment.md` | v5.1 FR-1 per-host scoping (fix, not port) |
| Second routing layer: pixi/uv resolver needs `.pixi/config.toml` `[pypi-config]` (JFrog index, sharded-repodata disable, files.pythonhosted bypass) — separate from `_http.py` | `enterprise-deployment.md` § 4 | v5.1 FR-15/A1 |
| Trendshift Phase T conditional surface (+1 phase, 2 tables, 1 view, 1 CLI, 1 MCP tool, 2 feeds, v30; never-hard-fail + no-trendshift-scrape invariants) | `trendshift-conda-forge.md` Track A | v5.1 § 3.3 conditional-surface bullet + § 13.1 Conditional row |
| Maintainer-universe discrepancy: atlas 769 (537 sole/232 co) vs cf-graph 813 (558/255) — two discovery paths disagree by ~44 | `feedstock-refresh.md` vs `conda-forge-tracker.md` | v5.1 § 3.3 data-quality gap + B1 AC |

## Tier 3 — Read-surface & operational confirmations

- Live-confirmed CLI consumers (`behind-upstream`, `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`, `detail-cf-atlas`, `staleness-report`) + the raw `package_maintainers ⋈ maintainers` JOIN pattern → v5.1 D1/D2 ACs (maintainer-role as BSL dimension; consumer set ports first). _Source: feedstock-refresh / feedstock-failure-remediation._
- Live-verify-over-cached mandate (G66/G74/G78 across langflow/flyte/db-gpt) → v5.1 § 3.4 freshness boundary (pipeline snapshots advisory for submission gating).
- Q3 bounds: vizro-ai in-env; litellm excluded (py3.14); copilot bridge TOS-bound single-dev; llama.cpp/ollama/mlx-lm as local options → v5.1 Q3 text. _Source: library-llms-full / copilot-to-api._
- FR-7 audit scope: second unregistered MCP server `tools/gemini_server.py` → v5.1 § 3.3 MCP bullet. _Source: claude-team-memory.md._
- `ANACONDA_API_BASE` as a distinct override (detail-cf-atlas build-matrix chain) → v5.1 § 3.3 + § 13.1. _Source: enterprise-deployment § 5._

## Tier 4 — Candidate signals (recorded, not committed)

Seven wished-for signals hand-rolled by the packaging efforts (per-subdir channel-propagation lag G66; closure view with blocker naming; `constrains`-axis pin skew G67; transitive python_min floor G40/41; noarch-ARM coverage G40/82; duplicate-submission detection G58; source-kind-aware version deltas) → v5.1 § 12.1 table with demand evidence.

## Errata

- The related same-day domain research initially graded great-expectations "uninstallable on py3.14" from PyPI metadata; the **v5.2 correction** (spec § 15) established the conda-forge 1.18.2 build imports on py3.14.6 live — GX is Committed, version-capped. Lesson: verify against the conda-forge build in the live env, not PyPI declarations alone.
- The corpus sweep's own outputs were verified against the live factory by `bmad-drift-check` (green at fold time); two INFO items it did not address (planning artifacts pinned at v8.76.0; index.md env count) remain the SYNC-RUNBOOK reconciler's job.

**Full agent-report texts**: this session's transcript (2026-07-16); spec deltas: `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` § 15 decision log (v5.1 row); commit `479d6be`.
