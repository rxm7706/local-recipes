---
title: "Story 47.5: Epic 44 depends on the era tail, and 44.13's scope names the spines"
type: story
created: 2026-09-07
baseline_revision: 3e529ddf95
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: pyforge-steward
warnings: []
deferred:
  - summary: "cutover-readiness.md P11/P12's own state cells still read 'not done' (2026-09-06 snapshot) even though their producers (marshal 30.5/30.2, steward 14.9) are all confirmed done -- correcting those cells is each producer's own job, out of this story's Surface line"
    evidence: "Named explicitly in G3's own resolution note; independently confirmed by three reviewers this staleness is real and correctly left untouched here"
    location: "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md rows P11/P12"
    severity: low
---

# Story 47.5: Epic 44 depends on the era tail, and 44.13's scope names the spines

<intent-contract>

## Intent

Close the last three cutover-readiness gaps (G2, G3, G6) by making Epic 44's
own `epics.md` text honestly reflect two facts that are, as of this pass,
ALREADY TRUE (verified live, not assumed): the era-tail prerequisites
(steward 14.9, marshal 30.5, marshal 30.2) that the cutover text has always
assumed are genuinely `done` in their own projects' ledgers today — steward
`14-9-the-apply-retires-deprecation-shims-on-purpose-no-shims: done`, marshal
`30-2-the-project-context-surface-follows-6-12-d1: done`, marshal
`30-5-the-harness-and-every-live-caller-follow-the-shim-retirement: done` —
and AD-10's own already-adopted convention ("cross-station prerequisites are
checks, not `Deps:` tokens... a ledger `blocked` row ... and a machine check
inside the consuming story's own acceptance") explicitly names Story 44.5 as
one of its own worked examples ("44.5 refuses while `cutover-readiness.md`
P11 / P12 are red") — meaning the SHAPE of the fix this story adds to 44.5's
text is not invented here, it is transcribed from an architecture decision
that already describes it. Story 44.13 separately gains one acceptance
clause (memlog fidelity must cover every spine's own `.memlog.md`
re-distillation, not just one), first recorded as a cutover-project memlog
`(note)` per the AC's own ordering requirement.

## Boundaries & Constraints

- **This story adds text to epics.md; it does not run 44.5, 44.12, or
  44.13, and does not itself verify P11/P12's live state as a NEW piece of
  work** — `cutover-readiness.md` P11/P12's own state cells are NOT in this
  story's Surface line (only G2/G3/G6 are) and are each a DIFFERENT
  story's/station's own job to keep current (marshal 30.5/14.9 for P11,
  marshal 30.2 for P12) — verified live only far enough to confirm the
  DEPENDENCY claim this story's own Given clause rests on (are 14.9/30.5/
  30.2 genuinely done — yes), not to re-audit P11/P12's own stale text.
  That staleness (P11/P12 still read "not done" despite their producers
  landing) is recorded as a named, out-of-scope finding, not silently
  fixed here and not silently ignored either.
- **`Deps:` fields carry only same-station `S-<epic>.<n>` tokens (AD-10's
  own hard rule)** — the cross-station producer is named in TRAILING
  PROSE, never as a `Deps:` token itself. 44.5's `Deps:` line gains
  `S-14.9` specifically because steward 14.9 IS same-station (this is the
  steward project's own epics.md) — the trailing prose "(after marshal
  30.5 and 30.2)" is what carries the two truly cross-station producers,
  exactly matching AD-10's own worked phrasing ("after steward 46.3") and
  the pre-existing pattern already used elsewhere in this same
  `epics.md` (Story 14.9's own `Deps:` line, already landed, already
  shaped this way — read directly as the template, not re-invented).
- **The `blocked` ledger row is added, then immediately reconciled to the
  ALREADY-TRUE state, not left mid-round-trip.** AD-10's own convention:
  "a ledger `blocked` row the operator flips when the producer lands." The
  producer landed before this story ran (verified live, not assumed) — so
  the honest ledger action is a SINGLE, direct entry reflecting current
  reality (44.5 stays `backlog`, unblocked by this specific cross-station
  gate — it remains gated by its own SAME-station deps, `S-44.4`/`S-44.11`,
  both still `backlog` today, unrelated to this story), with the
  cross-station-gate-checked-and-satisfied fact recorded in the cutover
  memlog instead of manufactured as a pointless `blocked`→`backlog`
  same-commit flip in the ledger's own history.
