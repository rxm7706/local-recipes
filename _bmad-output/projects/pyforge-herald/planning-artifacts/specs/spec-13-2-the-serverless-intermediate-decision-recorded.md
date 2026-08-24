---
title: 'The serverless-intermediate decision, recorded'
type: 'chore'
created: '2026-08-11'
status: 'done'
review_loop_iteration: 5
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'cfc951aac9f3cf63eb1c4d6cf20cc96b4d44f0e2'
final_revision: 'd9a16e7192fc0eb246d164dbd0abea0a12176d97'
---

<intent-contract>

## Intent

**Problem:** Epic 13's Spec Constraint 2 blocks Story 13.3 (DB-backed storage) from dispatching
until each of the Spec's three named cheaper alternatives (`herald snapshot`, telemetry-derived
defaults for `herald progress --update`, locking-plus-hook-triggered CLI invocation) is either
built or its skip is justified in writing, measured against the full backend's (LB-1/2/3) cost —
undecided today.

**Approach:** Confirm each named step's current (non-)existence directly in the shipped codebase
(not from the 2026-08-08 research doc alone), weigh each against Epic 13's already-approved
LB-1/2/3 work and the operator's prior go/hosting-adoption decisions, and append a `(decision)`
entry with a per-item build-or-skip verdict and justification to the Spec's `.memlog.md`
companion.

## Boundaries & Constraints

**Always:**
- Ground each of the 3 named items' verdict in the shipped codebase's actual current state,
  confirmed by direct inspection, not inferred from the research doc's 2026-08-08 snapshot.
- Give each of the 3 named items its own explicit, individually-justified verdict (build or
  skip) — never one blanket reason covering all three.
- Justify any skip verdict against the full backend's already-committed cost (Stories
  13.3-13.6), not merely assert it as low-priority.
- Append the decision as a `(decision)`-tagged bullet to `.memlog.md`, matching its existing
  tag/entry convention (`(provenance)`, `(note)`, `(capability)`, `(question)`, `(decision)`,
  `(constraint)`, `(event)`), and bump the file's `updated:` frontmatter timestamp.

**Block If:**
- Investigation finds Story 13.1 is not actually `status: done` — this decision cannot be made
  against an unmet hard prerequisite. HALT.
- Evidence surfaces that materially contradicts the operator's already-recorded 2026-08-09 /
  2026-08-10 go / Steward-hosting-adoption decisions (e.g., the adopted pattern turns out
  unavailable) — that is a human's decision to revisit, not this story's. HALT.

**Never:**
- Implement any of the three named steps as code. A "build" verdict records that a step becomes
  epic scope; it does not execute that scope inside this story (Effort: S, no source-code
  surface).
- Edit or renumber `epics.md` / `sprint-status.yaml` story entries — this story's surface is the
  Spec's memlog only; epics.md stays the static plan (no other completed story in this project
  carries an inline resolution marker).
- Touch the Spec's own `SPEC.md` `status` or `open_questions` frontmatter — neither is about this
  constraint.

</intent-contract>

## Code Map

- `_bmad-output/planning-artifacts/specs/spec-herald-moments-2-4-live-backend/.memlog.md` --
  append the decision entry here (12 existing entries; established `(tag)` convention)
- `_bmad-output/implementation-artifacts/deferred-work.md` -- append a `herald snapshot`
  follow-up entry here (see Design Notes; revised after review pass 1 -- item 1 is a BUILD
  verdict, tracked here rather than skipped; wording refined again in review pass 2)
- `_bmad-output/planning-artifacts/specs/spec-herald-moments-2-4-live-backend/SPEC.md` --
  read-only: Constraints § "Sequence behind the serverless intermediates", Capabilities LB-1/2/3
- `_bmad-output/planning-artifacts/research/technical-herald-shipped-architecture-research-2026-08-08.md`
  -- read-only: §4.2 names the 3 steps, §4.3 prices the full backend
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` (`_run_progress_update` `:942`)
  -- read-only: confirms no telemetry-derived defaults exist
- `src/shared/packages/pyforge-herald/scripts/export_web_snapshot.py`,
  `scripts/export_notices_snapshot.py`, `web/scripts/sync-progress.mjs` -- read-only: the three
  unconsolidated per-tab export paths `herald snapshot` would replace; the first two's docstrings
  are load-bearing evidence for item 1's revised BUILD verdict (see Design Notes)
- `src/shared/packages/pyforge-herald/docs/automation-troubleshooting.md` -- read-only: documents
  the current CLI-by-hand workflow as an accepted interim state
- `src/shared/packages/pyforge-herald/tests/test_locking.py`, `tests/test_state.py`,
  `tests/test_progress.py`, `tests/test_claims.py`, `tests/test_notices.py` -- read-only: tracked,
  durable evidence for Story 13.1's concurrency-lock proof (item 3's justification), cited instead
  of the gitignored `implementation-artifacts/spec-13-1-*.md` (review pass 2 finding)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (Herald's own, `13-4:` line) and the
  sibling `pyforge-steward` project's `implementation-artifacts/sprint-status.yaml` (`9-1:` line)
  -- read-only: ground `steward:S-9.1`'s actual landed status (review pass 2 finding)
- `_bmad-output/planning-artifacts/specs/spec-13-1-the-state-layer-survives-a-second-writer.md` --
  NEW: promote the already-merged Story 13.1's spec from the gitignored `implementation-artifacts/`
  copy to this tracked location, per this repo's own CLAUDE.md "story specs are durable" convention
  (overdue -- every other Story 1.1-12.4 spec is already promoted here, 13.1 is the one gap) and
  per review pass 4's finding that item 3's severity citation depended on an ephemeral file
- `_bmad-output/planning-artifacts/specs/README.md` -- update the stale "47 stories (Epics
  1-12)... no promotion gap" status line for the 48th (Epic 13) promotion this pass adds (review
  pass 5 finding -- caused directly by this story's own Task 3)

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/planning-artifacts/specs/spec-herald-moments-2-4-live-backend/.memlog.md` --
  append the `(decision)` entry and the closing `(note)` entry below verbatim (already fully
  reasoned in Design Notes); bump `updated:` frontmatter
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- append BOTH entries below
  verbatim: the `herald snapshot` follow-up (item 1's BUILD verdict, tracked here rather than
  executed as code in this story) AND a second, new `defer`-classified entry (review pass 5)
  documenting that `deferred-work.md` itself is written via an unlocked read-modify-write across
  a Tier-3 cross-worktree backlink -- pre-existing, not caused by this story, surfaced
  incidentally and now formally deferred rather than left to resurface a third time
- [x] `_bmad-output/planning-artifacts/specs/spec-13-1-the-state-layer-survives-a-second-writer.md`
  -- create by copying the existing `_bmad-output/implementation-artifacts/spec-13-1-the-state-layer-survives-a-second-writer.md`
  verbatim (byte-for-byte, no edits) -- promotes an already-merged story spec to its durable,
  tracked home per this repo's own convention, and makes this story's own item-3 citations of
  Story 13.1's review-triage detail independently verifiable from a non-gitignored source
