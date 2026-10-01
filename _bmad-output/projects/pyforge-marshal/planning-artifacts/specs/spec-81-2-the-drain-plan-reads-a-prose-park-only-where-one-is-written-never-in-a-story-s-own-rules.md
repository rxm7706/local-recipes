---
title: "81.2: The drain plan reads a prose park only where one is written, never in a story's own rules"
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: '70c074d58076180ce75919a4ee3bcde1a7244f00'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-2-a-drain-schedules-the-follow-up-review-a-landed-story-recommended.md
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `core/dispatch_prelaunch.py::find_prose_park` reports a story as parked in prose when its `epics.md` block or
its tracked spec has a line matching "parked" or "do not dispatch". It scans the whole spec, including the
`<intent-contract>` block, where a feature's own rules live. On 2026-10-01 `drain --plan` reported 73.2 as parked
(MRS-DRAINPLAN-002) on its Never bullet "Do not dispatch a follow-up whose row is closed or absent…", which describes
what 73.2 builds, not a decision to hold 73.2.

**Approach:** in the tracked spec, `find_prose_park` skips the `<intent-contract>` … `</intent-contract>` block; every
other line of the spec, and the whole `epics.md` block, is scanned as today.

Ledger key: `81-2-the-drain-plan-reads-a-prose-park-only-where-one-is-written-never-in-a-story-s-own-rules`.
Type / Effort / Deps: fix / XS / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-274 (Story 65.1, `drain --plan`). A defect of shipped behaviour, so no new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a spec whose only "do not dispatch" line is inside its `<intent-contract>` block When `find_prose_park` scans it Then it returns `None`
- Given a spec with a "parked" or "do not dispatch" line outside the intent contract When it is scanned Then the park is reported as today
- Given a story's `epics.md` block with such a line When it is scanned Then the park is reported as today
- Given 73.2's tracked spec When `drain --plan` runs Then no MRS-DRAINPLAN-002 names 73.2
- Given the intent-contract skip removed When the new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Keep `find_prose_park` pure. `skip_policies` stays the one park mechanism.

**Never:** Do not change the park regexes. Do not edit 73.2's spec to dodge the check.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_prelaunch.py` -- `find_prose_park` (the one change site) scans `epics_block` then `spec_text` through `_park_line`; `_PARKED_RE` / `_DO_NOT_DISPATCH_RE` are read-only (Never: no regex change). Core is pure (AD-4): no I/O.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py` -- callers at `evaluate_story` (~l.354) and `_scan_prose_park` (~l.722) pass the raw spec text in; read-only, no change needed.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_prelaunch.py` -- `find_prose_park` tests (~l.63-136); add the contract-skip tests beside them.
- `src/shared/packages/pyforge-marshal/tests/unit/test_drain_plan.py` -- `test_a_prose_park_in_the_tracked_spec_is_found` (~l.1215) is the plan-level twin; add the no-finding twin for a contract-only line.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-73-2-a-drain-schedules-the-follow-up-review-a-landed-story-recommended.md` -- read-only evidence: its only park-matching line (l.65) sits inside its `<intent-contract>` (l.16-91); never edit it.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_prelaunch.py` -- strip each whole-line `<intent-contract>` ... `</intent-contract>` block from `spec_text` (not `epics_block`) before `_park_line`, per Design Notes (a tag counts only as its own line, so a backticked or mid-line mention never opens or closes a block); update the comment and docstring to say exactly that -- the contract holds a feature's own rules, not a hold decision
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_prelaunch.py` -- tests for the contract ACs: a contract-only line is `None` (mutation: this test fails with the skip removed); a line outside the contract (before it, after it, and between two blocks) still reports `source == "tracked spec"`; a contract line in an `epics_block` still reports; an opening tag line with no closing tag line scans the whole spec; a contract whose text mentions both tags in backticks stays skipped to its real closing line (the shape of this story's own spec); a mid-line opening-tag mention before a real park line does not hide that park; a block never joins the lines around it (`do not <block>dispatch` is not a park)
- `src/shared/packages/pyforge-marshal/tests/unit/test_drain_plan.py` -- a plan over a spec whose only "do not dispatch" line is in its contract raises no MRS-DRAINPLAN-002
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` -- append a corrective surface-reconcile entry naming the changed governed paths and superseding the earlier 2026-10-01 Story 81.2 entry's regex description (a non-greedy mid-line strip) with the whole-line rule (via `_bmad/scripts/memlog.py`, never hand-edit `SPEC.md`), on this Spec and on each co-governor `spec-surface` names (`spec-pyforge-core`)

