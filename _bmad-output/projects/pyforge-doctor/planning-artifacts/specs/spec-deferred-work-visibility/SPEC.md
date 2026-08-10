---
spec: deferred-work-visibility
status: ready
owner-dream: docs/dreams/deferred-work-visibility.md
surface: []          # Governs no files of its own, and that is honest rather than a frontier
                     # claim. CORRECTED 2026-08-10: the earlier note here claimed
                     # `.claude/skills/bmad-dev-auto/**` was governed by mason's
                     # spec-fleet-stewardship. It is NOT — verified two ways (zero hits for
                     # `bmad-dev-auto` in scripts/.spec-surface-baseline.json, and no Spec
                     # surface glob in any of the 8 projects matches
                     # `.claude/skills/bmad-dev-auto/step-04-review.md`). That path is
                     # ALLOWLISTED, not governed: spec_surface_allowlist.txt line 3,
                     # `.claude/**  # non-CFE agent config`. The detector half IS governed, by
                     # doctor's own station spec — and as of PR #394 it lives at
                     # `Source.DEFERRED_WORK` in `pyforge/doctor/sources/`, not the deleted
                     # shim. A glob matching nothing is silent by design.
companions: []
sources:
  - ../../../../../../docs/dreams/deferred-work-visibility.md
open_questions: []
---

## Why

`deferred_work_check` exists to guarantee one thing: that work a review pass chose to defer
reaches a **tracked, durable ledger** rather than dying in a gitignored Tier-3 file no clone
will ever have. It reports `OK: every Tier-3 deferral has a tracked twin` and exits 0.

It cannot see **470 of them**.

`_DW_RE` (`scripts/deferred_work_check.py:71`) harvests `DW-*` ids from the Tier-3 file and the
tracked ledger and compares those two **sets**. `bmad-dev-auto`'s mandated defer format
(`.claude/skills/bmad-dev-auto/step-04-review.md`) writes bare `- source_spec:` bullets with
**no id at all**, so anonymous entries land in neither set and are never compared — while the
identified ones all do have twins, so the comparison passes and the detector reports success.

Measured with the detector's own `_anonymous()` parser rather than a grep (a grep over
`source_spec:` bullets overcounts, because identified entries contain that field too):

| marshal | doctor | steward | atlas | warden | herald | mason | scribe | **total** |
|---|---|---|---|---|---|---|---|---|
| 202 | 72 | 56 | 54 | 41 | 26 | 13 | 6 | **470 anonymous / 33 identified** |

The finding came from marshal story 4-14's own review pass and was proven **by execution, not
inference**: `grep -c 'spec-4-14-…'` on Tier-3 returns 11, `grep -c '4-14'` on the tracked
ledger returns 0, and the detector still prints `OK`.

## Capabilities

- **CAP-1 — a deferral carries identity from birth.**
  - **intent:** A review pass that defers something produces an entry bearing an id under the
    **owning station's own convention**, never a fleet-wide imposition.
  - **success:** a newly damped story leaves a Tier-3 entry whose id matches that station's
    existing scheme — `DW-FU-<story>` for doctor/atlas/marshal/warden, `DW-<story>-<n>` for
    mason — and no `bmad-dev-auto` run creates a new anonymous entry.

- **CAP-2 — the detector sees what it claims to check.**
  - **intent:** Anonymous Tier-3 entries are reported rather than silently skipped, so "every
    Tier-3 deferral has a tracked twin" means *every* deferral.
  - **success:** deleting an id heading from a Tier-3 entry **reds** the detector — demonstrated
    by mutation, the same proof standard `_anonymous()`'s own docstring already records for the
    tracked side.

- **CAP-3 — the existing 470 do not red every landing pass on day one.**
  - **intent:** The backlog that accumulated while the detector was blind is baselined, and the
    gate bites on what is **new**.
  - **success:** after the detector learns the anonymous shape, a landing pass is green on an
    unchanged repo, and adding a single anonymous entry reds it.

## Constraints

