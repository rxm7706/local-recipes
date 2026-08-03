---
title: bmad-loop can't see a story's own documented dependency
type: dream
owner: marshal
status: realized
---

# bmad-loop can't see a story's own documented dependency

## The Dream

`bmad-loop`'s picker (`next_actionable` in `bmad_loop/sprintstatus.py`, called
from `engine.py`'s `_pick_next`) is a strict file-order scan within the current
epic. It has no `depends_on` concept at all — confirmed directly against the
installed library source. Every station's `epics.md` can document a real
per-story dependency via a `**Deps:** S-X.Y` field, but the engine only ever
reads a story's status in `sprint-status.yaml` (`backlog` / `ready-for-dev` /
`in-progress` / `review` / `done`). When a story's own documented dependency
lives in a *later* epic than the story itself, the engine cannot tell — it
will dispatch that story the moment its own epic's earlier stories clear, and
burn a real dev attempt (and up to `max_review_cycles` review passes) on work
that structurally cannot complete yet.

Found 2026-08-03 while setting Marshal up to run its backlog unattended.
Marshal's own `epics.md` had *already* documented the dependency for two
stories (2.3 → S-3.2, one with a full explanatory paragraph; 2.7 → S-4.1) —
the information existed, it just never reached the one file the engine
actually reads. A third forward-dependency (8.5 → S-10.2) turned up in the
absorbed genesis-installer epics (7-12) on a full sweep of every story's
`**Deps:**` field.

This Dream exists so the gap gets closed **once**, for every station, and
stays closed: a mechanical fix per station is a one-time patch; a permanent
detector is what stops it recurring the next time someone adds a story whose
dependency happens to live in a later epic.

## What it looks like when real

- Every station's `epics.md`-family document has been swept for forward-epic
  `**Deps:**` references (a story naming a dependency in a later epic than its
  own).
- Every finding has its story's status set to a non-actionable, non-standard
  value (`blocked`) in both the loop-home's live Tier-3 feed and the tracked
  `sprint-status-ledger.yaml` twin — confirmed safe: `bmad_loop.sprintstatus
  .load()` does not validate `status` against its own declared
  `STORY_STATUSES` enum, so `ACTIONABLE_STATUSES = {"backlog", "ready-for-dev"}`
  naturally excludes it. Same mechanism the pre-existing `optional`
  retrospective status already relies on.
- A permanent detector (`scripts/*_check.py`, self-registered via the existing
  `scripts/detectors.py` registry) scans every station's structured epics doc
  for forward-epic `**Deps:**`, cross-checks each against the tracked ledger,
  and fails if a forward-dependent story is still `backlog`/`ready-for-dev` —
  so adding a new story with a forward dependency later, and forgetting to
  mark it, is caught in CI rather than discovered by a run burning compute on
  it.
- Stations whose `epics.md` uses an older narrative format with no structured
  `**Deps:**` field (confirmed: `pyforge-warden`) are reported by the detector
  as **not determinable from this format**, never silently passed as clean —
  this repo's own fidelity-enforcement doctrine (never claim green you didn't
  measure) applies here exactly as it does everywhere else.
- Flipping a `blocked` story back to `backlog` once its real dependency lands
  is a one-line edit, not a rediscovery — the PROJECT NOTES comment at the top
  of each affected `sprint-status.yaml` names exactly which dependency to
  watch for.

## What is real

- Marshal fixed: `2-3-frozen-surface-scope-check-narrowing-only` (deps
  `S-3.2`), `2-7-a-gate-binds-to-the-specs-success-signal` (deps `S-4.1`), and
  `8-5-marker-deletion-as-a-sanctioned-opt-out` (deps `S-10.2`, in the absorbed
  genesis-installer epics 7-12) — all three set `blocked` in the loop-home's
  live feed and promoted to the tracked ledger. Verified directly against the
  library: `next_actionable(epic=2)` now correctly returns 2.4, skipping both
  Epic-2 findings. `2-3`/`2-7` shipped in PR #237; `8-5` applied the same
  session, not yet in a PR at the time this Dream was captured.
- A full sweep of marshal's own two epics files (`epics.md`,
  `epics-genesis-installer.md`) confirmed these are the *only* three forward
  dependencies across all 12 epics / 86 stories — every other `**Deps:**`
  reference stays within-epic-or-earlier.
