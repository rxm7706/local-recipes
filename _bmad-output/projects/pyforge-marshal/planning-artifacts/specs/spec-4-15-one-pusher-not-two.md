---
title: 'One pusher, not two'
type: 'chore'
created: '2026-08-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '11461c3166'
final_revision: '6bd6826dff'
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `scripts/loop_push_watch.py` (pixi task `loop-push-watch`) still calls itself "a
STOPGAP — the durable fix is for the loop to push at its own stage boundaries" — a claim FR-61
(Story 3.8) made false: the supervisor now pushes at `dev-commit-landed`/`review-verdict-
recorded`/`story-merged` boundaries PLUS its own internal interval fallback, automatically, for
every run, with no operator action. Investigation confirms the standalone watcher was never
actually wired to auto-start anywhere (no fleet-launch, CI, or skill invokes it) — it is dead,
misleading documentation, not a live safety net.

**Approach:** Retire `scripts/loop_push_watch.py` outright (its live-run role is fully subsumed;
its docstring's own "run beside a fleet launch" instruction was never enacted). Confirm
`scripts/unpushed_work_check.py` (S-3.10, tip-based, already covers `loop/*` station branches
and is already wired into `marshal status`) as the standing signal for between-runs staleness,
and correct every live description that still calls stage-boundary push unbuilt.

## Boundaries & Constraints

**Always:** Every edit is documentation/task-registration reconciliation or a straight file
deletion — no production code path changes behavior. `pixi.toml`'s `unpushed-work-check`
description gains one sentence stating its role as the standing between-runs signal; no change
to `scripts/unpushed_work_check.py` itself (S-3.10 already covers the case). Deleting
`scripts/loop_push_watch.py` deletes its `pixi.toml` task block AND its
`scripts/spec_surface_allowlist.txt` entry in the same change (else `spec_surface_check` reports
`[stale-allowlist]`, a gating finding — verified live pre-change: the check is green today
specifically because that entry currently matches the file). Because `pixi.toml` is governed by
exactly two spec surfaces (`spec-pyforge-core`, `spec-unified-container` — per
`spec-pyforge-core/.memlog.md`'s own correction note, not three), both `.memlog.md` files get a
`(change) RECONCILED BY NAME` entry naming `pixi.toml`, in this repo's own established format
(five prior identical-shaped entries already exist in each file) — omitting either produces a
gating `[drift]` finding on the station branch.

**Block If:** Nothing here requires human judgment mid-execution — the retire-vs-rescope
decision is resolved by this spec (retire) based on investigation already completed; there is no
runtime ambiguity to halt on.

**Never:** Never touch `supervisor/__main__.py` or `supervisor/durability.py` — FR-61's
stage-boundary + interval-fallback push already ships correctly (Story 3.8, done) and needs no
change. Never touch `scripts/unpushed_work_check.py`'s detection logic — S-3.10 already tip-
compares and already includes `loop/*`; only its `pixi.toml` description gains one confirming
sentence. Never edit `docs/dreams/durable-runs.md` or `docs/dreams/loop-home-fleet-refresh.md` —
both are `status: archived`/`realized` Tier-0 historical prose, explicitly self-marked
superseded; the "unbuilt" claim this story corrects lives only in the two LIVE operational
sites (the script's own docstring, deleted with it, and `pixi.toml`'s task description).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `spec-surface-check` runs after this change | `scripts/loop_push_watch.py` deleted, allowlist entry removed, both memlogs moved naming `pixi.toml` | exits 0 — no `[stale-allowlist]`, `[drift]`, or `[ungoverned]` finding | none |
| Any remaining reference to `loop_push_watch.py`/`loop-push-watch` in a live (non-archived) file | repo-wide grep post-change | zero hits outside `docs/dreams/**` (archived), PRD FR-177 prose, and `epics.md`'s own Story 4.15 text (all historical/requirement records, not live operational claims) | none |
| `unpushed-work-check` invoked standalone | fleet with a `loop/*` branch whose remote tip is behind | reported as unpushed work (S-3.10 behavior, unchanged by this story) | none |

</intent-contract>

## Code Map

- `scripts/loop_push_watch.py` -- DELETE. Its only real function (interval push during a live
  run) is now the supervisor's own automatic interval-fallback (`supervisor/__main__.py`,
  gated on `watched_alive`, `threshold_s` derived from `idle_threshold_minutes`); it was
  confirmed never auto-started anywhere (no fleet-launch/CI/skill invokes it as a subprocess —
  it is 100% manual, and observed NOT running through an entire live multi-hour fleet session
  on 2026-08-03), so deletion changes zero observed behavior.
- `pixi.toml` -- remove the `[feature.local-recipes.tasks.loop-push-watch]` block (task header +
  `description` + `cmd`, plus the one blank separator line before the next task). Append one
  sentence to the `unpushed-work-check` task's `description` (do not touch its `cmd`): state
  that it is now the standing signal for between-runs staleness now that `loop-push-watch` is
  retired, since S-3.10's tip comparison already covers `loop/*` station branches -- no other
  wording in that description changes.
- `scripts/spec_surface_allowlist.txt` -- remove the `scripts/loop_push_watch.py` line (current
  line 37). Required: `spec_surface_check.py` reports `[stale-allowlist]` for any allowlist
  pattern matching zero tracked files, and this pattern would match nothing the instant the
  script is gone.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`
  -- append one `(change) RECONCILED BY NAME, 2026-08-10:` entry naming `pixi.toml`, matching
  this file's own established five-entry precedent verbatim in shape: what changed (the
  `loop-push-watch` task removed, one sentence added to `unpushed-work-check`'s description),
  that it is task-only with no dependency change, and that it has no effect on this Spec's own
  (unbuilt) contract.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container/.memlog.md`
  -- append the matching entry (pixi.toml is governed by exactly two surfaces at once per this
  file's own 2026-08-09 correction note -- this Spec and `spec-pyforge-core`, not
  `spec-pyforge-doctor`): task-only edit, no dependency change, so the container image this Spec
  contracts (CAP-1) is unaffected.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-durable-runs/SPEC.md` --
  in `## What carries forward`, the line "The two shipped scripts (`unpushed_work_check.py`,
  `loop_push_watch.py`) remain live, unmodified by this retirement." is now false for the second
  script. Append a short, dated correction (do not rewrite the frozen historical prose above it):
  note `loop_push_watch.py`'s retirement via this story/FR-177, and that its role is now the
  supervisor's own FR-61 push; `unpushed_work_check.py` remains live and unmodified.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/SPEC.md`
  -- Q3 ("overlap with FR-61 stage-boundary push and loop-push-watch: does this Spec's push step
  subsume the existing watcher for the refresh path, or only complement it?") is answered by this
  story: there is no watcher left to overlap with. Prefix the open-question entry (both in
  frontmatter `open_questions:` and the `## Open Questions` body list) with
  `RESOLVED (Story 4.15, 2026-08-10):` and the one-line answer; do not delete the question text,
  matching this repo's append/annotate convention for resolving recorded questions.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/loop_push_watch.py` -- delete the file -- retires the standalone watcher fully
  subsumed by FR-61
- [x] `pixi.toml` -- remove the `loop-push-watch` task block; add one confirming sentence to
  `unpushed-work-check`'s description -- removes the dead task, states the reconciled role
- [x] `scripts/spec_surface_allowlist.txt` -- remove the `scripts/loop_push_watch.py` line --
  prevents a `[stale-allowlist]` finding
- [x] `spec-pyforge-core/.memlog.md` -- append the `pixi.toml` reconciliation entry -- prevents
  a `[drift]` finding on this spec's governed surface
- [x] `spec-unified-container/.memlog.md` -- append the matching `pixi.toml` reconciliation
  entry -- prevents a `[drift]` finding on the second co-governing spec
- [x] `spec-durable-runs/SPEC.md` -- append the dated correction to "What carries forward" --
  keeps the retirement record accurate about the script it names
- [x] `spec-loop-home-fleet-refresh/SPEC.md` -- resolve Q3 in frontmatter and body -- closes the
  open question this story's own decision answers

**Acceptance Criteria:**
- Given the supervisor's stage-boundary + interval push already ships (FR-61/Story 3.8, done),
  when this story completes, then `scripts/loop_push_watch.py` no longer exists and no live
  (non-archived) file claims stage-boundary push is unbuilt.
- Given `pixi run -e local-recipes spec-surface-check`, when it runs after this change, then it
  exits 0 with no `[stale-allowlist]`, `[drift]`, or `[ungoverned]` finding.
- Given `scripts/unpushed_work_check.py` already tip-compares and already covers `loop/*` station
  branches (S-3.10), when this story completes, then its `pixi.toml` description states it is
  the standing signal for between-runs staleness, with no change to its detection code.

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium 2, low 3)
- defer: 2 (low 2)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` (both reviewers) `spec-loop-home-fleet-refresh/SPEC.md`'s Non-goals
    section still cited `loop_push_watch.py`'s docstring as authority for "the durable fix is
    out of this repo's hands" — now a dangling reference to a deleted file, directly
    contradicting the Q3 resolution added three lines above it in the same diff. Fixed: the
    bullet now states the upstream fix is the supervisor's own shipped FR-61 mechanism and
    notes the retirement, keeping the file internally consistent.
  - `[medium]` `[patch]` (Edge Case Hunter) `spec-durable-runs/.memlog.md`'s 2026-08-09 entry
    asserted "both files exist and run" — now false for `loop_push_watch.py`. Fixed: appended a
    dated correction entry, matching the SPEC.md correction's own pattern.
  - `[low]` `[patch]` (both reviewers) `spec-durable-runs/SPEC.md`'s "What carries forward"
    line stated both scripts "remain live, unmodified" directly above the new Correction
    paragraph stating the opposite for one of them — a stark, avoidable contradiction. Fixed:
    reworded to past tense with a forward pointer to the correction, without rewriting the
    frozen historical record.
  - `[low]` `[patch]` (Edge Case Hunter) The same file's "Why it ended" CAP-2 bullet called
    `loop_push_watch.py` "already shipped" with no note of its later retirement. Fixed: added
    an inline pointer to the correction.
  - `[low]` `[patch]` (Blind Hunter) `docs/dreams/README.md`'s index row for
    `loop-home-fleet-refresh.md` implied the push mechanism still existed and merely needed
    starting ("no auto-start exists anywhere"), misleading since the mechanism no longer exists
    at all. Fixed: reworded to state the during-run push side is now the supervisor's own
    automatic push, and `loop-push-watch` was retired.
  - `[low]` `[defer]` (Blind Hunter) The supervisor's own durability sidecar (FR-61/Story 3.8)
    is now the sole pusher during a live run — if that process itself crashes, nothing pushes,
    with no independent watcher as a structural backstop. Pre-existing since Story 3.8 shipped
    (the retired watcher provided zero actual protection either, confirmed never running);
    out of scope (this story's Boundaries forbid touching supervisor code). Logged to
    deferred-work.md.
  - `[low]` `[defer]` (Blind Hunter) The supervisor's interval-fallback push (unchanged by this
    story) pushes only the station branch, never per-story worktree branches, unlike the
    retired watcher's design — a pre-existing scope characteristic of Story 3.8, not a
    regression from this story. Out of scope for the same reason. Logged to deferred-work.md.
  - `[reject]` (Blind Hunter) `prd.md`'s FR-177 is not annotated as resolved: confirmed against
    this repo's own landing precedent (Story 4.13's and 4.14's landing commits touched neither
    `prd.md` nor `epics.md`) — PRD/epics annotation is landing-owned, not a dev-pass concern.
  - `[reject]` (Blind Hunter) `sprint-status-ledger.yaml` still shows `backlog` for this story:
    same landing-owned mechanism as above, verified by the same precedent.
  - `[reject]` (Blind Hunter) The "confirmed never auto-started anywhere" claim in the spec
    lacks an inline evidence citation: the claim itself is correct (independently re-verified
    by the reviewer), so this is a citation-style preference, not a defect.
  - `[reject]` (Blind Hunter) "Never auto-started" is described as conflated with "fully
    subsumed" in the spec's reasoning: the substantive coverage question this raises is the
    same one already captured by the two `[defer]` findings above; the meta-point about
    argument structure is not itself a defect.
  - `[reject]` (Blind Hunter) The new `unpushed-work-check` description sentence is
    "under-cited" for not also naming `marshal status`'s wiring: the sentence as written is
    true and sufficient (S-3.10's tip comparison is what makes it a standing signal); citing
    additional true facts is not required for correctness.
  - `[reject]` (Blind Hunter) `spec-pyforge-core/.memlog.md`'s "no effect on this Spec's own
    contract" phrasing is unsupported: verified against the file's own prior entries, this
    exact phrasing is established house style used verbatim across multiple earlier
    reconciliation entries, consistently and correctly applied here.

## Design Notes

**Why full deletion, not a deprecation shim or a "no live run" re-scope.** The AC offers two
legitimate paths; deletion is chosen because the re-scope path (push only when no supervisor is
live) has no real target: a home with no live run generates no new local commits by construction
(nothing is running), so a periodic pusher for that state has nothing to do except cover a
crash-orphaned commit -- and that gap is already a DETECTOR's job, not an active-pusher's:
`unpushed_work_check.py` already reports it (tip-based, `loop/*` included), and it is already
folded into `marshal status`'s fleet sweep (`cli/status.py` shells out to the exact same script
-- one detector, two consumers, confirmed by reading both call sites). Re-scoping would build a
new, never-requested "push idle homes" mode to serve a gap that is already both detected and
tied to `marshal status`'s existing reporting. Retiring the never-auto-started watcher, per the
AC's own explicit "removes a duplicate rather than a net loss" framing, is the simpler and
better-evidenced choice.

**Why the two `docs/dreams/*.md` files are out of scope despite repeating the stale claim.**
Both carry `status: archived`/`realized` frontmatter and an explicit banner stating they are
superseded/absorbed into the live PRD (FR-61/62/63). They are frozen historical narrative by this
repo's own Tier-0 convention ("kept, not deleted, so the reasoning that produced the Spec is
still readable"); a reader who needs current system state consults the PRD (already correct)
or `pixi.toml`/the script itself (corrected by this story), not an archived Dream. Editing
Dream prose piecemeal, outside a dedicated Dream-trim pass, risks exactly the kind of
"Dream trim waits for its Spec" violation this repo's own convention warns against.

## Verification

**Commands:**
- `git ls-files scripts/loop_push_watch.py` -- expected: empty output (file untracked/deleted)
- `grep -rn "loop_push_watch\|loop-push-watch" --include='*.py' --include='*.toml' --include='*.txt' .` -- expected: zero hits
- `pixi run -e local-recipes spec-surface-check` -- expected: exit 0, "OK: every tracked file governed or allowlisted; no drift."
- `pixi run -e local-recipes unpushed-work-check -- --branches-only --json` -- expected: runs clean (exit 0 or reports pre-existing unpushed branches unrelated to this change), proving the standing signal is unaffected
- `python3 -c "import tomllib; tomllib.load(open('pixi.toml','rb'))"` -- expected: no exception (valid TOML after the task-block removal)

## Auto Run Result

**Summary:** Retired `scripts/loop_push_watch.py` (the standalone interval-push watcher),
confirmed `scripts/unpushed_work_check.py` as the standing between-runs staleness signal, and
reconciled every live description that still claimed stage-boundary push was unbuilt.

**Files changed (9):**
- `scripts/loop_push_watch.py` — deleted (148 lines; never auto-started anywhere, role fully
  subsumed by the supervisor's own FR-61 push).
- `pixi.toml` — removed the `loop-push-watch` task; added one confirming sentence to
  `unpushed-work-check`'s description.
- `scripts/spec_surface_allowlist.txt` — removed the now-dead `loop_push_watch.py` entry.
- `spec-pyforge-core/.memlog.md`, `spec-unified-container/.memlog.md` — appended `pixi.toml`
  reconciliation entries (both co-govern the file).
- `spec-durable-runs/SPEC.md`, `spec-durable-runs/.memlog.md` — corrected now-false claims
  that the retired script "remains live, unmodified."
- `spec-loop-home-fleet-refresh/SPEC.md` — resolved Q3 (frontmatter + body) and fixed a stale
  Non-goals citation of the deleted script's docstring.
- `docs/dreams/README.md` — corrected the `loop-home-fleet-refresh.md` index row, which implied
  the push mechanism still existed and merely needed starting.

**Review findings breakdown:** 0 intent_gap, 0 bad_spec, 5 patch (all applied — 2 medium, 3
low), 2 defer (logged to `deferred-work.md`: the supervisor sidecar is a single point of
failure during a live run; its interval fallback covers only the station branch, not per-story
branches — both pre-existing since Story 3.8, neither caused by this story), 6 reject (PRD/
sprint-status-ledger annotation is landing-owned per verified precedent; the rest were citation
nitpicks on already-correct claims).

**Verification performed:** `git ls-files scripts/loop_push_watch.py` empty; repo-wide grep for
`loop_push_watch`/`loop-push-watch` across `*.py`/`*.toml`/`*.txt` zero hits; `pixi.toml` valid
TOML after edit; `pixi run -e local-recipes spec-surface-check` exits 0 clean (no
`[stale-allowlist]`/`[drift]`/`[ungoverned]`); `pixi run -e local-recipes unpushed-work-check --
--branches-only --json` runs cleanly, confirming the standing-signal role is intact.

**Residual risks:** None blocking. Two low-severity, pre-existing architectural characteristics
of the supervisor's own durability mechanism (Story 3.8, unchanged here) are logged to
`deferred-work.md` for a future story's judgment, not this one's to fix.