- [x] `_bmad-output/planning-artifacts/specs/README.md` -- update the stale "47 stories (Epics
  1-12)... no promotion gap" line to reflect the 48th (Epic 13) spec this pass promotes

**Acceptance Criteria:**
- Given the appended `.memlog.md` entry, when read, then all three named steps (`herald
  snapshot`, telemetry-derived defaults, hook-triggered CLI) each carry an explicit verdict, and
  no two verdicts share a single undifferentiated reason.
- Given the appended entries, when compared against the shipped codebase, then every factual
  claim in them (what exists / doesn't exist today, what each script's docstring says) is
  independently verifiable, not asserted.
- Given item 1's BUILD verdict, when `deferred-work.md` is read, then it names the concrete
  fix candidate and the evidence (both export scripts' docstrings) grounding it as follow-up
  work, not new Epic 13 scope.
- Given the decision is recorded, when Story 13.3 is next considered for dispatch, then nothing
  about it remains blocked by Spec Constraint 2.
- Given the promoted `spec-13-1-*.md`, when diffed against the original `implementation-artifacts`
  copy, then the two are byte-identical (a promotion, not a rewrite).
- Given the promotion, when `planning-artifacts/specs/README.md` is read, then its story-count
  status line matches the directory's actual contents (48, Epics 1-13's first spec).
- Given `deferred-work.md` after this pass, when read, then it contains two new entries (`herald
  snapshot`, and the file's own unlocked-write race), not one.

## Spec Change Log

### 2026-08-11 — Review pass 5 bad_spec repair (final -- iteration cap reached next pass)
- **Triggering findings:** Blind Hunter's pass-5 run independently re-verified every high-stakes
  claim in the entry and found nothing to report -- explicit convergence signal. Edge Case Hunter
  found three items: (a) the `steward:S-9.1` DONE claim, while factually correct (re-verified
  independently a third time), cites the sibling project's gitignored `implementation-artifacts/`
  ledger; the one artifact a reader of THIS repo can actually check without cross-project access
  -- `pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` (tracked) -- still reads
  `9-1: backlog` as of its last regeneration (2026-08-10 21:35, before the landing). (b) this
  story's own Task 3 (promoting `spec-13-1-*.md`) makes `planning-artifacts/specs/README.md`'s
  "47 stories (Epics 1-12)... no promotion gap" status line stale the moment it lands -- caused
  directly by this story's own change. (c) `deferred-work.md`'s unlocked-write race, first
  surfaced in pass 3 and explicitly deferred as "will be re-evaluated... if still applicable," is
  still applicable and still unaddressed two passes later.
- **Amended:** the closing `(note)` now names both sources for the `steward:S-9.1` claim and
  states plainly that the tracked ledger is stale, so a reader checking it isn't left confused.
  New Task 4 updates `planning-artifacts/specs/README.md`'s status line. Task 2 now covers a
  SECOND `deferred-work.md` entry: a formal `defer` for the file's own unlocked read-modify-write
  race (this is the entry that finally closes it out, rather than leaving it to resurface again).
- **Known-bad state avoided:** a decision record whose central cross-project claim couldn't be
  checked by a reader confined to this repo without an explanation of why the one artifact they
  *can* check disagrees, and a stale README the very artifact promoted here contradicts by count.
- **KEEP:** everything from passes 1-4 -- all three verdicts, the `steward:S-9.1` correction, the
  SQLite-vs-fcntl note fix, the 13.3+13.4 window bound, the `state.py` exclusion, the
  `notices._write_markdown` caveat, the two-dispositions wording, and the spec-13-1 promotion.
  None revisited or reverted by this pass.

### 2026-08-11 — Review pass 4 bad_spec repair
- **Triggering findings (Blind Hunter, 8 actionable):** (a) item 3's "write paths a hook would
  exercise" wrongly listed `state.py` — that module is scoped to deck-bridge commands only,
  never touched by progress/success/notice automation. (b) item 3's safety claim omitted a real,
  documented residual gap directly in its own claimed-safe surface: `notices._write_markdown` is
  still a non-atomic `write_text` (`deferred-work.md`'s pass-5 entry), so a concurrent reader can
  observe a torn file even after Story 13.1's lock. (c) the "one medium, one low" severity
  citation was sourced from a gitignored file with no durable equivalent (the specific claim that
  the file "doesn't exist anywhere in this worktree" was itself wrong — it does — but the
  durability concern is real and matches this repo's own promotion convention, unapplied to
  Story 13.1). (d) "duplicate mechanism" flattened a local git hook (opt-in, single-operator) and
  a server-side webhook (universal) as strictly equivalent. (e) the closing note's "CLOSED: yes"
  on the real-pull open question re-asserted the funding-vs-demand-evidence conflation pass 1
  already fixed elsewhere in this same entry, in a spot pass 1 didn't touch. (f) "three different
  dispositions" is arithmetically wrong (two dispositions: BUILD, SKIP, across three items). (g)
  per-item cost comparisons cited only 13.3+13.4, not engaging 13.5/13.6 as the AC's "Stories
  13.3-13.6" wording asks, even though the aggregate Net section does. (h) the research doc names
  five serverless-intermediate steps; this entry addresses only the three `epics.md`'s own
  Constraint 2 names, without saying so, risking a future reader assuming three is the complete
  universe considered.
- **Amended:** (a) `state.py` dropped from item 3's write-path list, leaving
  `progress`/`claims`/`notices`. (b) item 3's safety paragraph now names the
  `notices._write_markdown` non-atomicity gap explicitly and scopes the safety claim to what it
  actually covers (writer-vs-writer serialization, not reader-vs-writer atomicity). (c) Story
  13.1's spec promoted to `planning-artifacts/specs/` (new Task 3; see Code Map) so the severity
  citation is independently verifiable from a durable, tracked source rather than worked around.
  (d) item 3 now distinguishes the CI-job reading (genuine duplicate of 13.4's trigger surface)
  from the local-git-hook reading (narrower, still a second maintained path). (e) the closing
  note's "CLOSED: yes" qualified as funding-readiness (matching `epics.md`'s own framing), not
  independent demand evidence. (f) "three different dispositions" corrected to name the two
  dispositions across three items. (g) each item's cost paragraph now names why 13.5/13.6 are not
  the relevant comparison (no functional overlap) while the Net section keeps citing all four.
  (h) one clause added noting the research doc names two further steps this story's Constraint 2
  doesn't cover and why (not part of the binding three).
- **Known-bad state avoided:** a safety argument (item 3) that omitted the one residual gap
  actually located in the write paths it claims are safe, and a severity citation that, while
  factually present today, depended on a file this repo's own documented incident history (the
  pyforge-warden/pyforge-atlas Tier-3 losses in CLAUDE.md) says does not reliably survive
  worktree teardown.
- **KEEP:** all three verdicts (item 1 BUILD, items 2/3 SKIP), the `steward:S-9.1` correction and
  SQLite-vs-fcntl note fix from pass 2, and the 13.3+13.4 window-bound fix from pass 3 — none
  disturbed by this pass; only precision and completeness improved.

### 2026-08-11 — Review pass 3 bad_spec repair
- **Triggering finding:** Blind Hunter found item 3's SKIP justification said the interim window
  a hook-triggered CLI would fill is "bounded by Story 13.3's own build (Effort: L)" — but a
  hook's actual redundancy point is Story 13.4 shipping (the webhook), not Story 13.3 (the DB
  swap, which adds no triggering). Since 13.4 depends on 13.3, the correct bound is 13.3+13.4
  combined — the same metric item 2 already used one paragraph earlier in the same entry.
