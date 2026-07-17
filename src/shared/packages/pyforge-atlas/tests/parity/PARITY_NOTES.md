# Parity-diff fixtures — provenance & scope (Story B1)

The `parity-diff` gate is the Wave-B verify gate. It is **built incrementally
B1→B3 and consumed at the attended B4 event** (AD-11 / AD-19).

## B1 contribution (this story)

- **Harness skeleton** (`harness.py`): a node dispatch registry + a fixture loader +
  an order-independent frame-diff engine. Runs in **fixture mode** — `--frozen`,
  non-credentialed, offline (network never touched).
- **Core + VCS fixtures** for the **11 phases ported here** (B, B.5, B.6, F, I, J, M,
  E, E.5, K, L, N — `compute_downloads` covers F's four outputs in one fixture): one
  captured input frame + the captured legacy OUTPUT snapshot per node, in the tracked
  test tree (`fixtures/{core,vcs_health}/*.json`). The gate **never reads
  `.claude/data/`**.
- The `parity-diff` pixi task runs `pytest tests/parity`.

## Fixture provenance (IMPORTANT — B1 vs B4)

B1's fixtures are **representative legacy-shaped seeds** that encode the per-phase
**engineering contracts** on small, hand-authored inputs (e.g. Phase B.5's
`dbt-bigquery → dbt-bigquery` umbrella-vs-dedicated attribution; Phase F's
`downloads_source` per row ∈ {anaconda-api, s3-parquet} (never `merged` — that
is a run-summary label only, CFA:189-193; corrected by the B1 follow-up review),
s3-only breakdowns, and
calendar-month `downloads_30d`). They prove the migrated node reproduces the legacy
contract shape + values on the representative case.

The **full B4 credentialed live-parity run** — the exact row-count + value parity on
the `v_actionable_packages`-family views under the Q1 default, from real operator
runtime data — is **NOT in B1 scope** (AD-19, attended). B4 replaces these seeds with
snapshots captured once, attended, from operator runtime data (spine "Tests &
fixtures" row) and consumes this same harness.

## AC-5 — the Phase E maintainer-universe delta (DOCUMENTED, not reconciled)

Per AC-5's "reconciles — **or explicitly documents**" branch, B1 DOCUMENTS the delta
(full reconciliation deferred to B4):

- atlas `package_maintainers` = **769** (537 sole + 232 co, build 2026-06-19)
- cf-graph `node_attrs` discovery = **813** (558 + 255, `conda-forge-tracker.md`)
- Δ ≈ **44** feedstocks (spec:287-292)

The ~44-feedstock disagreement is a data-quality investigation beyond one story. It is
recorded here and in the `enrich_maintainers` node docstring; B1 and B4 are both named
owners in spec § 3.3, and B4 finalizes the reconciliation.
