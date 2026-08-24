---
title: Configurable per-project invocation
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 33d71ef2bf
---

<intent-contract>

## Intent

**Problem:** Chain regeneration must run unmodified against any of the 8 stations by parameters only — never hardcoded per station (FR-192 CAP-5; spec-fleet-chain-completeness).

**Approach:** Parameterize `marshal planning chain-regenerate` with `project_slug`, `dream_path`, `chain_mode` (`full` default | `minimal`), `preserve_code_status` (default true), `stage` (default false), `apply_orphans` (default false), `resume`. `auto_commit` remains false and is not offered. Cross-station: physical `_bmad-output/projects/<slug>/planning-artifacts/...` paths + `BMAD_ACTIVE_PROJECT=<slug>` per invocation; never concurrent `scripts/bmad-switch`. Deps: 21.2–21.4 done. Completes Epic 21.

## Acceptance Criteria

- Same workflow definition runs against any of 8 stations by varying only documented parameters.
- Defaults match resolved SPEC: Full chain, preserve on, stage/apply off, never auto-commit.
- Multi-station (if supported in one run) uses literal physical paths + per-invocation env; never `bmad-switch`.
- CLI/help documents all CAP-5 parameters; tests cover at least two distinct project_slugs.
- Epic 21 CAP-1…CAP-5 complete after this story (21.1 audit already shipped).

## Boundaries & Constraints

**Never:** Hardcode station paths. Never offer auto-commit. Never `scripts/bmad-switch`. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-fleet-chain-completeness/SPEC.md` (CAP-5)
- Extends: `cli/planning.py`, `core/chain_regen.py` parameter surface
- Tests: multi-slug invocation; default matrix; no bmad-switch / no auto-commit

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Smoke: `--project` + `--dream` against two fixtures without code changes per station
