---
spec: deferred-work-visibility
status: in-progress   # CAP-1..7 shipped (Epic 7 + Epic 8, 2026-08-15); CAP-8..10 (Epic 9) queued, not dispatched
owner-dream: docs/dreams/deferred-work-visibility.md
covers-dreams:
  - docs/dreams/deferred-work-audit-completeness.md   # folded in 2026-08-15 as CAP-4..9 (see § Why below); satisfies INV-1 for this Dream
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
                     # shim. A glob matching nothing is silent by design. EXTENDED 2026-08-15
                     # (CAP-4..10): still empty — the new capabilities also land in
                     # `pyforge/doctor/sources/`, already governed by doctor's own station
                     # spec, plus `scripts/.deferred-work-baseline.json` (same governance as
                     # CAP-3's baseline) and `fleet_picture.py`'s ATTENTION block (CAP-10).
companions: []
sources:
  - ../../../../../../docs/dreams/deferred-work-visibility.md
  - ../../../../../../docs/dreams/deferred-work-audit-completeness.md
open_questions:
  - "Does adding CAP-4..10 to an already-ready Spec need a fresh self-validate pass + a
     return to draft before bmad-create-epics-and-stories, or can Epic 8+ decompose directly
     since CAP-1..3 are unaffected and already shipped? Operator call."
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

**Extension, 2026-08-15 — the backlog Q2 grandfathered still needs clearing, and it isn't
alone.** CAP-1..3 shipped (Epic 7, PRs behind stories 7-1..7-4) — the emitter mints ids at
defer time, the detector sees anonymous entries, and the pre-existing backlog is baselined so
it doesn't red every landing pass. The leak is stopped. But Q2's own resolution named triaging
that backlog "its own follow-on" and never built it — so it still sits grandfathered, at the
same loss risk (gitignored Tier-3, dies on worktree teardown) it always was, just silenced
rather than solved. A 2026-08-15 by-hand fleet audit — triggered by a user challenge to a
"0 findings" reading for pyforge-warden that turned out to be a *different*, already-resolved
station — found this the hard way: promoted 144 `tier3-only-deferral` findings plus ~72 more
previously-invisible ones by hand across 6 of 8 projects, shipped two real bugs in the
process (content duplication from an "orphan bullet" heuristic that didn't check header
ownership; a 10x overcount from the same heuristic misreading a multi-bullet-per-header shape
as orphans), and still has **72 entries left** (`tier3-entry-unidentified`, 2026-08-15: marshal
30, steward 38, mason 2, herald 2). That audit also surfaced a structurally identical gap one
level up: `pyforge-warden`'s own `bmad-output-hygiene` sweep (dead test scaffolding, hollow
`sprint-status.yaml`, orphan files, README placeholders, stale Dream statuses) was run once, by
hand, for one station, and never generalized to the other seven. Both are the same shape — a
class of finding across all 8 stations, fixed once by hand, never systematized — and both
converge on this Spec rather than spawning parallel ones, per explicit operator direction to
keep one big process instead of several small ones.

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

- **CAP-4 — a pre-CAP-1 anonymous entry is correctly parsed, whatever legacy shape it used.**
  - **intent:** CAP-1 only stops *new* anonymous entries. Legacy ones use at least two distinct
    pre-fix shapes found live — a headerless flat `- source_spec:`/`summary:`/`evidence:` bullet
    under a `bmad-dev-auto` step-04 marker comment (58 real findings in atlas alone, dating to
    July), and, separately in `pyforge-warden`'s Tier-3 file, an even older `## Deferred from:
    code review of <spec> (<date>)` section-header convention predating any `DW-` id scheme.
  - **success:** a parser fixture built from real excerpts of both legacy shapes, plus CAP-1's
    current shape and a headed-but-multi-bullet shape (`## DW-<id>`/`### DW-<id>` with more than
    one `- source_spec:` bullet stacked under it), classifies every entry correctly — the exact
    two shapes that broke two different hand-rolled attempts on 2026-08-15 (a false-orphan
    duplication of already-headed content; a 10x overcount treating a header's second bullet as
    a new orphan).

- **CAP-5 — a legacy entry mints a collision-free id in CAP-1's own per-station convention.**
  - **intent:** Promoting old backlog entries must not invent a second id scheme alongside the
    one CAP-1 just standardized going forward (`DW-FU-<story>` for doctor/atlas/marshal/warden,
    `DW-<story>-<n>` for mason).
  - **success:** minting against a tracked ledger that already has entries for a story picks the
    next free numeric suffix for *that* story, never restarting at 1 — verified against three
    real 2026-08-15 near-misses (`DW-10-5-1`, `DW-10-6-1`, `DW-13-3-1` each attempted a duplicate
    mint before being caught and renumbered by hand).