- **Cross-station audit complete: zero additional forward dependencies.** A
  research pass read every other station's epics doc(s) directly. Two are
  structured enough to carry a mechanical Deps field (atlas: `**Depends on:**`
  under an alias-first heading `### Story A1 (2.1):`, not marshal's plain
  `### Story 2.1:` shape; mason's `epics-presenton-pixi-image.md` satellite:
  marshal's exact shape) and both are clean. The other five (doctor, herald,
  mason's own main `epics.md`, scribe, steward, warden) use a narrative format
  with marshal-shaped `### Story E.N:` headings but **no Deps field of any
  kind** — several of those documents even self-validate in their own closing
  prose that no forward dependency exists ("no story depends on a future
  story within its own epic", scribe; "no forward dependencies", steward).
  Confirmed unmeasurable mechanically either way — marshal was the only
  station actually carrying the bug.
- **The permanent detector is built, tested, and passing**:
  `scripts/forward_dependency_check.py` (pixi task
  `forward-dependency-check`), self-registered via `scripts/detectors.py`.
  Imports `ACTIONABLE_STATUSES` from the installed `bmad_loop.sprintstatus`
  module rather than restating it. Extracts each story's own block (heading to
  next heading) and searches within it for the Deps field, rather than
  anchoring to a line start — the field routinely shares a line with
  `**Type:**`/`**Effort:**`. A station only counts as "measured" if at least
  one real Deps field was found anywhere in its epics doc(s); a station with
  headings but zero Deps fields (doctor/scribe/steward/warden/mason's main
  doc) reports as unmeasured rather than a false "0 findings" — caught as a
  real bug in the detector's own first draft before this Dream closed. Current
  live output: 2 stations measured (marshal, mason) clean, 6 unmeasured
  (atlas, doctor, herald, scribe, steward, warden), 0 findings, exit 0.
- Two unrelated findings surfaced by the audit, out of this Dream's scope,
  left for a separate decision: herald's live `planning-artifacts/epics.md`
  describes a different, undocumented "deck bridge" effort than what the
  tracked ledger actually drives — reading `epics.md` doesn't tell you what
  herald is building. Mason's `epics-presenton-pixi-image.md` satellite and
  doctor's newly-added Epic 4 are both absent from their tracked
  sprint-status ledgers (currency gaps, not correctness bugs).

## Constraints

- Never touch `.memlog.md` history or `archive/` content.
- The `blocked` status value is deliberately outside `STORY_STATUSES` — do not
  add it to that enum upstream in `bmad_loop` even if a PR opportunity arises;
  this repo does not vendor or patch `bmad-loop` (a declared, pinned runtime
  dependency), and inventing a status the engine doesn't formally recognize is
  the *workaround*, not a request to change the library's contract.
- A station whose epics format can't be mechanically parsed must be reported
  as unmeasured, never silently treated as "0 findings = clean."

## Non-goals

- Not a request to add `depends_on` to `bmad-loop` itself — that fix belongs
  upstream, and this repo's stance elsewhere (`scripts/story_status_check.py`'s
  own docstring) is explicit that known-upstream defects get *contained*
  locally, not patched in a vendored fork.
- Not re-litigating whether forward dependencies should exist in the epics
  structure at all — some are legitimate (a fold/aggregation step genuinely
  needs to land before a consumer can be built); the fix is making the engine
  aware of the ones that do, not restructuring epics to avoid them.

## Realization log

- **2026-08-03** — Captured after finding and fixing 3 instances in marshal
  (2.3, 2.7, 8.5) while preparing to run marshal's backlog unattended. Cross-
  station audit and the permanent detector are in progress in the same
  session; user asked explicitly for this to be recorded as a Dream and fixed
  across every station, not just marshal.
- **2026-08-03** — Realized. Cross-station audit found zero additional forward
  dependencies (marshal was the only affected station); the permanent
  detector (`scripts/forward_dependency_check.py`) is built, registered, and
  passing (2 stations measured clean, 6 correctly reported unmeasured, 0
  findings). The detector itself caught a real bug in its own first draft
  before landing — a station with headings but no Deps field would have
  silently counted as "measured, 0 findings" instead of unmeasured, the exact
  false-green class this Dream exists to prevent.
- **2026-08-03** — First real unblock: S-3.2 landed, so `2-3` was flipped
  back to `backlog` (its own dep is now satisfied) — exactly the mechanism
  this Dream designed for. Noted a known detector limitation surfaced by
  this: `forward_dependency_check.py` flags `2-3` as a finding again
  immediately after the correct unblock, because it only checks "is this
  story's status non-actionable," not "has its declared dependency actually
  landed." Not a bug in the unblock — a real enhancement opportunity for the
  detector (check the dependency story's own status, not just this story's),
  not urgent enough to build today. Left as a known, understood false
  positive rather than silenced.
