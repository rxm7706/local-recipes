---
title: 'Dependency-derived dispatch ordering (Story 28.12, Epic 28)'
type: 'feature'
created: '2026-08-31'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** `factory drain` (no `--stories`) walks `sprint-status-ledger.yaml` in raw
ledger order, which has no relationship to each story's declared `Deps:` graph — including
cross-epic edges. Operators hand-derive topological order or risk dispatching a story
ahead of an unmet dependency.

**Approach:** When `factory drain` runs without a caller-supplied `--stories` override,
derive dispatch order from each backlog story's declared `Deps:` (topological sort over the
tracked dependency graph, honoring cross-epic edges). Among stories with no unmet dependency
either way, fall back to ledger order (deterministic, no invented preference). `--stories`
remains an explicit caller override unchanged.

## Acceptance Criteria

- Given a station backlog whose `Deps:` graph spans more than one epic, when `factory drain`
  runs with no `--stories` override, then the computed dispatch order never violates a
  declared `Deps:` edge — proven by a test with a cross-epic dependency (e.g. atlas
  23.9 → 22.1).
- Given stories with no unmet dependency either way, when order is computed, then ledger
  order is the tie-break (deterministic, no invented preference).
- Given a caller-supplied `--stories` list, when drain or dispatch runs, then behavior is
  byte-identical to today — explicit override unchanged.
- Given a station with no `--stories` override, when order is computed, then the result is
  always a valid total order over eligible backlog stories (no crash on empty or single-story
  backlogs).

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-12-dependency-derived-dispatch-ordering`.

**Block If:** A change would silently skip `--stories`, invent dependency edges not declared
in epics/spec frontmatter, or reorder in-flight campaigns retroactively.

**Never:** A second dispatch-order mechanism. Replacing `fleet-drain-queue.yaml`
`order_overrides` — that file remains the operator's explicit override surface.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py` (ordered backlog reader; topological sort hook)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (`factory drain` / `--stories` path)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(cross-epic topo order, ledger tie-break, `--stories` unchanged, empty/single backlog).
Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.12 and spec-marshal-token-economy CAP-14. Deps: — (depends on
existing `factory drain`/`dispatch` machinery only). Motivating incident:
`docs/dreams/marshal-dependency-aware-dispatch.md` and sprint-change-proposal-2026-08-31.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-31: drafted from marshal-dependency-aware-dispatch fold-in (CAP-14; bmad-correct-course sprint-change-proposal-2026-08-31)