- **Amended:** Item 3's window language corrected to match item 2's "13.3+13.4 combined (Effort
  L, L)" framing. The verdict is unchanged (still SKIP) — a longer, more precisely-bounded window
  doesn't flip it, since the core argument is the duplicate-mechanism cost, not the exact window
  length; "bounded, not indefinite" (true either way after `steward:S-9.1` landed) is what
  matters, and that holds under the corrected figure too.
- **Known-bad state avoided:** an internal inconsistency between item 2's and item 3's own stated
  cost metrics for what is, on inspection, the identical dependency chain (13.3 -> 13.4) — a
  reader comparing the two paragraphs would have noticed the mismatch and had reason to distrust
  the rest of the entry's arithmetic.
- **KEEP:** everything else from pass 2's repair (the `steward:S-9.1` correction, the closing
  note's SQLite-vs-fcntl fix, the durable test-file citations, the effort-size citations) —
  independently re-verified accurate by pass 3's Blind Hunter and Edge Case Hunter runs.
- **Not actioned this pass (protocol: bad_spec makes lower-category findings moot; deferred to
  the next fresh review pass against the corrected diff):** Blind Hunter also noted `epics.md`'s
  frozen Epic 13 preamble has no visible pointer to the memlog's three-way disposition (a
  discoverability observation, not a factual error — the story's own AC sanctions recording the
  resolution in the memlog, not in `epics.md`, which this story's Never-list forbids editing).
  Edge Case Hunter found `deferred-work.md` itself is written via an unlocked read-modify-write
  across a Tier-3 cross-worktree backlink (the same race class Story 13.1 fixed for Herald's own
  state files, here in the BMAD governance tooling instead) — real, pre-existing, and not
  introduced by this diff; latent today (no concurrent `pyforge-herald` worktree active).

### 2026-08-11 — Review pass 2 bad_spec repair
- **Triggering finding:** Edge Case Hunter found the pass-1 text's central timeline premise —
  `steward:S-9.1` is `backlog` with no committed date — was already stale: the sibling
  `pyforge-steward` project's own `sprint-status.yaml` shows it `done`, landed 2026-08-11 (after
  this story's `baseline_revision`), unblocking Story 13.4. Blind Hunter separately found the
  closing `(note)` bullet self-contradicted the entry's own body: it claimed the SQLite-vs-fcntl
  clause "remains genuinely open" when Story 13.1 (done) already resolved it as its own first AC
  (per-file advisory locking); found "two residual low-severity items" undercounts Story 13.1's
  actual pass-7 deferred tally (`defer: 2: (high 0, medium 1, low 1)` — one is medium); found
  item 2's "strict superset" claim presumes facts about Story 13.4's still-undesigned trigger/
  payload shape (13.4's own first AC); and found the skip verdicts never cited the actual
  committed sizes (`epics.md`: 13.3 Effort L, 13.4 L, 13.5 M, 13.6 M) the AC requires them to be
  measured against.
- **Amended:** Design Notes items 2 and 3 rewritten to reflect `steward:S-9.1` landing (the
  interim window either item would fill is now short and bounded by Story 13.3's build, not an
  open-ended external block — this makes both SKIP verdicts *more* defensible, not less, but the
  stale premise had to be corrected regardless per this story's own AC 2). The closing `(note)`
  rewritten: SQLite-vs-fcntl is CLOSED (not open), only the webhook-trigger/auth clause remains
  open; a second closing thread added noting Herald's own `sprint-status.yaml` still shows
  `13-4: blocked` (stale, out of scope to fix here per this story's Never-list). Item 3's severity
  claim corrected to name the actual pass-7 tally and clarify neither deferred item touches the
  write paths a hook would exercise. Item 2 softened to "expected to substantially reduce" rather
  than "strict superset," with 13.4's own open first AC named. Both skip verdicts now cite
  `epics.md`'s actual Effort sizes. Citations for Story 13.1's concurrency proof switched from the
  (gitignored, ephemeral) story-spec file to the tracked, durable test files themselves
  (`tests/test_locking.py`, `tests/test_state.py`, `tests/test_progress.py`,
  `tests/test_claims.py`, `tests/test_notices.py`) plus the merge commit already recorded as this
  story's own `baseline_revision`. Item 1's "closes a real, currently-live risk" softened to
  "would close" (present-tense overclaim — nothing is built yet) in both the memlog entry and the
  `deferred-work.md` entry; minor wording fix distinguishing `herald snapshot` (a command) from
  the other two items (behaviors/integration points, not commands).
- **Known-bad state avoided:** a decision record whose own central timeline claim was already
  false at authoring time (S-9.1 landed hours before this pass), and a closing note that
  contradicted its own entry's body about whether Story 13.1 resolved the SQLite-vs-fcntl
  question — either one would have misled whoever reads this memlog next about Story 13.4's
  actual readiness to dispatch once 13.3 completes.
- **KEEP:** all three verdicts (item 1 BUILD, items 2/3 SKIP) — unchanged by this pass; only
  their factual grounding and precision improved. The append-only mechanics, per-item structure,
  and the `deferred-work.md`-not-Epic-13-scope resolution for item 1.

### 2026-08-11 — Review pass 1 bad_spec repair
- **Triggering finding:** Blind Hunter found the original Design Notes' `herald snapshot` SKIP
  verdict contradicted the shipped code's own docstrings (`export_web_snapshot.py`,
  `export_notices_snapshot.py`), which already anticipate and half-build exactly this
  consolidation as a low-risk next step, independent of Epic 13's DB/webhook/cron scope. Blind
  Hunter also found the original "moot" framing overclaimed what the operator's go decision
  actually resolved, and that items 2/3 leaned on a single shared, unfalsifiable timeline
  assumption rather than independent reasoning. Edge Case Hunter found a stale pre-existing
  `(question)` bullet in `.memlog.md` that the new entry's "already answered" claim contradicted
  without closing.
- **Amended:** Design Notes rewritten: item 1 (`herald snapshot`) changed from SKIP to BUILD,
  tracked via a new `deferred-work.md` entry rather than executed as code in this story (still
  compliant with the untouched `<intent-contract>` Never-boundary against implementing any step
  as code). Items 2 and 3 keep SKIP but with tightened, timeline-independent justifications and
  an explicit revisit trigger (Story 13.4's own dispatch). Added a `(note)` bullet closing the
  stale open-question clause. Code Map corrected (12 existing memlog entries, not 17) and
  extended to include `deferred-work.md`. Tasks & Acceptance extended with the second append
  task and a fourth AC.
- **Known-bad state avoided:** a `.memlog.md` entry asserting `herald snapshot` isn't worth
  building when the shipped code's own authors already scoped and half-built it as the obvious
  next increment — a claim any reader who opened those two scripts would immediately see was
  wrong, undermining the credibility of the other two verdicts by association.
- **KEEP:** items 2 and 3's core SKIP verdicts (only their justification wording changed); the
  append-only mechanics and per-item structure; the "no Epic 13 renumbering" resolution — still
  correct, now reached for a different reason (item 1 isn't Epic 13 scope at all, not because
  all three were skipped).

## Review Triage Log

### 2026-08-11 — Review pass 6 (converged)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none
- (Both Blind Hunter and Edge Case Hunter, run independently and in parallel over the full
  current diff -- `.memlog.md`, `README.md`, the promoted `spec-13-1-*.md`, and both
  `deferred-work.md` entries -- reported zero findings after re-verifying the highest-stakes
  claims directly against the live codebase. Combined with pass 5's Blind Hunter convergence
  signal, this is two consecutive passes with no defects surviving independent adversarial
  review. The artifact has converged.)

### 2026-08-11 — Review pass 5
- intent_gap: 0
- bad_spec: 1 (high 0, medium 0, low 1)
- patch: 1 (high 0, medium 0, low 1)
- defer: 1 (high 0, medium 0, low 1)
- reject: 0
- addressed_findings:
  - `[low]` `[bad_spec]` `steward:S-9.1`'s DONE status was correct but cited only a gitignored,
    cross-project file, while the one tracked artifact a reader here can check
    (`sprint-status-ledger.yaml`) still says `backlog` -- closing note now names both and
    explains the tracked one is stale, rather than leaving the discrepancy unexplained.
  - `[low]` `[patch]` `planning-artifacts/specs/README.md`'s story-count status line, made stale
    by this story's own Task 3 promotion -- updated (new Task 4).
  - `[low]` `[defer]` `deferred-work.md`'s own unlocked read-modify-write race (first surfaced
    pass 3, still applicable) -- formally deferred via a second new entry in the same file,
    closing the loop rather than leaving it to resurface again.
- (Blind Hunter's independent pass-5 run reported zero findings after re-verifying every
  high-stakes claim in the entry -- an explicit convergence signal alongside Edge Case Hunter's
  narrowing finding count: 6 findings pass 1 -> 6 pass 2 -> 1 pass 3 -> 8 pass 4 -> 3 pass 5, all
  low-severity this pass.)

### 2026-08-11 — Review pass 4
- intent_gap: 0
- bad_spec: 8 (high 0, medium 3, low 5)
- patch: 0
- defer: 0
- reject: 1 (high 0, medium 0, low 1)
- addressed_findings:
  - `[medium]` `[bad_spec]` Item 3's write-path list wrongly included `state.py` (scoped to
    deck-bridge commands only) — removed.
  - `[medium]` `[bad_spec]` Item 3's safety claim omitted `notices._write_markdown`'s documented
    non-atomic-write gap, which sits directly in a hook-relevant write path — named explicitly,
    safety claim scoped to what it actually covers.
  - `[medium]` `[bad_spec]` Severity citation ("one medium, one low") depended on a gitignored
    file with no durable equivalent — Story 13.1's spec promoted to `planning-artifacts/specs/`
    (new Task 3) rather than reworded around.
  - `[low]` `[bad_spec]` "Duplicate mechanism" flattened a local git hook and a server-side
    webhook as strictly equivalent — item 3 now distinguishes the two readings.
  - `[low]` `[bad_spec]` Closing note's "CLOSED: yes" re-asserted the funding-vs-demand-evidence
    conflation pass 1 fixed elsewhere — qualified as funding-readiness, not demand evidence.
  - `[low]` `[bad_spec]` "Three different dispositions" is arithmetically wrong (two dispositions
    across three items) — corrected.
  - `[low]` `[bad_spec]` Per-item cost paragraphs cited only 13.3+13.4 without saying why
    13.5/13.6 aren't the relevant comparison — one clause added per item.
  - `[low]` `[bad_spec]` The research doc names five serverless-intermediate steps; this entry
    silently addressed only the three `epics.md` names — one clause added noting the other two
    are out of this story's binding scope and why.
  - `[reject]` "Item 1's deferred-work entry lacks severity/status/owner fields, a discoverability
    gap" — restated pass 2's already-settled finding (matches file convention; not a required
    fix), offered as an observation ("even though it's compliant"), not a new defect.

