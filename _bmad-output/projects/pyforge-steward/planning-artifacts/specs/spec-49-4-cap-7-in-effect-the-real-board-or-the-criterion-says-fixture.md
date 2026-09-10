---
title: 'CAP-7 in effect — the real board, or the criterion says fixture'
type: 'feature'
created: '2026-09-10'
status: 'in-review'
baseline_revision: 47afe2e983346381768071e644df772d171e14d3
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/convergence.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards/SPEC.md
  - src/platform/tests/test_host_board_row_isolation.py
  - src/shared/packages/django-atlas/src/django_atlas_portal/board.py
warnings: []
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** CAP-7's success criterion implies Atlas's full Vizro/BSL analytical board on the host,
but the only host-mounted board today is a 5-row JSON fixture (`django_atlas_portal/board.py`) and
the isolation test explicitly asserts the real Vizro stack is not mounted — so CAP-7 reads
"shipped-but-not-in-effect" on the Residual list despite the fixture fully exercising two-user row
isolation.

**Approach:** Record the operator ruling (2026-09-10): CAP-7's deliverable is the role-isolated
JSON fixture board at `/stations/atlas/board/` adopting the secure-dashboard pattern
(`filter_by_role`, `AccessDeclaration`, `get_master_dataset`). Rewrite CAP-7's intent/success/
verified text and downstream docs to name the fixture honestly; defer `spec-secure-live-dashboards`
Django half (INSTALLED_APPS + audit/export wiring) in the same act. Atlas's 34-page Vizro board
stays package-local (`dashboard-dryrun`, `:8050` serve) — out of CAP-7 scope.

## Boundaries & Constraints

**Always:**
- The dated ruling and both branches must be recorded where CAP-7 is graded (`SPEC.md`,
  `convergence.md`, `spec-secure-live-dashboards`).
- Existing host isolation tests must keep passing unchanged — the fixture is the deliverable, not a
  gap to remove.
- Correct "never adopted" → "adopted at fixture grade" with file:line citations.

**Never:**
- Do not mount Vizro on the host URLconf in this story (that is the alternate branch, not chosen).
- Do not add `pyforge.steward.dashboard` to `INSTALLED_APPS` or wire audit/export (deferred with
  the fixture ruling).
- Do not change fixture row data or filtering behavior — docs and criterion only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| FIXTURE_RULING | Two users, same `/stations/atlas/board/` URL | Disjoint row sets (east 3, west 2) via steward filtering | Existing tests cover this |
| CRITERION_REWRITE | CAP-7 before edit | Intent/success/verified name fixture; Residual drops CAP-7 | N/A |
| CONVERGENCE_CORRECTION | convergence.md:38,:129 | "Adopted at fixture grade" with board.py citations | N/A |
| SECURE_DASHBOARDS_DEFER | spec-secure-live-dashboards Django half | Marked deferred with 49.4 ruling reference | N/A |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md:308-317` — CAP-7 intent/success/verified; `:776-780` Residual six-cap list
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/convergence.md:38` — secure-dashboard pattern row; `:129-131` Atlas adoption note
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards/SPEC.md:190-216` — built-not-adopted grading + 49.4 decision block
- `src/shared/packages/django-atlas/src/django_atlas_portal/board.py:17-36` — fixture imports + `_MASTER_ROWS`
- `src/platform/tests/test_host_board_row_isolation.py:71-87` — two-user isolation oracle; `:213-229` — fixture-grade boundary test (Vizro absent by design)
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` — real Vizro board (package-local, zero steward imports; out of scope)

## Tasks & Acceptance

**Execution:**
- `spec-pyforge-unifying-strategy/SPEC.md` — rewrite CAP-7 intent/success/verified with 2026-09-10 fixture ruling; remove CAP-7 from Residual six-cap list — docs
- `convergence.md` — correct lines 38 and 129-131 to "adopted at fixture grade" — docs
- `spec-secure-live-dashboards/SPEC.md` — record Django half deferred under fixture ruling — docs
- `test_host_board_row_isolation.py` — update module/test docstrings so fixture-grade boundary is documented as deliverable, not absence-as-failure — docs-only comment

**Acceptance Criteria:**
- Given CAP-7 listed CAP-7 on the Residual as "fixture board; real Vizro asserted absent", when this story runs with the fixture ruling, then CAP-7's criterion names the JSON fixture as the host deliverable, the Residual no longer lists CAP-7 as unexercised, and `convergence.md` reads "adopted at fixture grade".
- And `spec-secure-live-dashboards` Django half (INSTALLED_APPS + audit/export) is marked deferred in the same act with the dated ruling reference.
- And `test_host_board_row_isolation.py` passes without behavioral change.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes platform-ci-test -- tests/test_host_board_row_isolation.py` — expected: all tests pass
- `pixi run --frozen -e pyforge-steward pyforge-steward-test -- -k dashboard` — expected: dashboard unit tests pass

## Spec Change Log

## Review Triage Log

## Design Notes

**Operator ruling (2026-09-10, Story 49.4):** Branch B — fixture is CAP-7's named deliverable.
Rationale: the host fixture at `/stations/atlas/board/` fully exercises per-tenant row isolation
via the secure-dashboard pattern with green two-user tests; mounting the 34-page Vizro board on
the host is a separate cross-cutting integration effort properly owned by atlas, not steward Epic 49.
