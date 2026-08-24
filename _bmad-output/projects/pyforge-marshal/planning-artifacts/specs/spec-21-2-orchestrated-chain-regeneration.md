---
title: Orchestrated chain regeneration
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: d77af3b4f3b772efa46f9b384435326b09b4d4fd
review_loop_iteration: 0
followup_review_recommended: true
deferred:
  - summary: >-
      Soft code-linkage verify reports missing cites in detail but always
      completes; tightening to fail/block is a product choice beyond CAP-1.
    evidence: |-
      Review found verify_code_linkage returns status=complete with missing
      cite counts in detail only. AC requires read-only verify then orphan
      report; failing the chain on linkage gaps was not specified.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/chain_regen.py
    severity: low
  - summary: >-
      Dual CLI: marshal chain regenerate (17.4) coexists with marshal planning
      chain-regenerate (21.2) without deprecation cross-link.
    evidence: |-
      Story 17.4 intentionally shipped the four-phase dry-run verb; 21.2 adds
      the Full orchestrated verb. Documentation/deprecation is out of CAP-1.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/chain.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Regenerating Dream→Spec→Research→Brief→PRD→Architecture→Epics still requires hand-carrying files between BMAD skills (FR-192 CAP-1; spec-fleet-chain-completeness Q1–Q4 now resolved).

**Approach:** Ship `marshal planning chain-regenerate --project <slug> --dream <path>` that orchestrates skills headlessly via the FR-52 harness seam. Default mode **Full** (all eight Dream phases including `bmad-deep-recon` → `bmad-product-brief`). Optional `--minimal` skips Research/Brief. Resume-from-phase journal under `planning-artifacts/.chain-regen/<run-id>/`. Per-invocation `BMAD_ACTIVE_PROJECT` + physical paths (never `scripts/bmad-switch`). Deps: none for CAP-1 core; Q1–Q4 resolved 2026-08-23. Do not implement CAP-2 code-status preservation (21.3), CAP-4 orphan apply (21.4), or CAP-5 parameter polish (21.5) beyond what CAP-1 needs to run.

## Acceptance Criteria

- `marshal planning chain-regenerate` invokes Full phase order: bmad-spec → bmad-deep-recon → bmad-product-brief → bmad-prd → bmad-architecture → bmad-create-epics-and-stories → code-linkage verify (read-only) → orphan **report** (manifest only; apply is 21.4).
- `--minimal` skips phases 2–3.
- Run journal at `planning-artifacts/.chain-regen/<run-id>/state.yaml`; `--resume` continues last incomplete phase; skill `blocked` halts; transient failure retries current phase ≤2×.
- Skills driven through FR-52 harness; memlog-derivation invariant preserved (never hand-overwrite derived artifacts).
- Regeneration output left unstaged; never auto-commit/push.
- Does not implement Stories 21.3–21.5 beyond stub hooks needed for CAP-1.

## Boundaries & Constraints

**Never:** Absorb skill logic. Never `scripts/bmad-switch`. Never auto-commit. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-fleet-chain-completeness/SPEC.md` (CAP-1; Q1–Q4 resolved)
- `cli/planning.py`, `core/chain_regen.py`, FR-52 harness seam (`ports/skill_invoke.py`, `adapters/skill_invoke_harness.py`)
- Journal under `_bmad-output/projects/<slug>/planning-artifacts/.chain-regen/`
- Tests: Full phase sequence, `--minimal`, resume, blocked halt, retry, no-commit

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Unit/integration covering phase orchestration + journal resume

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 3, medium 5, low 1)
- defer: 2: (low 2)
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` Distinct finding codes: blocked=`MRS-CHAIN-005`, failed=`MRS-CHAIN-002`; registered in findings.py
  - `[high]` `[patch]` Retry + exhausted-failure tests (`fail_times=1` / `fail_times=3`)
  - `[high]` `[patch]` Write orphan manifest on blocked/failed early exit
  - `[medium]` `[patch]` `_parse_status` whitespace-tolerant; bare exit 0 without STATUS → failed; unit tests
  - `[medium]` `[patch]` Subprocess timeout via `MARSHAL_SKILL_TIMEOUT` (default 3600s)
  - `[medium]` `[patch]` Safe int parse for journal `attempts`; resume project mismatch guard
  - `[medium]` `[patch]` Empty/path-traversal project slug rejected in CLI
  - `[medium]` `[patch]` Catch `SkillInvokeError`/`OSError` into envelope
  - `[low]` `[patch]` Gitignore `.chain-regen/` run journals

## Auto Run Result

Status: done

Summary: Shipped `marshal planning chain-regenerate` with Full 8-phase orchestration (or `--minimal`), FR-52 `SkillInvokePort` (plan default; `--live` optional), journal resume under `.chain-regen/<run-id>/`, ≤2 retries/phase, blocked halt, orphan report only, CAP-2/4/5 stub hooks. Review patches applied for finding codes, retries, orphan-on-halt, harness parsing/timeout, and input guards.

Files changed:
- `cli/planning.py` — new planning verb
- `cli/main.py` — register planning subparser
- `core/chain_regen.py` — Full/minimal orchestrator + journal
- `ports/skill_invoke.py` + `adapters/skill_invoke_harness.py` — FR-52 seam
- `core/findings.py` — `MRS-CHAIN-005`
- `tests/unit/test_chain_regen.py` — orchestration matrix
- `.gitignore` — ignore `.chain-regen/`

Review findings: 9 patches applied; 2 deferred (soft linkage, dual CLI); follow-up recommended (high patches present; score ≥5).

Verification: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 6264 passed, 12 deselected.

Admin merge: (filled after merge)

Residual risks: default invoker is plan/dry-run (no live LLM unless `--live`); CAP-2/4/5 remain stubs.
