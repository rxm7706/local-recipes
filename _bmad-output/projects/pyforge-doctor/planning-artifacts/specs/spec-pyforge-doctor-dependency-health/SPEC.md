---
id: SPEC-pyforge-doctor-dependency-health
spec: pyforge-doctor-dependency-health
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/pyforge-doctor-dependency-health.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/pyforge-doctor-dependency-health.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# pyforge-doctor-dependency-health — retirement record

## Why it was contracted

A vision for Doctor as a dependency-health diagnostics engine: multi-axis health scoring
(A–F grade), obsolescence detection, version intelligence with safe-upgrade recommendations,
adoption tracking (PyPI/conda/GitHub signals), actionable remediation suggestions, and a
fleet-wide health dashboard.

## Why it ended

**Retired 2026-08-02, same day it was created**, as part of a dream-consolidation pass. The
dream was generated in a bulk commit (`dad47c408a`) later found to contain fabricated content
elsewhere in the same commit (a false sprint-status-ledger migration note, boilerplate
test-architecture docs invented for six stations). Unlike several sibling dreams from the
same commit (all found to be pure duplicates of already-shipped scope and retired outright),
this one earned a mixed verdict on real investigation against Doctor's actual, already-authored
PRD (`prd-pyforge-doctor-2026-07-25`):

- **Health Scoring, Fleet-wide Health Dashboard, Adoption Tracking, and safe-upgrade
  recommendation are real, unaddressed gaps** — the PRD's own Non-Goals section explicitly
  names the dashboard as "a possible v1.x addition, not a v1 commitment" and excludes a new
  scanning engine and a real dependency-graph resolver from v1 specifically, without rejecting
  them as ideas. These four items carry forward — see below.
- **The rest of the dream's content does not survive scrutiny.** Its precision claims —
  "validated against 1000+ real packages," "95%+ obsolescence catch rate," "80%+ operator
  acceptance," hourly/sub-second speed targets — cite no source, no prior measurement, and no
  method for arriving at them. They read as generated plausibility, not evidence, the same
  failure mode found in this dream's five sibling dreams from the same commit.
- **"Obsolescence Detection" and "Version Intelligence" as separate new capabilities are not
  new** — Doctor's real Epic 2 (Fleet Pulse) already wires cf_atlas's `release-cadence` and
  `feedstock-health` signals into an `abandonment` watch axis covering the same ground.

## What carries forward

The four real gaps are captured, in Doctor's own voice and grounded in Doctor's real
constraints (never a new scanning engine; never a full dependency-graph resolver), in
[`docs/dreams/pyforge-doctor.md`](pyforge-doctor.md)'s "The frontier" section, and decomposed
into a real Epic 4 in `epics.md` (CAP-5..CAP-8 in `spec-pyforge-doctor`, FR-10..FR-13 in the
PRD). This is not a rejection of the vision — it is the vision, rewritten to be true.

## Non-goals

- **Reviving this Dream as written.** Its real content already lives in `pyforge-doctor.md`
  and Doctor's real Epic 4; its invented precision numbers should not be revived alongside it.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design — the backlog item is Epic 4's stories, not this record.
- **Taking any number in this dream's original text as evidence of anything.** None were
  traced to a source; treat them the way this session's audit of `pyforge-marshal.md` records
  the lesson: "a premise handed to an agent is not evidence."

## Success signal

A reader arriving at this Dream learns in one page that it was half-real: which parts were
genuine gaps that now have a home in Doctor's real chain, and which parts were fabricated
precision with nothing behind them — without having to re-verify either from scratch.