## Spec Change Log

### 2026-10-01 — review pass 1 (bad_spec)
- Trigger: the first implementation followed the Design Notes' unanchored regex `<intent-contract>.*?</intent-contract>`. It pairs tag text anywhere on a line: a backticked `</intent-contract>` inside the contract ended the strip early (this story's own spec still reported a park), and a mid-line opening-tag mention before a real `Parked …` line silently dropped that park (reproduced; 63 of 351 specs with tags are not exactly one open plus one close).
- Amended: Design Notes and the `dispatch_prelaunch.py` and test tasks now require tags matched as whole lines only; the unclosed-tag sentence is made exact; Tasks add the prose-mention tests, the park-between-two-blocks test (pins the non-greedy match) and a corrective memlog entry.
- Known-bad state avoided: a tag mentioned in prose acting as a block delimiter, in either direction.
- KEEP: strip only from `spec_text`, replacing each block with a newline; `epics_block` scanned whole; the park regexes untouched; the contract-only, outside-the-contract, epics-contract-line, unclosed-tag and multiple-block tests; the plan-level test; the memlog entries on `spec-pyforge-marshal` and `spec-pyforge-core` (append-only, so the correction is a new entry).

## Design Notes

Strip the block, never scan it line by line. Match each tag only as a whole line, `^[ \t]*<intent-contract>[ \t]*$` to `^[ \t]*</intent-contract>[ \t]*$`, non-greedy, with `re.MULTILINE | re.DOTALL`, and replace the match with a newline so the surrounding lines stay apart. A backticked or mid-line mention of either tag is prose, never a delimiter. An opening tag line with no closing tag line after it matches nothing, so the whole spec is scanned (a malformed spec reports a park rather than silencing one, AD-8). A stray own-line opening tag before the real block pairs with the next closing line; the template emits one block, so that malformed shape is out of scope.

## Binding

