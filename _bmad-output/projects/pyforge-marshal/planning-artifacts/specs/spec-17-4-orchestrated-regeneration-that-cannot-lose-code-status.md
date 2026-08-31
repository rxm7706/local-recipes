---
title: Orchestrated regeneration that cannot lose code status
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: a38a2dbdfb
---

<intent-contract>

## Intent

**Problem:** Regenerating a project's Dream→Spec→…→epics chain is still manual and fragile (FR-148); a regen can rewrite story keys and lose `done` code-status (FR-149); orphaned specs/epics have no review-gated report path (FR-151). Story 17.3 shipped layer presence only — not orchestration.

**Approach:** Add `marshal chain regenerate` — one CLI/orchestration invocation that runs a named project's planning phases in dependency order, reuses `scripts/promote_sprint_status.regressions` so every pre-regen `done` key stays byte-identical (only backlog may restructure), and reports orphaned specs/epics for review (nothing deleted). Per-project only (AD-72). Full BMAD-skill backends remain Epic 21.2 (Q1); this story ships the marshal orchestrator + guard + orphan report with an injectable phase runner.

## Boundaries & Constraints

**Always:** Physical `_bmad-output/projects/<slug>/…` paths; `BMAD_ACTIVE_PROJECT=<slug>` semantics without calling `scripts/bmad-switch`; reuse `promote_sprint_status.regressions` (never a second done-guard); report orphans, never delete; leave Story 17.3 `--layers` audit unchanged.

**Block If:** Operator requires a live LLM skill backend as the default phase runner before this story can ship (that is Epic 21.2 / Q1).

**Never:** Blind-delete orphans. Never rewrite `done` story keys. Never `scripts/bmad-switch`. Never mutate another station's tree. Never reimplement BMAD skill derivation. Finalize marshal ledger only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ordered phases | `--project acme` with injectable runner | Phases run `spec→prd→architecture→epics` in that order | Fail stops later phases |
| Done preserved | Ledger has `1-1: done`; runner proposes drop/backlog | Write refused; `regressions` names the key; ledger unchanged | MRS-CHAIN-003 ERROR |
| Backlog restructure | Only backlog keys change; done untouched | Ledger write allowed; done keys byte-identical | No error |
| Orphan report | Spec `owner-dream:` points at missing Dream | Orphan listed; files not deleted | MRS-CHAIN-004 WARN |
| Isolation | Two projects under `--root`; regenerate A | Only A's tree/ledger touched | No error |
| Missing project | Unknown slug / no planning tree | UNEVALUABLE finding; no write | MRS-CHAIN-001 |
| Dry-run default | No `--apply` | Phases + orphans reported; no ledger write | No error |
| Layers audit intact | `chain-completeness --layers` | Behavior unchanged by this story | No error |

</intent-contract>

## Code Map

- `src/.../marshal/cli/chain.py` — new `chain regenerate` verb (nested like `deploy`/`seed`)
- `src/.../marshal/core/chain_regen.py` — phase order, report types, orphan scan, guard application
- `src/.../marshal/cli/main.py` — register `add_chain_subparser`
- `src/.../marshal/core/findings.py` — register `MRS-CHAIN-001..004`
- `scripts/promote_sprint_status.py` — **read-only reuse** of `regressions` / `render` / `ledger_path_for` via importlib (same pattern as `cli/deploy.py::_load_promote_sprint_status`)
- Story 17.3 `gather_chain_layers_audit` / `--layers` — leave intact; optional pre/post evidence only
- `tests/unit/test_chain_regen.py` — I/O matrix fixtures
- Continuity: Story 17.3 layers audit; Story 15.2 promote regressions pin; Epic 21.2 owns live skill backends (Q1)

## Tasks & Acceptance

**Execution:**
- `core/chain_regen.py` — define `CHAIN_PHASES`, report dataclasses, `find_orphans`, `apply_status_guard`, `run_regeneration`
- `cli/chain.py` — `marshal chain regenerate --project` (+ `--apply`, `--root`, `--format`); default dry-run
- `cli/main.py` + `findings.py` — wire subparser + MRS-CHAIN codes
- `tests/unit/test_chain_regen.py` — cover I/O matrix (order, done guard, orphans not deleted, isolation)
- `pixi.toml` — document `marshal-chain-regenerate` task if helpful; regenerate `environment.yaml` only if pixi.toml changes

**Acceptance Criteria:**
- Given a named project fixture, when `marshal chain regenerate --project <slug> --apply`, then phases execute in dependency order and only that project's tree is mutated
- Given pre-regen `done` keys, when a phase proposes dropping or downgrading them, then the write is refused and keys remain byte-identical
- Given orphan specs (missing Dreams) or epics referencing orphan/missing specs, when regenerate runs, then orphans are reported and no orphan file is deleted
- Given no `--layers` change, when Story 17.3 audit runs, then behavior is unchanged

## Spec Change Log

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1 (Epic 21.2 live BMAD-skill backends / Q1 — explicitly out of this slice)
- reject: 0
- Notes: Default PlanPhaseRunner records planned skills + status-guard merge; live skill execution deferred to Epic 21.2. Matrix rows covered by test_chain_regen. 17.3 --layers untouched.


## Design Notes

- **Invocation shape (Story 17.4 slice):** `marshal chain regenerate` with injectable `PhaseRunner`. Default runner records planned skill names (`bmad-spec`→`bmad-prd`→`bmad-architecture`→`bmad-create-epics-and-stories`) and, on `--apply`, merges proposed statuses through `regressions` before any ledger write. Live LLM skill execution is explicitly Epic 21.2 (Q1 still open there).
- **Guard:** import `regressions` from `scripts/promote_sprint_status.py` — one guard, no fork.
- **Orphans:** report-only; cleanup stays review-gated (operator deletes).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/667
Merge SHA: 7aa120fe86084d5590366ce5b8538636dae403c0
Tests: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 5786 passed, 12 deselected
Layers audit: Story 17.3 `chain-completeness --layers` unchanged / still runnable
