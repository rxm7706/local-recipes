---
title: Configurable per-project invocation
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: 73f95d4bb239bf7e3e2ae7f7ad457ce819598c8d
followup_review_recommended: true
deferred:
  - summary: >-
      CAP-5 help prose hard-codes defaults instead of deriving text from
      `cap5_defaults()`, inviting future doc/code drift.
    evidence: |-
      Review pass noted help strings in cli/planning.py duplicate the
      default matrix returned by core.chain_regen.cap5_defaults(). Cosmetic;
      tests assert both surfaces independently today.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/planning.py
    severity: low
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

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 1, low 4)
- defer: 1: (high 0, medium 0, low 1)
- reject: 12
- addressed_findings:
  - `[low]` `[patch]` Added `resume: False` to `cap5_defaults()` + defaults test.
  - `[low]` `[patch]` Help assertion now requires CAP-5 term `stage`.
  - `[medium]` `[patch]` Added CLI handler tests: `--chain-mode minimal` reaches orchestrator; `--minimal`+`--chain-mode full` emits MRS-CHAIN-001 without starting a chain.
  - `[low]` `[patch]` Conflict finding `path` set to `flags: --minimal/--chain-mode` (not repo root).
  - `[low]` `[patch]` Harness test asserts `never … scripts/bmad-switch` jointly, not bare `never`.

## Auto Run Result

Status: done

Summary: CAP-5 polish for `marshal planning chain-regenerate`. Same workflow against any station via documented parameters (`project_slug`, `dream_path`, `chain_mode`, `preserve_code_status`, `stage`, `apply_orphans`, `resume`). Defaults: Full / preserve on / stage+apply off / never auto-commit. Added `--chain-mode {full,minimal}` consistent with `--minimal`, `cap5_defaults()`, CLI/help CAP-5 docs, multi-slug tests (`pyforge-marshal` + `pyforge-doctor`), harness `BMAD_ACTIVE_PROJECT` / no-`bmad-switch` coverage. Never `scripts/bmad-switch`. Ledger finalize after merge (Epic 21 closeout).

Files changed:
- `cli/planning.py` — CAP-5 docs; `--chain-mode` + `resolve_chain_mode()`; conflict finding path
- `core/chain_regen.py` — CAP-5 docs; `cap5_defaults()` (incl. resume)
- `tests/unit/test_chain_regen.py` — defaults, help, two-slug, handler wiring, harness env

Review findings: 5 patches applied (1 medium, 4 low); 1 deferred (help/defaults drift); 12 rejected (eight-station matrix, concurrent multi-station CLI, naming aliases, etc.). Follow-up review recommended: true (score = 3×1 medium + 4 low = 7).

Verification: `pixi run -e pyforge-marshal pyforge-marshal-test` → **6283 passed**, 12 deselected; `test_chain_regen.py` CAP-5 block → 10 passed.

Admin merge: PR https://github.com/rxm7706/local-recipes/pull/710 merge SHA `3155ec626b0c87a9a522f20589e4ef2ac212d4a4` via `gh pr merge --merge --admin` (GitHub Actions billing blocks CI; local tests green).
