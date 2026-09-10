---
title: 'The CFE pin is derived, never stamped'
type: 'fix'
created: '2026-09-09'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
final_revision: ''
context:
  - _bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py
warnings: []
deferred: []
declared_low_risk: true
baseline_revision: 'e15c12a98a4fd3e76466b39e48ba2dd0cdbc56fc'
---

<intent-contract>

## Intent

**Problem:** `bmad-drift` reports seventeen live `pin-behind` warns on marshal artifacts because each stamps a CFE version literal in `source_pin:` frontmatter while `.claude/skills/conda-forge-expert/SKILL.md:10` reads a newer `version:` — the literal goes stale within hours of every hand pass.

**Approach:** Derive the live CFE version from `SKILL.md` frontmatter (`version:`) for currency checks. Treat `source_pin` on living and plan docs as a re-grounding record (a fact about a past act), not a currency claim — suppress `pin-behind` for those categories. Keep `pin-behind` on snapshot docs (INFO, non-gating). Rewrite SYNC-RUNBOOK row 84 to state the distinction normatively.

## Boundaries & Constraints

**Always:** Read live skill version from `SKILL.md` frontmatter `version:` (derive-don't-declare). Preserve `pin-missing` for all tracked categories. Preserve snapshot `pin-behind` at INFO severity. Genuine content staleness continues via `count-stale`, `phase-list-stale`, `stale-rule`, and baseline `surface-changed` — not suppressed.

**Never:** Hand-bump seventeen marshal artifact pins to silence warnings. Remove `source_pin` from tracked docs. Import `pyforge.marshal`. Change snapshot-doc pin-behind semantics.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| LIVING_OLD_PIN | Living doc with `source_pin: conda-forge-expert v8.86.1`, live SKILL.md `version: 8.90.1` | No `pin-behind` finding | `pin-missing` still fires if pin absent |
| PLAN_OLD_PIN | Plan doc (PRD) with old pin, live SKILL newer | No `pin-behind` finding | Same |
| SNAPSHOT_OLD_PIN | Snapshot doc with old pin, live SKILL newer | `pin-behind` at INFO (OK status) | Unchanged from pre-fix |
| SKILL_UNREADABLE | SKILL.md missing or no `version:` in frontmatter | `bmad-drift-unevaluable` WARN from `check_pins`; `pin-missing` half still runs | Never silent clean |
| LIVE_MARSHAL | Real pyforge-marshal project tree | Zero `pin-behind` WARN on living/plan tracked docs | `count-stale` etc. may still WARN |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py:434-436` — `_skill_version` reads CHANGELOG today; change to SKILL.md frontmatter `version:`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py:537-569` — `_live_version` uses `_skill_version`; error message must name SKILL.md
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py:687-725` — `check_pins`: skip behind-ness for `living`/`plan` categories
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py:99-119` — `_seed_ground_truth` must seed SKILL.md frontmatter with `version:`
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py:232-360` — pin-behind tests: living → no behind; snapshot → still behind
- `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md:86-89` — row 84 pin-behind reconciler text

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py` — derive live version from SKILL.md; suppress pin-behind for living/plan — core fix
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py` — update fixtures and pin-behind matrix tests
- `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` — rewrite pin-behind rows for derived-pin semantics

**Acceptance Criteria:**
- Given marshal tracked living/plan docs with stale `source_pin` literals and live SKILL.md at 8.90.1, when `bmad-drift-check` runs, then zero `pin-behind` WARN findings on those docs
- Given a snapshot tracked doc with stale pin, when `bmad-drift-check` runs, then `pin-behind` reports at INFO (OK) unchanged
- Given SYNC-RUNBOOK row 84 updated, when an operator reads it, then the derived-pin vs re-grounding-record distinction is stated once and normatively

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (review layers skipped — single-pass low-risk fix with matrix tests green)

## Auto Run Result

Status: done

**Summary:** Live CFE version is now derived from `SKILL.md` frontmatter `version:`. `pin-behind` is suppressed for living/plan marshal docs (source_pin is a re-grounding record); snapshot docs retain informational pin-behind. SYNC-RUNBOOK row 84 rewritten.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py` — derive live version from SKILL.md; suppress living/plan pin-behind
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py` — fixture + matrix tests updated
- `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` — derived-pin reconciler row
- `spec-33-10-…md` — story contract
- `sprint-status-ledger.yaml` — 33-10 → done

**Review:** 0 patches from review layers; implementation verified directly.

**Verification:** `pytest -k test_sources_factory` → 61 passed; `bmad-drift-check` → zero living/plan `pin-behind: warn` (snapshot INFO only).

**Residual risks:** Baseline fingerprint `skill_version` now reads SKILL.md not CHANGELOG — operators should re-stamp baseline after merge if `surface-changed` fires.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-doctor-test -- tests/unit/test_sources_factory.py -q` — expected: all pass
- `pixi run -e local-recipes bmad-drift-check 2>&1 | rg 'pin-behind.*warn'` — expected: no living/plan pin-behind warn lines (empty or snapshot-only)