- **CAP-6 — a `--fix` mode promotes every genuine legacy-anonymous entry safely.**
  - **intent:** Mirrors `scripts/spec_surface_check.py`'s `--write-baseline` pattern: classify
    via CAP-4, mint via CAP-5, append to the tracked ledger with `status: open` and a `promoted:`
    provenance line, and refuse to write if the result would be a duplicate id or duplicate
    summary-text — replacing the error-prone by-hand promotion this repo has now done twice
    (2026-07-29 for warden, 2026-08-15 fleet-wide) with a tool that cannot ship the two bugs that
    by-hand attempt actually shipped.
  - **success:** running `--fix` against the live 72-entry backlog (marshal 30, steward 38,
    mason 2, herald 2 as of 2026-08-15) fully clears `tier3-entry-unidentified` for those with
    zero content duplication, and a manufactured collision fixture aborts the write with no
    partial output (mutation-tested).

- **CAP-7 — the grandfather baseline stays in lockstep with `--fix`.**
  - **intent:** After a `--fix` run, `scripts/.deferred-work-baseline.json` (CAP-3's own
    mechanism) is re-stamped so newly-promoted entries are never re-flagged — the same discipline
    `spec_surface_check.py --write-baseline` already keeps for its own baseline.
  - **success:** running `--fix` twice in a row is a no-op the second time — 0 new writes, 0
    findings delta.

- **CAP-8 — a fleet-wide hygiene sweep, generalizing the warden-only precedent.**
  - **intent:** The 2026-08-14/15 `bmad-output-hygiene` pass (dead test scaffolding archival,
    hollow `sprint-status.yaml` detection, orphan-file detection, README-placeholder detection,
    stale Dream-status detection) ran once, by hand, for `pyforge-warden` only. The same finding
    classes could equally exist on any of the other 7 stations and nothing looks for them there.
  - **success:** running the sweep against all 8 projects reproduces warden's own 5 finding
    classes as a fixture (zero false positives against warden itself, already clean) and
    surfaces at least one true positive on a station never audited this way.

- **CAP-9 — hygiene findings are reported, never auto-applied.**
  - **intent:** A dead-scaffolding or orphan-file finding names the path and the evidence for
    why it is judged dead/orphaned; the archive/delete action stays a separate, human-reviewed
    step — matches this repo's own archive-don't-delete convention and the review discipline
    CAP-6 keeps for deferred-work promotion.
  - **success:** the sweep's own invocation never mutates a file; every finding it reports is
    actioned by a distinct, reviewable follow-up commit.

- **CAP-10 — loop-home branch staleness is visible without a human asking.**
  - **intent:** `fleet_picture.py`'s ATTENTION block — already the ambient, always-run home for
    cross-cutting fleet signals (it grew a baseline-drift line this same 2026-08-15 session) —
    gains a line naming any `loop/pyforge-<slug>` branch N+ commits behind `origin/main`, the
    exact gap a 2026-08-15 session found by accident (all 4 active stations' branches 55-60
    commits stale, which is how 3 separate stations independently rediscovered the same
    already-fixed spec-surface bug before their branches caught up).
  - **success:** fleet-picture's ATTENTION block names a synthetically-staled loop-home branch
    without a separate manual check being run.
