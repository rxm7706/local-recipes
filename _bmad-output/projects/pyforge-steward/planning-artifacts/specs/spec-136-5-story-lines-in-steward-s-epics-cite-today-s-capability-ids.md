---
title: '136.5: Story lines in steward''s epics cite today''s capability ids'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 136-5-story-lines-in-steward-s-epics-cite-today-s-capability-ids
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-cutover-2026-11-10-9`. The 2026-11-10 design pass counted 383 Story `FR/AD` lines in steward's `epics.md` that cite a pre-fold or bare capability id or none: 133 bare, 149 qualified to an absorbed Spec, 101 with none.

**Approach:** Re-count first, with a script kept in the story's change log. Re-key each line that cites an absorbed Spec's id by the provenance headings of `SPEC.md` (`CAP-n ... <- spec-<absorbed> CAP-m`), the map `test_cap_citations.py` holds; qualify a bare `CAP-n` only where the Story's own text or its Epic heading fixes which Spec it meant. A line with no capability, and a bare id that cannot be resolved from the page, is left as it is and counted: a guessed arrow is worse than none (trace, never count). Only the citation token moves on a line; no Story text, status, key or heading changes.

Ledger key: `136-5-story-lines-in-steward-s-epics-cite-today-s-capability-ids`.

### Living CAP citations

- spec-pyforge-steward CAP-179 (the ids the station cites are the Spec's; realized, no text change); CHAIN-STANDARD section 2 (a citation names a defined capability); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never guess an arrow: an id the page does not resolve stays as it is.
- Never renumber or reword a Story.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-cutover-2026-11-10-9` reports 383 Story FR/AD lines in steward's `epics.md` that cite an absorbed Spec's capability id, a bare id or none
**When** each line citing an absorbed Spec is re-keyed through the Spec's provenance headings, and each bare id the page resolves is qualified
**Then** no Story FR/AD line cites an absorbed steward Spec's capability as a live id, every re-keyed id is a capability `spec-pyforge-steward` defines, and the lines left unresolved are counted by kind in the story's change log
**And** no Story key, heading, status or acceptance line changes, `chain-completeness-check`, `story-status-check` and `ledger-regression-check` pass, and the row reads resolved, naming any remainder as a new row if one is left

- **AC1 — The chain detectors hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild chain-completeness-check
  ```

- **AC2 — Story statuses are untouched.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild story-status-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-179 (the ids the station cites are the Spec's; realized, no text change); CHAIN-STANDARD section 2 (a citation names a defined capability); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-5-story-lines-in-steward-s-epics-cite-today-s-capability-ids`.
- Deferred-work row: `DW-steward-cutover-2026-11-10-9`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: the counting rules (a one-off script in the session's scratch folder, not committed). A Story FR/AD line is a line under a `### Story` heading that carries `**FR/AD:**`; its segment runs from that label to the next ` • **Label:**` or the line's end. The provenance map is `SPEC.md`'s headings read with `test_cap_citations.py`'s `_PROVENANCE` expression: 183 headings, 143 from 32 absorbed Specs, no `(Spec, CAP-m)` pair twice. A line's kind is the first that holds: *absorbed* (a live id qualified by an absorbed Spec's name or by `sld:`, `suite:` or `hub:`), *bare* (a `CAP-n` with no Spec named before it on the line, not an `FR-n ← CAP-m` arrow), *none* (no capability id), *qualified* (the rest). A `← spec-<absorbed> CAP-m` or `from spec-<absorbed> CAP-m` note beside today's id is provenance, not a live id.
- 2026-11-25: reproduction on the unchanged tree. 486 Story FR/AD lines: 99 absorbed, 54 bare, 102 none, 231 qualified; 255 lines in the row's three kinds against the 383 it reported on 2026-11-10 (133 bare, 149 absorbed, 101 none). The row's script is not kept, so the difference is not traced: this count holds a continuation id (`spec-pyforge-steward CAP-175 and CAP-5`), an arrow and the live prefixes `pap:`, `fnd:`, `fcl:` and `fnr:` as qualified. By citation: 87 absorbed by Spec name, 27 by `sld:`, `suite:` or `hub:`, 94 bare, 3 provenance notes.
- 2026-11-25: the change. 105 lines changed, each only in its citation tokens (checked: the text outside the FR/AD segment is identical, the segment with its capability ids masked is identical, and the `### Story`, `## Epic` and `**Status:**` lines, the 508 stories, the line count and every line from Epic 136's heading on are unchanged). 110 absorbed ids re-keyed to `spec-pyforge-steward CAP-n` by their one provenance heading: 83 written with the Spec's name (one in the form `spec-jira-github-projects-sync, CAP-1`, three in backticks) and 27 by prefix (`sld:` 8, which a Surface line under Epic 48 on the page declares for secure-live-dashboards; `suite:` 18, by the one Spec the heading of Epic 39, 46 or 47 names; `hub:` 1, whose own line names `spec-intelligence-hub`). 12 bare ids qualified with `spec-pyforge-unifying-strategy`, the one Spec the heading of Epic 40, 48 or 49 names, each defined there.
- 2026-11-25: after. 2 absorbed, 46 bare, 102 none, 336 qualified. Left unresolved, by reason: 82 bare ids on 46 lines whose Epic heading names no Spec or more than one; 102 lines with no capability id, untouched; 3 absorbed ids on Story 12.9's line (`spec-ocp-as-a-portability-profile CAP-1, CAP-2, CAP-3 (parent CAP-6 / pap:AD-11)`), because re-keying them would make the unqualified `parent CAP-6` read as a steward id; 1 absorbed id on Story 59.2's line (`spec-vocabulary-one-name-one-job CAP-2`), which no provenance heading carries. Untouched and not counted as unresolved: 76 ids under a live prefix (`pap:`, `fnd:`, `fcl:`, `fnr:` and other stations'), 28 arrows, 3 provenance notes. So the acceptance clause "no Story FR/AD line cites an absorbed steward Spec's capability as a live id" holds but for those two lines, which need a ruling and a new row.
- 2026-11-25: verdicts, each from its exit code: `chain-completeness-check` 0, `story-status-check` 0, `ledger-regression-check` 0, `dream-chain-check` 0, `chain-currency-sweep-check` 0. Not done here, left to the landing session: the deferred-work row, the memlog surface reconcile and the scoped stamps.
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff), its findings applied; the deferred-work row or rows are closed in their ledgers by the session lead, and the full local `pr-preflight` gates the PR that lands it (branch `named-blocker-rows-2026-11-25`).
