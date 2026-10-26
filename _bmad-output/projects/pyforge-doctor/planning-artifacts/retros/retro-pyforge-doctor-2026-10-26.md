---
title: 'pyforge-doctor — Retrospective (Epic 50: every requirement arrow resolves to a defined capability)'
project: pyforge-doctor
epic: 50
date: '2026-10-26'
created: '2026-10-26'
updated: '2026-10-26'
verdict: accepted-with-open-items
criteria: declared
headless: true
scope: 'Epic 50, Story 50.1 (done at retro time), built and reviewed inside the one-PR "every requirement derives from a capability" effort of 2026-10-26 (branch claude/chain-fr-cap-only-eb5b87, base main 92fa3edbbd). Written as the reconciler half of chain currency: the detector code is newer than the previous doctor retro (2026-10-04), so this retro runs in the same PR.'
evidence:
  - 'git log 92fa3edbbd..HEAD (nine commits; the detector half in ffa1715a08 and b59245a8c8, the chain in dd27387817, the amendments in c4292d3501, 1daf6503ce, a9a6f38fe6, 226459ff11)'
  - '.claude/skills/bmad-retrospective/scripts/git_evidence.py --range 92fa3edbbd..HEAD --stories 50.1 (9 commits, 101 files, 0 merges)'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-50-1-fr-without-cap-resolves-every-arrow-against-a-defined-capability-and-names-a-counted-run.md (intent, ACs, I/O matrix, Review Triage Log)'
  - 'spec-pyforge-doctor/SPEC.md CAP-92 and CAP-93; .memlog.md entries of 2026-10-26 (the ruling, the two decisions, the review-round decision, the render and validate events)'
  - 'the two independent review reports of 2026-10-26 (planning tables: FAIL then re-reviewed; detector diff: FAIL, 2 blockers, 5 should-fix, 8 nits, then round 2 verified)'
  - 'pixi run --frozen -e pyforge-doctor pyforge-doctor-test (3876 passed, 1 skipped); lint-types 0; detectors-ci 0; python -m pyforge.doctor.sources fr-without-cap 0 (508 enforced of 635 definitions, zero FAIL); chain_currency_sweep_check.py --project pyforge-doctor 0'
---

# pyforge-doctor — Retrospective (Epic 50)

## Epic summary

**Epic.** Epic 50, *Every requirement arrow resolves to a defined capability* (`epics.md` § Epic 50), one story.
The operator ruled on 2026-10-26 that a PRD requirement cites one or more defined capabilities and nothing else
(`spec-one-chain-per-station` CAP-5 as amended; CHAIN-STANDARD § 12). Story 50.1 is Doctor's half: the gate.

**Diff range.** `92fa3edbbd..HEAD` on the chain PR branch; the doctor code is in `ffa1715a08` (the first build) and
`b59245a8c8` (review round 2); the chain (Dream entry, CAP-92 and CAP-93, FR-14/FR-15 arrows, FR-16's heading, the
restored Spec text, Epic 50, the story spec, the ledger key) is in `dd27387817` with the other seven stations' stories.

**Stories completed.** 50.1 (`done` at retro time). `pending_stories`: none.

**Evidence inventory.** Available: the story spec with its Review Triage Log; the Spec and memlog; both independent
review reports and the re-review; the commit list; the test, lint and detector runs (exit codes read). Missing: no
dispatch journal (the story was hand-built in the chain PR, not dispatched), no session logs beyond the subagent
hand-backs; recorded as the process gap below.

## Findings

### Spec-to-implementation reconciliation

- **CAP-92 as built matches its success text** (`one_chain.py`, "Story 25.2" section rewritten): definition grammar
  (heading / bullet / table / bold marker, dotted and lettered ids, a wrapped prose line or a column-0 sentence never
  defines), arrow parsing (`fr-cites-non-capability`), resolution against capability *definition* lines in the named
  Spec (`fr-cap-unresolved` with `spec-not-found` / `cap-not-defined` / `spec-unreadable` / `spec-closed`),
  `fr-id-unhyphenated`, `fr-id-malformed`, `fr-duplicate-id`, `fr-counted-run`, the advisory
  `fr-arrow-no-title-overlap`, the baseline ratchet (`projects` = arrowless population; `findings` only shrinks;
  `--prune` removes only; `--snapshot-findings` one-time or `--force` with the delta printed; `fr-baseline-stale`
  WARN; `owners` map). Source: `spec-pyforge-doctor/SPEC.md` CAP-92; `scripts/fr_baseline.py`;
  `docs/governance/fr-baseline.json`. Disposition: accept.
- **The first build missed what the review found** (detector review, 2 blockers, 5 should-fix): an unguarded
  `--snapshot-findings` that would have laundered new findings; a bold-opened definition shape and five warden ids
  outside the grammar that vanished silently; a record-section rule that hid first definitions under any dated
  heading; a `spec-<x>` prefix that did not carry across cite items; dropped closed-Spec and unreadable-file
  handling; an asymmetric first/later definition test. All fixed in round 2 and verified by the re-review. Source:
  the review report; `b59245a8c8`. Disposition: fixed now.
- **CAP-93 is a paper mint**: Doctor's FR-15 had no capability stating it; CAP-93 records the guarantee the Epic 6
  stories (6.2, 6.8, 6.9) and Story 49.1 already delivered. No code moved for it. Disposition: accept (the review
  confirmed no other doctor CAP states the generalized ownership).
- **FR-14 and FR-15 cited the Charter**; now CAP-9 and CAP-93. FR-16 had no PRD heading since 2026-08-11; now it has
  one. Disposition: accept.

### Verification gap