- **CAP-11** *(added 2026-08-28 — motivated by a live fleet-wide hygiene sweep re-running
  `deferred-work-check` and finding 117 standing `tier3-only-deferral`/`tier3-entry-unidentified`
  findings across doctor/marshal/mason/scribe/steward/atlas)*
  - **intent:** CAP-4..7's id/position-based coverage check has a real gap: a Tier-3 entry can
    already have reached the tracked ledger by some OTHER path (a prior `--fix` run, a hand-edit,
    the CAP-8..9 spec-frontmatter bridge) under a DIFFERENT, independently-minted id, and the
    id/position comparison alone cannot see that — flagging it as missing when its CONTENT is
    already tracked. `scripts/deferred_work_promote.py`'s own `_validate_batch` write-side
    collision guard already defends against exactly this on the write side (a normalized-summary
    match against the tracked ledger); this capability is the read-side (detector) analogue, plus
    a second signal for the shape write-side matching cannot see: an `origin: spec-deferred
    <fingerprint>` marker (CAP-8's own harvest-damping shape, no `summary:` field of its own)
    already present in the tracked ledger's raw text, mirroring CAP-8's own
    `frontmatter_deferral_in_tracked` needle-search exactly.
  - **success:** Confirmed live: pyforge-atlas's own Tier-3 line 7 (summary byte-identical to its
    own tracked `DW-A1-6`) and `DW-10` (no summary, `origin: spec-deferred 8b4c28559f93` already
    present in the tracked ledger via the spec-frontmatter path) both stop being flagged, with no
    per-entry whitelist. **Explicitly bounded, not a full-backlog claim:** this closes the
    ID-vs-content-mismatch class specifically (6 of 117 findings on the live repo, all in
    pyforge-atlas); the remaining ~111 are not asserted to be false positives by this capability —
    they may be genuine, still-unpromoted backlog (Epic 8's own "bounded and shrinking" framing)
    or a further, not-yet-identified detector gap, and are explicitly out of this capability's own
    scope.

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
- **CAP-4..10 extend a shipped Spec; they do not touch CAP-1..3.** Added 2026-08-15 per explicit
  operator direction to keep one Spec rather than split into several — the emitter, detector,
  and baseline mechanisms CAP-1..3 already ship are reused as-is (CAP-5 reuses CAP-1's id
  convention; CAP-6/7 reuse CAP-3's baseline file), never rebuilt.
- **CAP-4..7 (backlog) and CAP-8..9 (hygiene) are the same shape on disjoint artifact types —
  implement as separate check kinds under one owner, not one undifferentiated mega-check.** Each
  finding type stays individually testable and individually runnable (a deferred-work `--fix`
  invocation vs. a separate hygiene-sweep invocation), matching how `deferred-work-check` and
  `dream-chain` already exist as separate `pyforge.doctor.sources` subcommands under one module.
- **Exemplar/quality-bar conformance is out of scope.** `EXEMPLAR-STANDARD.md`'s designated
  golden references, the six-act deck framework, canonical recipe patterns — these are
  judgment-based quality conformance, not a detectable/testable correctness class, and fail
  Spec Law rule 5 (a concrete pass/fail signal). Left in
  `docs/dreams/fleet-hygiene-verification-exemplar-program.md` as catalog/reference, not pulled
  into this Spec.
- **Code-verification of already-tracked entries stays a distinct future effort.** CAP-4..7
  promote a Tier-3 finding into durable storage verbatim, never curate or re-verify it — matches
  the "promoted, not curated" convention every prior manual promotion in this fleet has used.
  Tracked separately in `docs/dreams/deferred-work-resolution-sweep.md`, pending its own
  convergence check against this Spec before it gets specced.

## Non-goals

- **Not a rewrite of the deferral format.** The existing entries carry real content; only
  identity is missing.
- **Not a change to what gets deferred.** Review passes decide that. This is about durability
  of the record, not the decision.
- **Not a fleet-wide id convention.** The per-station difference is deliberate.
- **Not coupled to landing 6-9** — moot as of 2026-08-10: 6-9 has landed, so the ordering
  constraint is discharged rather than merely uncoupled.
- **Not a triage of the existing backlog's *content*.** CAP-6 promotes verbatim; whether any
  individual entry is still worth keeping, still accurate, or already resolved is the
  resolution-sweep's question, not this Spec's.
- **Not exemplar/quality-bar conformance checking** (see Constraints).

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

## Open Questions

- **Q5 (2026-08-15) — does adding CAP-4..10 to an already-`ready` Spec need a fresh
  self-validate pass and a return to `draft` before `bmad-create-epics-and-stories` runs, or can
  a new epic decompose directly since CAP-1..3 are unaffected and already shipped?** Operator
  call, not resolved by this extension.

## Success signal

A story defers something, and the entry it leaves behind is visible to the detector that exists
to protect it. Deleting that entry's id reds a landing pass. The count of invisible deferrals is
zero and stays zero — not because someone swept the backlog, but because nothing new can be
created without an identity.

**CAP-4..10 (2026-08-15):** `pixi run -e local-recipes deferred-work-check` reports 0
`tier3-only-deferral` and 0 `tier3-entry-unidentified` findings fleet-wide after a `--fix` run,
with the baseline re-stamped so a second `--fix` is a no-op. A fleet-wide hygiene sweep run
against all 8 projects reproduces warden's own finding classes as a fixture and finds at least
one true positive elsewhere. `fleet-picture`'s ATTENTION block names a stale loop-home branch
without a manual check.