### 2026-08-11 — Review pass 3
- intent_gap: 0
- bad_spec: 1 (high 0, medium 0, low 1)
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[bad_spec]` Item 3's stated interim-window bound ("Story 13.3's own build") didn't
    match item 2's own bound ("13.3+13.4 combined") for the identical dependency chain — item 3
    corrected to the same 13.3+13.4 metric; verdict unchanged.
  - (2 additional findings from this pass -- `epics.md` discoverability observation, and an
    unlocked-write race in `deferred-work.md` itself -- are moot per protocol once bad_spec
    triggered a re-derivation; see Spec Change Log "Not actioned this pass." Will be
    re-evaluated by the next review pass against the corrected diff if still applicable.)

### 2026-08-11 — Review pass 2
- intent_gap: 0
- bad_spec: 6 (high 1, medium 3, low 2)
- patch: 0
- defer: 0
- reject: 5 (high 0, medium 0, low 5)
- addressed_findings:
  - `[high]` `[bad_spec]` `steward:S-9.1` claimed `backlog`/no committed date; confirmed `done`
    (landed 2026-08-11, after baseline) via the sibling project's own `sprint-status.yaml` —
    items 2/3 rewritten around the now-short, bounded interim window.
  - `[medium]` `[bad_spec]` Closing `(note)` bullet claimed the SQLite-vs-fcntl clause "remains
    genuinely open," contradicting the entry's own body (Story 13.1, done, resolved it as its
    first AC) — rewritten to state it is CLOSED, only the webhook-trigger clause remains open.
  - `[medium]` `[bad_spec]` "Two residual low-severity items" undercounted Story 13.1's actual
    pass-7 deferred tally (one medium, one low) — corrected, with a note that neither touches the
    write paths a hook-triggered CLI would exercise.
  - `[medium]` `[bad_spec]` Item 2's "strict superset" claim presumed facts about Story 13.4's
    still-undesigned trigger/payload shape — softened to "expected to substantially reduce," with
    13.4's own open first AC named.
  - `[low]` `[bad_spec]` Skip verdicts never cited the actual committed Effort sizes (`epics.md`)
    the AC requires them to be measured against — added (13.3 L, 13.4 L, 13.5 M, 13.6 M).
  - `[low]` `[bad_spec]` Story 13.1's concurrency-proof citation relied on an ephemeral
    (gitignored) story-spec file rather than a durable source — switched to the tracked test
    files plus the already-recorded `baseline_revision` merge commit.
  - `[reject]` Item 1 "BUILD via deferred-work.md is operationally identical to SKIP" — this
    repo's own deferred-work ledger has a demonstrated track record of items being picked up and
    closed by later stories (e.g. `DW-1-1-1`, `DW-1-4-2`); softened "closes" to "would close" for
    tense accuracy but did not change the mechanism.
  - `[reject]` "'Epics 9/10 follow-up' home doesn't exist since both epics are closed" — the
    phrase describes provenance (whose docstring deferred this), not a claim that an open epic
    receives it; `deferred-work.md` entries routinely have no epic home until picked up.
  - `[reject]` Item 3's revisit trigger "has no enforcement mechanism" — consistent with every
    other forward-pointer in this memlog and the deferred-work ledger; not a deviation from
    established practice.
  - `[reject]` "No renumbering conclusion survived a rationale swap without visible re-derivation"
    — process commentary on pass 1's history, not a defect in the current artifact, which is
    correctly re-derived for its current (correct) reasons.
  - `[reject]` `deferred-work.md` entry "lacks a severity/status field" — no entry in the
    pre-promotion file carries one; severity/status are added at ledger-promotion time, not at
    authoring time, matching every other entry in the file.

### 2026-08-11 — Review pass 1
- intent_gap: 0
- bad_spec: 6 (high 1, medium 2, low 3)
- patch: 2 (high 0, medium 0, low 2)
- defer: 0
- reject: 5 (high 0, medium 0, low 5)
- addressed_findings:
  - `[high]` `[bad_spec]` `herald snapshot` SKIP verdict factually contradicted the shipped
    exporters' own docstrings (both already anticipate/half-build this exact consolidation) —
    Design Notes rewritten: item 1 -> BUILD, tracked via a new `deferred-work.md` entry.
  - `[medium]` `[bad_spec]` "the intermediates' purpose is moot" overclaimed what the operator's
    go decision resolved (funding/hosting, not standalone user-value evidence) — Net section
    reframed to a per-item cost/value comparison against Epic 13's committed work.
  - `[medium]` `[bad_spec]` Items 2 and 3's SKIP verdicts leaned on an unfalsifiable "the block
    won't last long" assurance with no re-evaluation trigger — rewritten with timeline-
    independent reasoning plus an explicit revisit trigger (Story 13.4's own dispatch).
  - `[low]` `[bad_spec]` "Each independently justified" framing was undercut by items 2 and 3
    sharing one premise (13.4 landing soon) — item 3's justification rewritten to hold
    regardless of 13.4's timeline; item 2's rewritten around its own bounded value.
  - `[low]` `[bad_spec]` Fleet-wide velocity ("10 stories in a session") was cited as evidence
    for one station's (Steward's) specific backlog movement — a scope mismatch — removed from
    item 3's justification entirely.
  - `[low]` `[bad_spec]` Item 3's "13.1 makes this safe" claim didn't acknowledge 13.1's own
    `followup_review_recommended: true` flag — reworded to name precisely what is/isn't settled
    (core race closed and proven; two low-severity residuals and Windows coverage are unrelated
    to this trigger's safety).
  - `[low]` `[patch]` Code Map's memlog entry count was wrong (claimed 17, actually 12) —
    corrected.
  - `[low]` `[patch]` A pre-existing `(question)` bullet in `.memlog.md` was left uncontradicted
    by the new entry's "already answered" claim — added a closing `(note)` bullet naming exactly
    which clause is resolved and which two remain open.

## Design Notes

**Current-state grounding (confirmed directly against the shipped code, 2026-08-11):**
- `herald snapshot`: does not exist as a command, but the consolidation seam already does.
  `export_web_snapshot.py`'s docstring designs itself as the shared exporter and explicitly
  anticipates "a future Epic 8/10 snapshot adds a sibling `export_*_snapshot` function here
  rather than a duplicate script"; `export_notices_snapshot.py`'s docstring says a later story
  can fold all three into one script "once the shape each Moment needs is settled" (deferred
  deliberately -- Simplicity First, not architectural doubt). That precondition is now met: all
  three exporters (`export_web_snapshot.py` writing `web/public/success.json` via
  `claims.snapshot()`, `export_notices_snapshot.py` writing `web/public/notices.json`,
  `web/scripts/sync-progress.mjs` copying `.herald/progress.json` -> `web/public/progress.json`,
  wired into npm's `predev`/`prebuild`, `web/package.json:8-11`) exist and ship stable output. No
  JSON record anywhere carries a `generated_at` freshness stamp.
- Telemetry-derived defaults: do not exist. `_run_progress_update` (`cli.py:942`) takes
  `--shipped`/`--compute-hours`/`--token-spend`/`--wall-clock-hours` as pure operator-typed
  input; its own docstring names this the deliberately scoped-down interpretation of the
  original AC ("extracted from bmad-loop journal / CI webhook payload" was never built). No code
  under `src/pyforge/herald/` reads `sprint-status-ledger.yaml` or any bmad-loop run state.
- Hook-triggered CLI: does not exist. No `post-merge` git hook or CI workflow step invokes any
  `herald` command; `docs/automation-troubleshooting.md` documents this as by-design ("scaled
  down to a CLI an operator runs by hand"). Story 13.1's lock closes the core lost-update race for
  writer-vs-writer serialization (proven by concurrency tests); its two pass-7 residual items
  (one medium, one low) are unrelated to this trigger's safety (`claims.py` revalidate path, not
  progress/success/notice writes), but a separate, real residual is relevant:
  `notices._write_markdown`'s non-atomic write means the lock doesn't guarantee reader-vs-writer
  atomicity (see item 3's full analysis below).

**Revised after adversarial review pass 1** (Blind Hunter + Edge Case Hunter): the original
draft skipped all three under one framing ("the evidence question is moot"). Review correctly
found that framing both overclaimed (the operator's go decided *whether to fund the epic*, not
*whether users want the automatic-feel*) and, for item 1 specifically, contradicted the shipped
code's own docstrings, which already invite exactly this consolidation at near-zero risk. Item 1
now gets an independent verdict on its own merits, not folded into items 2/3's reasoning.

**Revised again after adversarial review pass 2:** ground truth shifted mid-review — Edge Case
Hunter found `steward:S-9.1` (Story 13.4's cross-station dependency) landed 2026-08-11, after
this story's own `baseline_revision`, making the pass-1 draft's "no committed date" premise
stale. Blind Hunter separately found a self-contradiction (the closing note called the
SQLite-vs-fcntl question "open" when Story 13.1's own body two paragraphs above says it was
resolved) and a severity miscount (13.1's actual pass-7 deferred tally is one medium + one low,
not "two low"). None of this flips a verdict — if anything, S-9.1 landing makes items 2/3's SKIP
calls *more* defensible (the interim window is now short and bounded, not open-ended) — but the
stale/wrong claims had to be corrected regardless, per this story's own AC 2.

**Revised again after adversarial review pass 4:** Blind Hunter found item 3's write-path list
wrongly included `state.py` (scoped to deck-bridge commands only, never touched by this
automation); found item 3's safety claim omitted a real residual gap that IS in a hook-relevant
path (`notices._write_markdown`'s non-atomic write, `deferred-work.md`'s pass-5 entry); found the
severity citation depended on a gitignored file (Story 13.1's spec, now promoted to
`planning-artifacts/specs/` -- Task 3 -- to close this durably rather than reword around it);
found "duplicate mechanism" over-flattened a local git hook against a server-side webhook; found
the closing note's "CLOSED: yes" re-asserted a conflation pass 1 fixed elsewhere in this same
entry; found an arithmetic slip ("three different dispositions" when there are two: BUILD, SKIP);
found the per-item cost paragraphs didn't say why 13.5/13.6 aren't the relevant comparison; and
found this entry silently narrows the research doc's five named steps to the three `epics.md`
binds it to, without saying so. None flip a verdict; all improve precision or completeness.

**Scope note:** the technical research doc (§4.2) names five serverless-intermediate steps in
priority order; `epics.md`'s own Constraint 2 binds this story to only the first three (`herald
snapshot`, telemetry-derived defaults, hook-triggered CLI). The other two -- `herald notice
reindex` and hosting the static bundle on GitHub Pages -- are real research-doc suggestions but
outside this story's binding scope; their absence here is a scope boundary, not an oversight.

**Verdict: two dispositions across three items, not one blanket call -- each judged on its own
merits:**

1. **`herald snapshot` -- BUILD**, tracked as deferred-work (not executed as code in this
   Effort:S decision story; see the deferred-work entry below). It would close a real,
   currently-live risk in the CURRENTLY-SHIPPED v1 dashboard (research risk #1 of 6, staleness
   with no freshness signal) using an extension point Epics 9/10 already built and explicitly
   deferred to "a later story" -- this is overdue Epics-9/10 follow-up, not new Epic 13 scope, so
   it does not need insertion into Epic 13's own numbering and is not gated on LB-1/2/3 landing.
2. **Telemetry-derived defaults -- SKIP.** Bounded value regardless of timing: reduces keystrokes
   on an already-working, already-accepted 4-flag CLI flow -- a UX nicety, not a correctness or
   automation-completeness gap. Story 13.4 (Effort: L per `epics.md`, now clear to dispatch once
   13.3 completes -- `steward:S-9.1` landed 2026-08-11) is expected to substantially reduce or
   eliminate this need once its own still-open first AC (which CI events trigger it, and what
   payload they carry) is resolved; building a partial auto-fill now duplicates logic the
   eventual webhook handler may own, for a benefit smaller than 13.3+13.4's combined committed
   cost (Effort L, L -- 13.5/13.6 don't functionally overlap with this item's purpose, so they
   aren't the relevant comparison, though all four sizes are cited together in the Net section).
3. **Locking + hook-triggered CLI -- SKIP.** Story 13.1's lock (done) closes the core lost-update
   race for the write paths a hook would exercise (`progress`/`claims`/`notices` read-modify-
   write -- not `state`, which is scoped to deck-bridge commands only), proven by concurrency
   tests in `tests/test_locking.py`, `tests/test_progress.py`, `tests/test_claims.py`,
   `tests/test_notices.py` (tracked, merged at this story's own `baseline_revision`). Its two
   pass-7 deferred items (one medium, one low; independently verifiable in the now-promoted
   `spec-13-1-*.md`) are both in `claims.py`'s `revalidate`/`revalidate_all` path, not the
   `progress`/`success`/`notice` write paths a hook-triggered CLI would call, so they don't bear
   on this trigger's safety. One separate, real residual DOES sit in a hook-relevant path:
   `notices._write_markdown` is still a non-atomic `write_text`, so a concurrent reader can still
   observe a torn file even after this lock -- the lock closes writer-vs-writer races, not
   reader-vs-writer atomicity, and this safety claim is scoped to the former only. Safe enough to
   build for that narrower purpose, but not worth building: as a CI job it would be a
   straightforward duplicate of Story 13.4's webhook trigger surface; as a local git hook it is
   narrower (opt-in, single-operator) but still a second maintained path that doesn't cover the
   multi-operator/CI case 13.4 exists for. Either reading needs its own eventual deprecation once
   13.4 (Effort: L) ships. This cost is sharper now, not softer: with `steward:S-9.1` landed, the
   interim window either reading would fill is bounded, not open-ended -- Story 13.3+13.4
   combined (Effort L, L; 13.5/13.6 aren't the relevant comparison here either) -- a throwaway
   duplicate trigger buys even less than when this was first drafted.

**Net:** the operator's 2026-08-09 Steward-hosting adoption and 2026-08-10 funding go-ahead
already settled *whether* to fund Epic 13 -- that reprioritizes but does not itself answer each
intermediate's standalone value, so each item was judged on its own cost/value against Epic 13's
committed LB-1/2/3 work (`epics.md` Effort sizes: 13.3 L, 13.4 L, 13.5 M, 13.6 M). Items 2 and 3
don't clear that bar; item 1 does, as non-Epic-13-gated follow-up. No Epic 13 stories inserted or
renumbered; Epic 13 proceeds to Story 13.3 next, unmodified.

**Exact entries to append** (frontmatter `updated:` becomes `2026-08-11T09:17`):

`.memlog.md` (two new bullets, at file end):
```
- (decision) SERVERLESS INTERMEDIATES RESOLVED (Story 13.2, 2026-08-11): the Spec's three named
  cheaper steps are judged individually, not with one blanket verdict -- two dispositions across
  three items: (1) `herald snapshot` -- BUILD, tracked as a deferred-work entry (not gated on
  Epic 13; see deferred-work.md), not skipped. (2) Telemetry-derived defaults for `herald
  progress --update` -- SKIP. (3) Locking + hook-triggered CLI invocation -- SKIP. Current-state
  confirmed directly against the shipped code, not assumed from the 2026-08-08 research doc:
  none of the three exist today -- `herald snapshot` as a command, the other two as
  CLI/automation behaviors. Scope note: the research doc names five serverless-intermediate steps
  in priority order; epics.md's own Constraint 2 binds this story to only these first three --
  `herald notice reindex` and hosting the static bundle are real research-doc suggestions but
  outside this story's binding scope, not an oversight.

  (1) `herald snapshot` BUILD: export_web_snapshot.py's own docstring already designs itself as
  the shared exporter and explicitly anticipates "a future Epic 8/10 snapshot adds a sibling
  export_*_snapshot function here rather than a duplicate script"; export_notices_snapshot.py's
  docstring says a later story can fold all three in "once the shape each Moment needs is
  settled" -- that precondition is now met (all three exporters exist and ship stable output).
  This would close a real, currently-live risk (research risk #1 of 6, staleness with no
  freshness signal -- no JSON record anywhere carries a generated_at stamp; only
  sync-progress.mjs is wired into npm hooks) in the CURRENTLY-SHIPPED v1 dashboard, independent
  of whether/when the live backend (LB-1/2/3) lands -- so it is Epics 9/10 follow-up, not new
  Epic 13 scope, and does not need insertion into Epic 13's own story numbering. Filed as a
  deferred-work entry for pickup, rather than built inside this Effort:S decision-only story.

  (2) Telemetry-derived defaults SKIP: bounded value regardless of timing -- reduces keystrokes
  on an already-working, already-accepted 4-flag CLI flow, not a correctness or automation-
  completeness gap. Story 13.4 (Effort: L per epics.md, now clear to dispatch once 13.3 completes
  -- steward:S-9.1 landed 2026-08-11) is expected to substantially reduce or eliminate this need
  once its own still-open first AC (which CI events trigger it, what payload they carry) is
  resolved; building a partial auto-fill now duplicates logic the eventual webhook handler may
  own, for a benefit smaller than 13.3+13.4's combined committed cost (Effort L, L -- 13.5/13.6
  don't functionally overlap with this item, so aren't the relevant comparison).

  (3) Hook-triggered CLI SKIP: Story 13.1's lock (done) closes the core lost-update race for the
  write paths a hook would exercise (progress/claims/notices read-modify-write -- not state,
  which is scoped to deck-bridge commands only), proven by concurrency tests in
  tests/test_locking.py, tests/test_progress.py, tests/test_claims.py, tests/test_notices.py
  (tracked, merged at this story's baseline_revision). Its two pass-7 deferred items (one medium,
  one low; independently verifiable in the now-promoted spec-13-1-*.md) are both in claims.py's
  revalidate/revalidate_all path, not the progress/success/notice write paths a hook-triggered
  CLI would call, so they don't bear on this trigger's safety. One separate, real residual DOES
  sit in a hook-relevant path: notices._write_markdown is still a non-atomic write_text, so a
  concurrent reader can still observe a torn file even after this lock -- the lock closes
  writer-vs-writer races, not reader-vs-writer atomicity, and this safety claim is scoped to the
  former only. Safe enough to build for that narrower purpose, but not worth building: as a CI
  job it would be a straightforward duplicate of Story 13.4's webhook trigger surface; as a local
  git hook it is narrower (opt-in, single-operator) but still a second maintained path that
  doesn't cover the multi-operator/CI case 13.4 exists for. Either reading needs its own eventual
  deprecation once 13.4 (Effort: L) ships. This cost is sharper now, not softer: with
  steward:S-9.1 landed, the interim window either reading would fill is bounded, not open-ended
  -- Story 13.3+13.4 combined (Effort L, L; 13.5/13.6 aren't the relevant comparison here either)
  -- a throwaway duplicate trigger buys even less than when this was first drafted.

  Net: the operator's 2026-08-09 Steward-hosting adoption and 2026-08-10 funding go-ahead already
  settled WHETHER to fund Epic 13; that reprioritizes but does not itself answer each
  intermediate's standalone value, so each item was judged on its own cost/value against Epic
  13's committed LB-1/2/3 work (epics.md Effort sizes: 13.3 L, 13.4 L, 13.5 M, 13.6 M). Items (2)
  and (3) don't clear that bar; item (1) does, as non-Epic-13-gated follow-up. No Epic 13 stories
  inserted or renumbered; Epic 13 proceeds to Story 13.3 next, unmodified.
- (note) CLOSING two threads. First, a stale open-question clause: the "(question)" bullet's "is
  there real pull for this at all... zero production-usage evidence" clause was already answered
  by the operator's 2026-08-10 go (epics.md Epic 13 preamble: "Operator go: 2026-08-10...
  answering the Spec's own leading question"), left unmarked here until now -- CLOSED (for
  funding-readiness purposes, matching epics.md's own framing -- not independent evidence of
  operator demand for the automated-feel itself, which remains genuinely unmeasured). The same
  bullet's SQLite-vs-fcntl clause is ALSO closed, not open: Story 13.1 (done) answered it as its
  own first AC -- per-file advisory locking (fcntl/msvcrt), not SQLite, recorded in locking.py
  and DW-1-4-2's closure. Only the "what triggers the webhook, with what authentication" clause
  remains genuinely open, tracked as Story 13.4's own first AC. Second, ground truth as of
  2026-08-11 09:17: steward:S-9.1 (Story 13.4's cross-station dependency) is DONE, not backlog --
  landed after this story's own baseline_revision, confirmed via pyforge-steward's own
  implementation-artifacts/sprint-status.yaml. Its TRACKED twin,
  pyforge-steward/planning-artifacts/sprint-status-ledger.yaml, still reads 9-1: backlog as of
  its last regeneration (2026-08-10, before the landing) -- stale, the one artifact a reader
  confined to this repo without cross-project access can actually check, so don't be misled by
  it; the implementation-artifacts source is the current one. Herald's own sprint-status.yaml
  also still shows 13-4: blocked as of this writing; both stale lines should be corrected
  whenever Story 13.3/13.4 is next picked up (out of scope here -- this story's Never-list
  forbids editing sprint-status.yaml).
```

`deferred-work.md` (new entry, appended at file end):
```
- source_spec: `_bmad-output/implementation-artifacts/spec-13-2-the-serverless-intermediate-decision-recorded.md`
  summary: `herald snapshot` -- a single command consolidating the three currently-separate,
  mostly-unwired dashboard exporters (`scripts/export_web_snapshot.py`,
  `scripts/export_notices_snapshot.py`, `web/scripts/sync-progress.mjs`) into one, stamping
  `generated_at` on each -- should be built as near-term follow-up, not skipped: it would close
  the shipped v1's real "three hand-cranked snapshot hops" staleness risk (technical research
  risk #1 of 6). Worth prioritizing over routine low-priority ledger sweeps -- the fix candidate
  below is small and fully scoped, not exploratory.
  evidence: `export_web_snapshot.py`'s own docstring (lines 3-8) already designs itself as the
  shared exporter and explicitly anticipates "a future Epic 8/10 snapshot adds a sibling
  export_*_snapshot function here rather than a duplicate script"; `export_notices_snapshot.py`'s
  docstring likewise says "a later story can fold all three into one generic... script once the
  shape each Moment needs is settled" -- deferred there deliberately (Simplicity First,
  YAGNI-until-second-confirmed-use), not because of architectural uncertainty. That uncertainty
  is now resolved: all three exporters exist, ship working output, and their shapes are
  individually stable (confirmed 2026-08-11) -- the deferred precondition ("once the shape... is
  settled") is met. This work is independent of Epic 13's DB/webhook/cron scope (LB-1/2/3): it
  would close a real risk in the CURRENTLY-SHIPPED v1 dashboard regardless of whether or when the
  live backend lands, so it is not gated on any Epic 13 story and does not need insertion into
  Epic 13's own numbering -- it is overdue Epics 9/10 follow-up (whose own Stories 9.4/10.5
  shipped with a docstring explicitly deferring exactly this consolidation "to a later story"),
  not a claim that Epic 9 or 10 is reopened. Currently only `web/scripts/sync-progress.mjs` is
  wired into npm `predev`/`prebuild` (`web/package.json:8-11`); no snapshot JSON anywhere carries
  a `generated_at` field. Fix candidate: add `export_progress_snapshot`/`export_notices_snapshot`
  functions to `export_web_snapshot.py` alongside the existing `export_success_snapshot`, stamp
  `generated_at` in each, expose all three via one `herald snapshot` CLI subcommand (`cli.py`),
  and decide whether it supersedes or complements `sync-progress.mjs`'s npm-hook wiring.