- **Both sides move, and the order is load-bearing.** Emitter first (`bmad-dev-auto` writes
  ids — stops producing invisible entries, reds nothing), detector second **with a baseline**.
  Detector-first turns one green check into 470 findings overnight; every landing pass fails
  and the realistic outcome is the finding gets suppressed — strictly worse than today, because
  then it is suppressed *and* invisible. Emitter-only stops the bleeding but leaves all 470
  permanently unseeable.
- **Half the machinery already exists and is already hardened — do not rewrite it.**
  `_anonymous()` parses exactly this shape, and its docstring records this same vacuity class
  being caught once before and fixed by mutation testing. It is called on the **tracked** ledger
  only, never on Tier-3. The gap is one call plus a finding kind.
- **Follow the in-house grandfathering precedent.** `spec-pyforge-warden` already ships
  baseline-and-grandfathering for exactly this shape: a real gate that would otherwise red on a
  large pre-existing backlog. Do not invent a second mechanism.
- **The detector half is written against `sources/`, and the shim is already gone.**
  6-9 **landed** on 2026-08-10 (PR #394): `scripts/deferred_work_check.py` is deleted and the
  check is `Source.DEFERRED_WORK`, registered in `pyforge/doctor/sources/__init__.py`. What was
  an ordering constraint is now settled history — there is no shim left to write against by
  mistake.
- **Station id conventions are deliberate and survive.** doctor/atlas/marshal/warden use
  `DW-FU-<story>`; mason uses `DW-<story>-<n>`. Whatever ships respects each station's own
  precedent rather than normalising them.

## Non-goals

- **Not a rewrite of the deferral format.** The existing entries carry real content; only
  identity is missing.
- **Not a change to what gets deferred.** Review passes decide that. This is about durability
  of the record, not the decision.
- **Not a fleet-wide id convention.** The per-station difference is deliberate.
- **Not coupled to landing 6-9** — moot as of 2026-08-10: 6-9 has landed, so the ordering
  constraint is discharged rather than merely uncoupled.
- **Not a triage of the existing 470.** Whether they are all worth keeping is an open question
  above, and possibly its own effort.

## Resolved Questions

All four were answered 2026-08-10, after 6-9 landed removed the only recorded blocker.

- **Q1 — who owns which half? RESOLVED: Doctor owns both; the effort is not split.** Three
  grounds. The detector half is Doctor's beyond argument now that 6-9 has landed. The emitter
  half is not a change to loop *orchestration* (which would be Marshal's) but a one-line
  template change making `bmad-dev-auto` **comply** with a contract Doctor defines and
  validates — the station that says what a valid deferral looks like should own making the
  emitter produce one. And per the frontmatter correction, the emitter path is allowlisted, so
  a Doctor-owned change invades no other station's surface. *Rejected: splitting a 3-CAP effort
  across two stations for a single template edit — it buys a seam boundary and pays a
  coordination cost on every story.*
- **Q2 — are all 470 worth keeping? RESOLVED: grandfather all 470 wholesale at a dated
  cut-off; do not triage here.** Triage is already a Non-goal, and the warden precedent this
  Spec is told to follow does exactly this. Triage stays worth doing, named as its own
  follow-on rather than smuggled into a gate story — it is judgement work per entry and would
  block a mechanical fix behind an open-ended review.
- **Q3 — emitter or promotion mints the id? RESOLVED: the emitter, at defer time.** CAP-1
  already says "carries identity from birth", and the alternative is self-defeating: an entry
  that reaches promotion without an id is *already invisible* to the thing that would promote
  it. Marshal Story 4.13 promotes **by id** and so inherits this exact blind spot, which means
  routing minting through promotion would rebuild the defect one layer up.
- **Q4 — same severity on the tracked side? RESOLVED: yes.** One invariant, two sides.
  Different severities would let one side be silenced independently of the other — and drift
  between the two sides is the shape of the original defect, not a new risk.

## Success signal

A story defers something, and the entry it leaves behind is visible to the detector that exists
to protect it. Deleting that entry's id reds a landing pass. The count of invisible deferrals is
zero and stays zero — not because someone swept the backlog, but because nothing new can be
created without an identity.
