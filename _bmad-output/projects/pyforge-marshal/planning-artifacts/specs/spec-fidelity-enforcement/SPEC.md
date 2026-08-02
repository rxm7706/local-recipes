---
spec: fidelity-enforcement
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/fidelity-enforcement.md
surface: []          # archived — no live surface of its own; see § What carries forward
companions:
  - fidelity-stack.md
  - audit-triad.md
  - migration-and-invariants.md
sources:
  - ../../../../../../docs/dreams/fidelity-enforcement.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included. It states what was contracted, why it
> ended, and what survives — not a plan for work that will not happen. **Companions kept
> live** (not archived) — `fidelity-stack.md`, `audit-triad.md`, and
> `migration-and-invariants.md` remain the real reference detail for the still-open items
> below; a future Spec picking this work back up should read them, not rederive them.

# fidelity-enforcement — retirement record

## Why it was contracted

A contract nothing can fail against is a plan, not a gate. `EXEMPLAR-STANDARD.md` states ten
conformance requirements; `dream_chain_check` enforced only INV-0..3. Nine capabilities
(CAP-1..9) closed that gap: detector CI wiring, a shipped-story-needs-a-tracked-spec check,
automatic Tier-2 promotion, a gate-to-Success-signal binding, a Spec↔chain reverse gate, an
actor-attributed event record, ungated-boundary self-declaration, a fixed-point-per-
reconciliation record, and "install the judge" (Marshal cannot grade its own conformance).

## Why it ended

**Retired 2026-08-02, as part of a dream-consolidation pass.** This is the most mixed
disposition of the five Marshal satellites retired this session — not everything landed the
same way, and this record says so plainly rather than smoothing it over:

- **CAP-1** (detector CI trigger) — **shipped**, verified on disk 2026-08-01
  (`.github/workflows/detectors.yml` + `scripts/detectors.py`). Repo-level, not
  marshal-CLI-package code; cited as evidence, correctly given no FR.
- **CAP-3** (automatic Tier-2 promotion) — **convergent**, no gap: `spec-pyforge-marshal`'s
  already-specified FR-30/Story 4.1 already states this in full (re-verified by re-reading
  FR-30's exact consequences during the 2026-08-01 decomposition).
- **CAP-4** (gate evaluation binds to the tracked spec's Success signal) — **new FR-64**, the
  one genuinely new marshal-CLI capability from this Dream, squarely Epic 2's charter.
- **CAP-6** (the actor-attributed event record) — **Scribe's**, not Marshal's. Explicitly out
  of scope for `spec-pyforge-marshal`'s PRD per the 2026-08-01 operator-scoping decision; a
  named cross-project follow-up for `pyforge-scribe`'s own chain, not touched here.
- **CAP-9** (install the judge) — **Doctor's**, not Marshal's, same treatment as CAP-6 — a
  named cross-project follow-up for `pyforge-doctor`'s own chain.
- **CAP-2, CAP-5, CAP-7, CAP-8** — **real, unbuilt, repo-level detector/BMAD-skill tooling**
  (`dream_chain_check.py` extensions, `bmad-drift-check`'s reconciler), explicitly not
  marshal-CLI-package code, so correctly given no marshal FR — **but also not yet built
  anywhere else.** This is not a clean "absorbed," it is an honest "excluded from this PRD,
  still open." See § What carries forward.

## What carries forward

CAP-1/3/4/6/9 all have a real, current home (shipped code, an existing FR, or another
station's own chain) — nothing to track for them here. **CAP-2, CAP-5, CAP-7, and CAP-8 do
not** — they are real, specified, unbuilt repo-level detector work with no owning Spec after
this retirement. The three companions (`fidelity-stack.md`, `audit-triad.md`,
`migration-and-invariants.md`) are kept live specifically so this work is not lost: a future
Spec — repo-level, not station-scoped, likely authored directly against
`scripts/dream_chain_check.py` / `scripts/bmad_drift_check.py` — should pick these four
capabilities up from here rather than rediscovering them.

## Non-goals

- **Reviving this Dream as written.** CAP-1/3/4/6/9's intent already lives elsewhere; only
  CAP-2/5/7/8 are genuinely open, and reviving the whole Dream would re-litigate the five
  that are settled.
- **Treating this record as a backlog item in itself.** Archived Dreams are excluded from the
  Backlog board by design — but CAP-2/5/7/8's underlying work is a real, undismissed gap; a
  future repo-level Spec is the correct vehicle for it, not this record.
- **Assuming Marshal will build CAP-2/5/7/8.** This retirement explicitly does not assign
  them anywhere — they were excluded from `spec-pyforge-marshal`'s PRD because they are not
  marshal-CLI-package code, the same reason CAP-1 got no FR despite being shipped.

## Success signal

A reader arriving at this Dream learns in one page which five capabilities are settled and
where, and which four are genuinely still open with their reference detail preserved —
without mistaking "archived" for "everything here is done."
