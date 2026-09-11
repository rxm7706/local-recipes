---
title: 'README.md, CLAUDE.md, and AGENTS.md point cleanly into the reorganized structure'
type: 'fix'
created: '2026-09-11'
status: 'backlog'
baseline_revision: 'a7752e7f91015b81d79a979bfca61a0dc8c8c8bb'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Depends on Stories 22.4 and 22.5. Once the Diátaxis-adapted structure exists,
`README.md`, `CLAUDE.md`, and `AGENTS.md` (the repo's three highest-visibility entry-point docs)
still either duplicate content that now lives in the new structure, or point at the old,
pre-reorganization locations Story 22.5 moved content out of.

**Approach:** Update every link and cross-reference in the three entry-point docs that targets
content Stories 22.4/22.5 relocated, and remove any content now duplicated in the new
structure in favor of a pointer. `CLAUDE.md` and `AGENTS.md` stay where they are (tool entry
points, not general docs, per the owning Dream's own framing) — this story corrects their
pointers, it does not relocate them into the new quadrant structure.

## Boundaries & Constraints

**Always:**
- Every internal link into the reorganized structure must resolve — verify each one, do not
  assume Story 22.4/22.5's relocations match what the old links expected.
- Where a fact now lives in the new structure, the entry-point doc gets a pointer to it, not a
  second copy — matching Story 22.2's same discipline (the duplicated priority list) applied to
  the new structure.

**Never:**
- Do not relocate `CLAUDE.md` or `AGENTS.md` themselves into the Diátaxis structure — they
  remain tool entry points at the repo root.
- Do not touch content in `README.md`/`CLAUDE.md`/`AGENTS.md` that is unrelated to Stories
  22.4/22.5's relocations (e.g. Story 22.1/22.2's own already-corrected content is out of this
  story's scope, already done).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Link into a relocated file | e.g. `README.md` linking to a `docs/reference/*.md` file Story 22.4 moved | Link updated to the new path | n/a |
| Content now duplicated in the new structure | e.g. onboarding steps Story 22.5 relocated but README still carries the full text | README's copy replaced with a pointer to the new home | n/a |
| Link that already resolves correctly | A link untouched by Stories 22.4/22.5 | Left unchanged — not this story's scope | n/a |

</intent-contract>

## Code Map

- `README.md`, `CLAUDE.md`, `AGENTS.md` — every link/cross-reference into content Stories
  22.4/22.5 relocated.
- Story 22.4's map document and Story 22.5's relocated content — the targets these links must
  resolve to.

## Tasks & Acceptance

**Execution:**
- `fix` — audit every link in `README.md`/`CLAUDE.md`/`AGENTS.md` against Stories 22.4/22.5's
  actual relocations; update any that now point at a moved or stale location.
- `fix` — replace any content now duplicated in the new structure with a pointer.

**Acceptance Criteria:**
- Given the reorganized structure exists (Stories 22.4-22.5), when the three entry-point docs'
  pointers are corrected, then no internal link into the reorganized structure is broken.
- Given a fact now lives in the new structure, when the entry-point docs are checked, then no
  such fact is also duplicated verbatim in `README.md`/`CLAUDE.md`/`AGENTS.md` without one side
  pointing to the other.

## Verification

**Commands:**
- `pixi run --frozen -e local-recipes dreams-hygiene-check` — expected: no new finding
  introduced.
- Manual verification: every internal markdown link in `README.md`/`CLAUDE.md`/`AGENTS.md`
  resolves to a real path (no 404s against the repo tree).
