---
id: SPEC-bmad-loop-forward-dependency-blindness
spec: bmad-loop-forward-dependency-blindness
status: shipped
owner-dream: docs/dreams/bmad-loop-forward-dependency-blindness.md
surface:
  - scripts/forward_dependency_check.py
sources:
  - ../../../../../docs/dreams/bmad-loop-forward-dependency-blindness.md
open_questions: []
---

> **RETROACTIVE, written 2026-08-08.** This Dream shipped (PR #238, merged 2026-08-03) before
> this Spec was written — a real process gap against this repo's Dream-first mandate (a fast,
> mechanical fix + detector went straight from Dream to code). Written after the fact from the
> Dream's own "What is real" section and the actual shipped detector, not invented.
>
> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> was built. Source documents listed in frontmatter are for traceability only.

# bmad-loop's forward-dependency blindness, closed

## Why

`bmad-loop`'s picker (`next_actionable` in `bmad_loop/sprintstatus.py`) is a strict file-order
scan within the current epic — it has no `depends_on` concept, confirmed directly against the
installed library source. A story whose own `epics.md` documents a dependency on a *later*
epic's story is dispatched anyway the moment its own epic's earlier stories clear, burning a
real dev attempt (and up to `max_review_cycles` review passes) on work that structurally cannot
complete. Found 2026-08-03 setting Marshal up to run its own backlog unattended — Marshal's own
`epics.md` had already documented three such forward dependencies (2.3→S-3.2, 2.7→S-4.1,
8.5→S-10.2) and the engine could not see any of them.

## Capabilities

- **CAP-1 — every station's structured epics doc is swept for forward-epic `**Deps:**`
  references.** *Intent:* find every story whose documented dependency lives in a later epic
  than the story itself. *Success:* a full sweep of all 8 stations' epics docs, confirming
  Marshal's three forward dependencies are the only real ones across the fleet, and that Atlas
  and Mason's presenton-pixi-image satellite (both structured enough to carry a mechanical Deps
  field) are otherwise clean.
- **CAP-2 — a found forward-dependent story is set to a non-actionable status.** *Intent:*
  make the engine structurally unable to dispatch the story early. *Success:* status `blocked`
  in both the loop-home's live Tier-3 feed and the tracked `sprint-status-ledger.yaml` twin;
  `ACTIONABLE_STATUSES = {"backlog", "ready-for-dev"}` naturally excludes it since
  `bmad_loop.sprintstatus.load()` does not validate `status` against its own declared
  `STORY_STATUSES` enum (the same mechanism the pre-existing `optional` retrospective status
  already relies on) — confirmed directly: `next_actionable(epic=2)` now correctly returns 2.4,
  skipping both Epic-2 findings.
- **CAP-3 — a permanent detector prevents recurrence.** *Intent:* a new story added later with
  an unmarked forward dependency is caught in CI, not discovered by a run burning compute on it.
  *Success:* `scripts/forward_dependency_check.py`, self-registered via `scripts/detectors.py`,
  scans every station's structured epics doc for forward-epic `**Deps:**`, cross-checks each
  against the tracked ledger, and fails if a forward-dependent story is still
  `backlog`/`ready-for-dev`.
- **CAP-4 — an unparseable epics format is reported honestly, never silently passed.**
  *Intent:* this repo's fidelity-enforcement doctrine (never claim green you didn't measure)
  applies to the detector itself. *Success:* stations whose `epics.md` uses an older narrative
  format with no structured `**Deps:**` field (confirmed: `pyforge-warden`) are reported as
  **not determinable from this format**, not as clean.

## Constraints

- **Always:** flipping a `blocked` story back to `backlog` once its real dependency lands is a
  one-line edit, not a rediscovery — the PROJECT NOTES comment at the top of each affected
  `sprint-status.yaml` names exactly which dependency to watch for.
- **Never:** the detector never infers a dependency that isn't explicitly written in a
  `**Deps:**` field — it does not attempt semantic inference across epics.

## Non-goals

- **A general-purpose dependency graph / scheduler.** This closes the specific blindness
  (forward-epic deps invisible to a strict file-order picker), not a DAG-based execution model.
- **Retrofitting `**Deps:**` onto stations using the narrative epics format.** CAP-4 reports
  those honestly as undeterminable; migrating them to a structured format is separate,
  unscheduled work.

## Delivery Record

Shipped via PR #238 (`dream+detector: bmad-loop can't see a story's forward dependency`), merge
commit `a825ac0749`, 2026-08-03T08:01:58Z. Stories 2-3 and 2-7 (the mechanical fix) shipped
earlier the same session in PR #237; 8-5 and the permanent detector landed in #238.
https://github.com/rxm7706/local-recipes/pull/238

## Success signal

`next_actionable(epic=2)` returns 2.4, not 2.3 or 2.7, until their real dependencies land; the
detector fails CI on any newly-added forward dependency left unmarked; a re-run of the
cross-station sweep finds no new forward dependencies undetected.