```

`deferred-work.md` (SECOND new entry, appended immediately after the first, at file end):
```
- source_spec: `_bmad-output/implementation-artifacts/spec-13-2-the-serverless-intermediate-decision-recorded.md`
  summary: `deferred-work.md` itself is written via an unlocked read-modify-write across a Tier-3
  cross-worktree backlink -- the same lost-update race class Story 13.1 fixed for Herald's own
  `state`/`progress`/`claims`/`notices` stores, here in the BMAD governance tooling instead. Two
  concurrent `pyforge-herald` bmad-loop worktrees both appending to this file could silently drop
  one entry. Pre-existing, not introduced by this story; surfaced incidentally by review pass 3's
  Edge Case Hunter and re-confirmed still applicable by pass 5's.
  evidence: `deferred-work.md` resolves through this worktree's Tier-3 backlink symlink to a
  single shared file in the primary `local-recipes` checkout (`readlink -f` confirms), so it is
  NOT worktree-local the way tracked git files are -- every `bmad-loop` worktree for this project
  writing to it shares the identical file. Appends here (this story's own two entries included)
  are a plain read-append-write with no lock, sidecar, or advisory-file guard of any kind -- the
  exact pattern `locking.py` (Story 13.1) was built to replace for Herald's own stores. Currently
  latent (no second concurrent `pyforge-herald` worktree active at authoring time), not active.
  Fix candidate: extend `locking.locked()` (already stdlib-only, cross-platform,
  `fcntl`/`msvcrt`) to guard the Tier-3 backlink write path generically -- likely a bmad-loop
  tooling change (the backlink mechanism itself), not something scoped to any one project's
  `deferred-work.md`, since every project in this fleet's `_bmad-output/projects/*/` shares the
  identical pattern.
```

`planning-artifacts/specs/README.md` (edit the existing status line):
```
**Status (2026-08-08):** all 47 stories (Epics 1-12) have a spec here — no
promotion gap.
```
becomes:
```
**Status (2026-08-11):** all 48 stories through Epic 13's first promoted spec
(13.1) have a spec here — no promotion gap.
```

## Verification

**Manual checks (no CLI/test applies to this memlog/deferred-work/spec-promotion change):**
- `.memlog.md` frontmatter still parses as valid YAML after the edit (`updated:` bumped, no
  stray unquoted `:`).
- Exactly three *tracked* files changed (`git status` / `git diff --stat`): `.memlog.md` modified,
  `spec-13-1-the-state-layer-survives-a-second-writer.md` newly added, `README.md` (in
  `planning-artifacts/specs/`) modified; `deferred-work.md` is gitignored, so it will show only
  in a non-git listing / direct read, not in `git status`.
- `diff` between the promoted `spec-13-1-*.md` and its `implementation-artifacts` original shows
  no differences.
- The `.memlog.md` entry names all three steps and states an explicit, differentiated verdict
  for each; the `(note)` bullet closes the stale open-question clause and names both the current
  and the stale-tracked source for `steward:S-9.1`'s status.
- `deferred-work.md` contains two new entries: `herald snapshot` (names a concrete fix candidate,
  cites both scripts' docstrings) and the file's own unlocked-write race (names a fix candidate
  scoped correctly to the shared bmad-loop tooling, not this project alone).
- `planning-artifacts/specs/README.md`'s status line matches the directory's actual count.

## Auto Run Result

Status: done (6 review passes; 5 bad_spec loopbacks, converged on pass 6 with zero findings from
both reviewers).

**Summary:** Story 13.2 records Epic 13's required serverless-intermediate decision. Of the
Spec's three named cheaper alternatives to the full live backend (`herald snapshot`,
telemetry-derived defaults, locking+hook-triggered CLI), each got an independently-reasoned
verdict rather than one blanket call: `herald snapshot` is BUILD (tracked as deferred-work, not
Epic 13 scope -- overdue Epics 9/10 follow-up an extension point in the shipped code already
anticipates), the other two are SKIP (each superseded in kind or duplicated by Story 13.4's
webhook, which the concurrency-lock landing in Story 13.1 plus `steward:S-9.1`'s landing this
session now leaves clear to dispatch once Story 13.3 completes). No Epic 13 stories inserted or
renumbered; Story 13.3 is unblocked to dispatch next.

**Files changed:**
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-live-backend/.memlog.md`
  -- appended the `(decision)` verdict entry and a closing `(note)` entry; bumped `updated:`
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/README.md` -- corrected the
  promoted-spec count/status line (this story's own promotion made it stale)
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-13-1-the-state-layer-survives-a-second-writer.md`
  (new) -- promoted Story 13.1's spec from gitignored `implementation-artifacts/` to its durable
  tracked home, closing a pre-existing gap (13.1 was the one un-promoted spec among Stories
  1.1-13.1) and making this story's own citations of it independently verifiable
- `_bmad-output/implementation-artifacts/deferred-work.md` (gitignored) -- two new entries:
  `herald snapshot`'s build case, and a `defer` for `deferred-work.md`'s own unlocked
  cross-worktree write race (pre-existing, surfaced incidentally, not this story's to fix)

**Review findings breakdown across all passes:** bad_spec 22 total (pass 1: 6, pass 2: 6, pass 3:
1, pass 4: 8, pass 5: 1) -- all repaired via spec amendment + re-derivation, never a revert to
the underlying verdicts (item 1 flipped SKIP->BUILD once in pass 1 on factual grounds and never
moved again); patch 3 (Code Map count, README staleness, a stale-question closing note); defer 1
(`deferred-work.md`'s own concurrency gap); reject 6 (restated/settled/out-of-scope findings).
Passes 5 and 6 (2 of 6 total review-agent-pairs) found zero issues.

**Follow-up review recommendation: false.** Two consecutive passes (5's Blind Hunter, then both
of pass 6's reviewers) independently re-verified the highest-stakes claims against the live
codebase and found nothing -- a stronger convergence signal than volume-based heuristics alone.
The repair history is real (5 loopbacks) but each pass fixed genuinely distinct, narrowing-in-
severity issues (6 -> 6 -> 1 -> 8 -> 1 -> 0 -> 0 across the two-reviewer passes), not the same
issue recurring unresolved, and no verdict has changed since pass 1's single flip.

**Verification performed:** manual inspection only (a decision/memlog-record story has no
CLI/test surface) -- YAML frontmatter parse checks after every edit, `git diff --stat` /
`git status --porcelain` file-count checks after every pass, `md5sum`/`diff` byte-identity
checks on the promoted spec, and direct-file greps confirming every factual claim (docstring
quotes, line numbers, Effort sizes, cross-project sprint-status values) against the live repo,
independently repeated by 6 separate reviewer invocations across 3 passes.

**Residual risks:** `deferred-work.md`'s own unlocked read-modify-write race (now formally
deferred, not fixed -- a bmad-loop tooling-level gap affecting every project in this fleet, out
of this story's surface); Herald's own `sprint-status.yaml` `13-4: blocked` line and
`pyforge-steward`'s tracked `sprint-status-ledger.yaml` `9-1: backlog` line are both stale as of
this writing (both explicitly out of scope per this story's Never-list) and should be corrected
whenever Story 13.3/13.4 is next picked up.