Parent: `spec-pyforge-marshal` CAP-274 (Story 65.1); defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 (evening) entry.
Ledger key: `81-2-the-drain-plan-reads-a-prose-park-only-where-one-is-written-never-in-a-story-s-own-rules`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: fix the defect now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-01 — Review pass
- verdicts: 24 findings — high 4, medium 7, low 9, false 4, maybe-false 0
- findings:
  - `[high]` `[bad_spec]` Blind Hunter: the contract regex matches tag text anywhere, so a backticked `</intent-contract>` inside the contract ends the strip early and the fix fails on this story's own spec — evidence: `find_prose_park` on the 81.2 spec returned the contract line "only "do not dispatch" inside its…"; 63 of 351 specs with tags are not exactly one open plus one close. Amended: Design Notes and Tasks now require whole-line tags.
  - `[medium]` `[bad_spec]` Blind Hunter: `test_a_stripped_block_never_joins_the_lines_around_it` pins mid-line tag matching and no test uses a prose mention of a tag — evidence: its fixture is `do not <intent-contract>`; same root cause as the row above. Amended: Tasks name the prose-mention tests; the join test moves to whole-line tags.
  - `[low]` `[bad_spec]` Blind Hunter: the code comment and docstring overclaim the unclosed-tag case — evidence: a stray open tag plus a later real block pairs up (reproduced); same root cause. Amended: Design Notes state the exact rule.
  - `[low]` `[reject]` Blind Hunter: the 81.2 spec's own Execution bullet contains the trigger phrase outside the contract, so the plan flags the story — evidence: true (anchored probe still returns that bullet), but the fix is to edit this build's spec; the story's `epics.md` block carries the phrase as well (AC 3 keeps it a park), and the story leaves the queue at `done`.
  - `[low]` `[reject]` Blind Hunter: AC 4 is checked only with a synthetic fixture — evidence: `drain --plan --all-stories` over the real marshal station evaluated 73.2 and raised no MRS-DRAINPLAN-002 for it; a unit test coupled to a mutable planning file is not worth adding.
  - `[low]` `[reject]` Blind Hunter: the plan-level test has no positive control, a vacuous `code == 0`, and a dead `_write_spec` — evidence: the test fails with the skip removed (mutation run), so it scans 22-8; the sibling `test_a_prose_park_in_the_tracked_spec_is_found` is the positive control and the other two points mirror it.
  - `[low]` `[reject]` Blind Hunter: CAP-274 text is not amended, only logged as `(event)` entries — evidence: CAP-274's intent and success text do not describe the tracked-spec scan region, so nothing is contradicted; the contract says a defect needs no CAP change.
  - `[false]` `[reject]` Blind Hunter: the reconcile entries omit the story spec path, so `spec-surface` may read it as unreconciled — evidence: `spec_surface_reconcile.py` and `spec-surface-check` both exit 0 on the tree.
  - `[medium]` `[bad_spec]` Edge Case Hunter: a backticked `</intent-contract>` mention ends the strip early — evidence: reproduced (probe: the rule after the mention is reported as a park); same root cause as the first row.
  - `[high]` `[bad_spec]` Edge Case Hunter: a mid-line opening-tag mention before a real park line plus a later closing tag silently drops that park — evidence: reproduced (`find_prose_park` returned `None` for "Parked until 22.7 lands." between the two); same root cause.
  - `[low]` `[reject]` Edge Case Hunter: tag variants (upper case, attributes, a space before `>`) are not matched — evidence: no spec in the tree uses one (case-sensitive scan, 0 files); the template emits the literal tag and a wider pattern adds complexity for no demonstrated input.
  - `[medium]` `[bad_spec]` Edge Case Hunter: every new test uses own-line well-formed tags and none mentions a tag in prose — evidence: confirmed by reading the seven tests; same root cause.
  - `[medium]` `[bad_spec]` Edge Case Hunter (claim): the strip pairs the first opening string with the first closing string anywhere — evidence: reproduced on the story's own spec; same root cause.
  - `[high]` `[bad_spec]` Edge Case Hunter (claim): an unreported real park after a mid-line opening mention lets the drain dispatch a held story — evidence: reproduced as above; same root cause.
  - `[medium]` `[patch]` Verification Gap: nothing pins the non-greedy `.*?` — evidence: a greedy `.*` passes all seven tests; a park between two blocks is not covered. Moot this pass (code is re-derived); the amended Tasks list the between-blocks test.
  - `[medium]` `[bad_spec]` Verification Gap (other): a literal tag mention inside the contract body cuts the strip short; the story's own spec has 7 opens and 4 closes — evidence: reproduced; same root cause.
  - `[high]` `[bad_spec]` Verification Gap (other): prose mentions of an opening tag and a later closing tag pair up and hide the lines between — evidence: reproduced; same root cause.
  - `[low]` `[reject]` Verification Gap (other): no test reads the real 73.2 spec — evidence: same as the AC 4 row above; the real run came back clean.
  - `[low]` `[reject]` Intent Alignment 1: AC 4 is met by a stand-in, not by 73.2 itself — evidence: the end-to-end `drain --plan` over the real tree covers 73.2; the fixture pins the behaviour.
  - `[low]` `[reject]` Intent Alignment 2: the plan-level test covers only the `_scan_prose_park` path, not `evaluate_story` — evidence: both callers pass the same unmodified `spec_text` to the one pure function, which the unit tests pin; no divergence is plausible.
  - `[false]` `[reject]` Intent Alignment 3: AC 5 is claimed by a docstring, not a harness — evidence: with the skip removed the contract-only tests fail (in-process mutation run, 3 prelaunch tests plus the plan-level test); the AC asks only that the new test fails.
  - `[false]` `[reject]` Intent Alignment 4: the Never "do not edit 73.2's spec" is respected — evidence: a compliance report, no bad outcome claimed; the diff does not touch that spec.
  - `[false]` `[reject]` Intent Alignment 5: files outside the intent's stated surface changed (spec frontmatter, Code Map name, two memlogs) — evidence: the workflow and the run's reconcile rule require each of them; no bad outcome.
  - `[medium]` `[bad_spec]` Intent Alignment 6: an unclosed open tag plus a later closed block pairs the first open with that close — evidence: reproduced; same root cause as the first row.