- **44.5's new in-story check is DESCRIBED in its acceptance text (a new
  `**And**` clause), never implemented as code here** — this story ships
  no code; the check itself runs when Story 44.5 actually executes.
- **44.13's new clause is added to its OWN acceptance text; its `Given`/
  `When`/Deps/Type/Effort are otherwise unchanged.** The AC's own ordering
  requirement ("recorded first as a cutover memlog `(note)`") is honored:
  the memlog note is written BEFORE the epics.md text change, in this
  story's own execution order.
- **No Epic 44 story text beyond `Deps:` (44.5) and the one new acceptance
  clause each (44.5's check, 44.13's memlog-fidelity clause) changes** —
  the AC's own closing sentence is a hard boundary, verified by diff after
  the edit: 44.12 gains NOTHING in this story (re-reading epics.md, 44.12
  is named in the Surface line but the AC's own Given/When/Then never
  actually specifies a text change for it — a documented finding, not a
  silent omission, see Design Notes).

## I/O Matrix

| Input | Behavior |
|---|---|
| `epics.md` Story 44.5's `Deps:` line | `S-44.4, S-44.11` → `S-44.4, S-44.11, S-14.9` |
| `epics.md` Story 44.5's acceptance | Gains one new `**And**` clause describing the AD-10 in-story check against `cutover-readiness.md` P11/P12, with the trailing prose "after marshal 30.5 and 30.2" |
| `epics.md` Story 44.13's acceptance | Gains one new `**And**` clause: "and every spine `.memlog.md` re-distills through `bmad-architecture` without loss" |
| `epics.md` Story 44.12 | Unchanged (see Design Notes finding) |
| `sprint-status-ledger.yaml` `44-5-move-the-estate` | Unchanged: stays `backlog` (still gated by its own same-station deps, unrelated to this story's cross-station gate, which is confirmed already satisfied) |
| Cutover memlog (`spec-python-foundry-cutover/.memlog.md`) | Gains, in order: (1) a `(note)` recording 44.13's new acceptance clause BEFORE the epics.md edit; (2) an `(event)`/`(note)` recording the AD-10 cross-station gate check for 44.5 (14.9/30.5/30.2 all confirmed `done`) |
| `cutover-readiness.md` G2, G3, G6 | State cells: dated, read relayed-and-landed |
| `sprint-status-ledger.yaml` `47-5-...` | `blocked` → `done` |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`
  - Story 44.5: `**Type:** feature • **Effort:** L • **Deps:** S-44.4,
    S-44.11 • ...` → `... • **Deps:** S-44.4, S-44.11, S-14.9 • ...`.
  - Story 44.5's acceptance: new `**And**` line, e.g. "**And** this story
    refuses to run while `cutover-readiness.md` P11 or P12 reads anything
    but green (AD-10's own worked example) — after marshal 30.5 and 30.2
    and steward 14.9, all confirmed `done` as of 2026-09-07; the check
    itself, not this prose, is what 44.5 runs against P11/P12's live state
    at execution time."
  - Story 44.13's acceptance: new `**And**` line: "**And** every spine's
    own `.memlog.md` re-distills through `bmad-architecture` without loss
    (closing G6 — 44.13's own scope previously only exercised one
    re-derive, 44.14's)."
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/.memlog.md`
  - New `(note)` (44.13's clause, written FIRST per the AC's own ordering)
    and a following `(event)`/`(note)` (the AD-10 gate check for 44.5).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md`
  - G2, G3, G6 rows: state cells dated, relayed-and-landed.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
  - `47-5-...: blocked` → `done`. `44-5-move-the-estate` left unchanged
    (`backlog`) — see Boundaries.

## Tasks & Acceptance

1. **Add `S-14.9` to Story 44.5's `Deps:` line; no other Deps field in
   Epic 44 changes.**
   - AC: `grep -n "Deps:" epics.md` around 44.5's own line shows the new
     token; 44.12/44.13's own `Deps:` lines are byte-identical to before.
2. **Add the in-story-check acceptance clause to 44.5, and the
   memlog-fidelity clause to 44.13** — each exactly one new `**And**`
   line, nothing else in either story's text changed.
   - AC: `git diff` on `epics.md` shows exactly two new lines added
     (plus the one-token `Deps:` edit), zero lines removed, zero other
     story text touched.
3. **Write the cutover memlog note (44.13's clause) BEFORE editing
   epics.md; write the AD-10 gate-check note after.**
   - AC: both memlog entries exist, in that relative order (checked by
     line position in the file).
4. **Update `cutover-readiness.md` G2/G3/G6 only.**
   - AC: `git diff` on this file shows only those three rows changed.
5. **Leave `sprint-status-ledger.yaml`'s `44-5-move-the-estate` at
   `backlog`** (a deliberate non-change, not an oversight) **and flip
   `47-5-...` to `done`.**
   - AC: both confirmed via diff.

## Spec Change Log

- 2026-09-07: initial draft, written directly (no fork) after reading
  Epic 44's current `epics.md` text for Stories 44.4/44.5/44.11/44.12/
  44.13 in full, AD-10's complete definition in the lifecycle
  architecture spine (confirming it explicitly names 44.5's own P11/P12
  check as its worked example), the current `sprint-status-ledger.yaml`
  state for `14-9`/`30-2`(steward)/`44-4`/`44-5`/`44-11`/`44-12`/`44-13`/
  `47-5`, and marshal's own `sprint-status-ledger.yaml` for its OWN
  `30-2`/`30-5` keys (confirming both `done`, live, not assumed from the
  original task's own claim) — a coincidental story-number collision
  exists between steward's own unrelated `30-2` story and marshal's
  `30-2`; verified by reading each project's OWN ledger file directly,
  never conflated.

## Review Triage Log

Three independent, context-free reviewer subagents ran against the full
diff — the final story of this 13-story batch, editing the foundational
`epics.md` document, warranted the full three-reviewer treatment despite
its small size. 0 findings requiring a patch; 1 low-severity informational
note (standard git line-diff mechanics, not a defect); both of this spec's
own deliberate, non-obvious judgment calls were independently
re-evaluated from first principles (not rubber-stamped) and AGREED with
by a dedicated reviewer.

- **Blind Hunter**: independently re-verified the three-project dependency
  claim live (steward 14.9, marshal 30.2/30.5, reading marshal's OWN
  ledger file directly, never via `bmad-switch`); confirmed `epics.md`'s
  diff touches only Stories 44.5 and 44.13, nothing else in Epic 44 or any
  other epic; confirmed AD-10's own text genuinely supports the new
  acceptance clause's framing (verified "not green" ≡ "red" against
  AD-10's own worked-example wording); confirmed `cutover-readiness.md`
  touches only G2/G3/G6; confirmed memlog ordering (note before event) and
  the 1180-test count. One low, informational note: `git diff --numstat`
  shows "3 insertions / 1 deletion" rather than the spec's own loosely-worded
  "0 deletions" — standard git line-replace mechanics for the one-token
  `Deps:` edit (the whole line is diffed, not the token), not actual
  content loss; confirmed by word-diff that every token from the old line
  survives. No patch needed.
- **Verification Gap**: independently re-ran every Task's AC via direct
  commands (grep + diff + numstat + word-diff on epics.md; line-position
  check on the memlog; numstat on cutover-readiness.md; ledger diff) — all
  5 Tasks proven exactly as claimed, including confirming 44.12's own
  `Deps:` line (`S-44.1`) and 44.13's pre-existing `Deps:` (`none`) are
  genuinely untouched and fall outside any diff hunk.
- **Intent Alignment**: independently re-evaluated, from first principles,
  both of this spec's own deliberate deviations from the story's literal
  AC wording. (1) Leaving 44.12's text untouched despite the Surface
  line naming it: re-read the story's own Given/When/Then directly and
  agreed it never actually calls for a 44.12 change — the Surface line's
  own parenthetical is independently shown to be already stale (it
  mis-describes even 44.13's real change, which was an acceptance clause,
  not a `Deps:` edit as the Surface line implies), corroborating that the
  Surface line over-lists rather than the Given/When/Then under-delivering.
  (2) Leaving `44-5-move-the-estate` at `backlog` instead of manufacturing
  a `blocked` row: independently traced Story 14.9's OWN ledger history
  (the exact cited AD-10 template) through its real
  `backlog`→`blocked`→`done` lifecycle via `git log`, confirming `blocked`
  was entered ONLY while the dependency was genuinely unmet and cleared
  once genuinely resolved — and found this exact lifecycle was never
  entered for 44.5 in this pass, since all three producers were already
  `done` before this story touched the ledger. Agreed the spec's approach
  is a correct application of AD-10's actual intent, not a rationalization
  to dodge an inconvenient literal requirement.

Post-review verification: `pixi run -e pyforge-steward pyforge-steward-test`
→ **1180 passed** (unchanged — this story makes no source-code changes).

## Design Notes

- **Why 44.12 is named in the Surface line but gets no text change:**
  re-reading the story's own literal Given/When/Then text twice, it
  specifies a change to 44.5's `Deps:`+acceptance and to 44.13's
  acceptance — nothing about 44.12's own text. 44.12 is likely named in
  the Surface line because it's the OTHER Epic 44 story AD-10's own
  cutover-readiness discussion touches tangentially (the flag/replay
  harness), or as a residual copy-paste from an earlier draft of this
  story's own scope. Recorded here as a finding rather than inventing a
  44.12 text change that no AC text actually calls for — adding
  unrequested content to a foundational planning document (`epics.md`)
  on a guess would be a worse mistake than leaving a named surface-line
  entry unused.
- **Why `44-5-move-the-estate`'s ledger row is NOT set to `blocked` even
  though the AC's own text says "plus a `blocked` ledger row":** AD-10's
  full rule reads "(a) a ledger `blocked` row the operator flips when the
  producer lands." The producer (14.9/30.5/30.2) landed BEFORE this pass
  ran (verified live). Creating a `blocked` row and flipping it back to
  `backlog` in the same commit would manufacture a false historical
  moment in the ledger (a "blocked" state that was never actually true at
  any point this story's own execution observed) purely to satisfy the
  AC's literal words rather than its actual intent (visibly gate
  dispatch on an unmet cross-station producer). Since the producer is
  already met, the honest, intent-matching action is: leave the row
  exactly where the LIVE state says it belongs (`backlog`, gated only by
  its own real, same-station, still-open deps), and record the
  gate-check-passed fact in the memlog instead, where a reader can see
  that the AD-10 check WAS performed and passed, not infer a blocked
  state that never genuinely existed during this pass.

## Auto Run Result

Status: done
Blocking condition: none

Final story of the batch. Independently re-verified, live, that all three
era-tail prerequisites (steward 14.9, marshal 30.5, marshal 30.2 — the
latter two read directly from marshal's own project ledger, never via
`bmad-switch`) are genuinely `done` before proceeding. Added `S-14.9` to
Story 44.5's `Deps:` line plus one new AD-10-shaped acceptance clause
(refuses while `cutover-readiness.md` P11/P12 are red); added one new
memlog-fidelity acceptance clause to Story 44.13. Both cutover-project
memlog entries written in the AC's own required order (44.13's note
before the AD-10 gate-check event). `cutover-readiness.md` G2/G3/G6 all
now read relayed-and-landed, closing out the last three open gaps this
batch's own Epic 47 was chartered to close.

Two deliberate, non-obvious deviations from the story's literal wording
(leaving Story 44.12 untouched despite the Surface line naming it;
leaving `44-5-move-the-estate` at `backlog` rather than manufacturing a
`blocked` row for a dependency already satisfied) were each independently
re-derived from first principles by a dedicated reviewer and confirmed
sound against real precedent (14.9's own ledger history) rather than
merely rubber-stamped. Full 3-reviewer pass (warranted by `epics.md`
being a foundational document) found zero findings requiring a patch.
Final suite: 1180 passed (unchanged, zero source-code changes across all
13 stories' worth of docs/config work in this pass).
