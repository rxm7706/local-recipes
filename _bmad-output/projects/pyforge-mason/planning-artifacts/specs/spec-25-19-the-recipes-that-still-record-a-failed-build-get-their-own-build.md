---
title: "25.19: The recipes that still record a failed build get their own build"
type: 'fix'
created: '2026-11-05'
status: 'backlog'
baseline_revision: '836a2ee286'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: recipe-build
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 33 recipes record a 2026-10 `cfe-local-build-status: failed` outside Story 25.17's list: 20 `opentelemetry-*` recipes
whose Story 25.10 run table says success, and 13 others, at least 10 of them single-maintainer. Track A never ran through the
tracked driver under CAP-35's terms, and no tracked-driver report for it exists. So CAP-35's `grep` clause is false on `main`
(EGM audit MAS-D-F4, MAS-D-F8).

**Approach:** Re-count Track A's scope live from the atlas, then run that scope and the 33 through `refresh-wave`. The build stamps
come from the CFE tools, never by hand.

Ledger key: `25-19-the-recipes-that-still-record-a-failed-build-get-their-own-build`. Type / Effort / Deps: fix / L / none.

### Living CAP citations

- **CAP-35** — the feedstock refresh campaign; this story closes its `grep` clause and dates its marker.

## Acceptance Criteria

- **AC1 — The scope.** The story records Track A's live scope from the named atlas query, with the as-of date and count, and how many of the 446 records dated 2026-08 fall inside it.
- **AC2 — The run.** `pixi run -e local-recipes refresh-wave <manifest> --apply --gates --build --report-dir <dir>` runs the scope, and `report.json` ends every recipe in the ruled outcome set.
- **AC3 — The clause.** `grep -l 'cfe-local-build-status: failed'` over the `recipe.yaml` of every recipe in scope matches none (grep exits 1).
- **AC4 — The marker.** CAP-35 takes its dated marker at the recorded atlas snapshot through a memlog line and a re-derive.
- **AC5 — The retro.** The story lands a `retro(cfe):` commit with a CFE `CHANGELOG.md` entry, and `pixi run --frozen -e pyforge-mason pyforge-mason-test` exits 0.

## Boundaries & Constraints

- Parked at `backlog` by the session owner on 2026-11-05: recipe-factory work, L effort.
- `flag-exempt: recipe-build`.

**Never:**
- Never write a `cfe-local-build-*` field by hand; never open a feedstock, staged-recipes or upstream PR.

</intent-contract>

## Binding

Parent: `spec-pyforge-mason` CAP-35

- Finding: MAS-D-F4, MAS-D-F8 in `research/egm-audit-2026-11-05.md`.
- Epic: Epic 25.

## Verification

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: exit 0.

## Spec Change Log

- 2026-11-05: minted at `backlog` by marshal Story 113.18.