- **Live-tree measurement is the proof, and it moved under the build.** The detector was built while the parent
  session fixed the five Constraint arrows and restored the Spec titles; the baseline was regenerated three times
  (first build, round 2, after the planning amendments). The final tree reads 508 enforced of 635 definitions, zero
  FAIL; `findings` = atlas 22 `fr-duplicate-id` (Story 41.2's), warden 11 `fr-id-malformed` + 3
  `fr-id-unhyphenated` (Story 20.2's); `projects` = the NFR lines and atlas's arrowless satellite ids (Stories 41.3,
  108.2, 33.2, 20.2). Disposition: accept; the `owners` map names each.
- **`fr-counted-run` has no live hit** once marshal's CAP-235..CAP-238 titles were restored — the rule is proven by
  fixtures (44 tests in `test_sources_one_chain_fr_arrows.py`), not by a live finding. The honest runs (steward
  FR-32..FR-41, atlas FR-69..FR-77, doctor FR-9..FR-13) are a live negative. Disposition: accept.
- **Coverage.** `one_chain.py` 88 % from its two test files; the station suite 3876 passed; the five-second CPU
  budget test passed (the gather costs 0.06 s). Disposition: accept.

### Process lessons

- **An independent review found what the builder's own measurements could not**: the subagent that built the
  detector reported "zero FAIL" truthfully while its grammar skipped five warden ids and a whole definition shape.
  Every detector story should budget the adversarial review as a gate, not a courtesy (CHAIN-STANDARD § 7 item 8
  says a local `detectors-ci` run is the proof; this epic shows the proof needs a second reader of the grammar).
- **The number of record is the detector's, not a hand count.** The NFR population was counted three ways in one day
  (82, 79, 82); the governance memlog carries the corrections. Measure with the parser (`fr-without-cap`'s `counts`
  evidence) before writing a number into a standard.
- **Hand-built chain stories leave no journal.** The story was built in the chain PR, so the only session record is
  the subagent hand-backs quoted in the commit messages and the memlogs; `marshal factory dispatch` would have
  journaled it. Acceptable for a planning-heavy story; recorded as the gap.
- **Edits that fail silently inside a `set -e` batch**: two of the planning amendments (the 111.1 grep, the NFR
  numbers) did not land on the first pass because an earlier assertion aborted the batch after a later command had
  been expected to run; the re-review caught it. Verify each text edit with a grep in the same step.

### Aggregate views

- **Rule → gate → carriage.** The rule (CAP-5, § 12), the gate (CAP-92), the harness layers (`_bmad/custom/`), the
  pointers (`AGENTS.md`) and the memory captures landed together; none depends on a later PR.
- **What the baseline still carries is owned.** Every `projects` id and `findings` key has a `backlog` story
  (atlas 41.2 / 41.3, marshal 108.2, mason 33.2, warden 20.2); the ratchet shrinks as they land.

## Behavior verification

Exercised end to end on the live tree: `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap`
(exit 0; OK row "508 enforced of 635 definition(s) measured"; two `fr-baselined` rows; advisory WARNs only) and the
`detectors-ci` aggregate (exit 0, the `fr-without-cap` row passing). Fixture behaviour observed through the 44
arrow-grammar tests plus the two CLI tests. Not exercised: a real PR red (no non-CAP arrow exists on the tree to
trip it); the fixture `fr-cites-non-capability` case stands in.

## Previous-retro follow-through

The previous doctor retro (2026-10-04, Epic 41) left action items on the deferral burn-down's Phases 4 and 5; they
are outside this epic's surface and were not re-checked here (recorded as not re-verified). No action from that retro
bears on `one_chain.py`.

## Action items

- **Operator ruling, warden ids** (owner: warden, Story 20.2): the five NFR ids outside the grammar (`NFR-R3a`,
  `NFR-R3b`, `NFR-P-warm`, `NFR-P-cold`, `NFR-P-concurrency`), the six `FR-NEW-A..F` table ids and the three
  unhyphenated ids (FR30, FR33, FR35) are baselined under `fr-id-malformed` / `fr-id-unhyphenated`; re-spelling them
  changes ids and needs a ruling.
- **Backfill stories** (owners: atlas 41.3, marshal 108.2, mason 33.2, warden 20.2; renumber atlas 41.2): the only
  routine baseline verb is `--prune`; each landing prunes its rows.
- **Process** (owner: doctor): a detector story's independent review reads the grammar against the live PRDs with
  its own one-off counter, as this one did; keep that step in the story template's Verification.

## Acceptance verdict

**accepted-with-open-items** (criteria: declared — the story spec's AC1..AC5). AC1 fixtures with known answers:
met (44 tests). AC2 live tree zero FAIL, Constraint arrows gone, honest runs quiet: met. AC3 baseline shape and owner
stories: met (`owners` map). AC4 suites, lint, `detectors-ci`, budget: met (exit codes 0). AC5 chain (CAP-92, CAP-93,
FR-14..FR-16, ledger rows, this retro): met. Open items: the warden id spellings (a ruling), and the baseline rows the
five `backlog` stories own.

## Open questions

- Should `fr-id-malformed` ids be re-spelled in place (changing ids warden stories cite) or carried as a sanctioned
  suffix family? A ruling for Story 20.2; the standard today says the one grammar.

## Assumptions

- Epic selected by invocation (`-H 50`); `detect-epic --epic 50` run on a worktree-local Tier-3 feed seeded from the
  tracked twin with Story 50.1 `done`; `pending_stories` empty.
- The two review reports and the re-review are the evidence of record for "reviewed"; no session logs exist beyond
  them.
- Verdict chosen without the operator: open items are owned by named `backlog` stories, so `accepted-with-open-items`
  rather than `rejected`.
