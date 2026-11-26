---
title: '136.11: The Story lines the page did not resolve name their capabilities'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 136-11-the-story-lines-the-page-did-not-resolve-name-their-capabilities
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

**Problem:** `DW-steward-136-5-1`. After Story 136.5, 46 Story FR/AD lines of steward's `epics.md` cite 82 bare capability ids under an Epic heading that names no Spec or more than one, 102 lines cite no capability, Story 12.9 keeps three ids of the absorbed `spec-ocp-as-a-portability-profile` beside an unqualified `parent CAP-6`, and Story 59.2 cites `spec-vocabulary-one-name-one-job CAP-2`, which no `← ` provenance heading names.

**Approach:** Trace each line from records, never from sequence. For a bare `CAP-n`: read the Story's tracked story spec under `planning-artifacts/specs/spec-<n>-<m>-*.md` (its `spec:` frontmatter and Binding section name the Spec), the Epic's prose, and the capability's intent in the Spec it would name; qualify the id only when a record names the Spec and the capability's intent matches what the Story does. For Story 12.9: `spec-ocp-as-a-portability-profile CAP-1` to `CAP-3` are `spec-pyforge-steward` CAP-78 to CAP-80 by the provenance headings; find from the archived Spec what `parent CAP-6` named and qualify it too. For Story 59.2: CHAIN-STANDARD section 0 says the vocabulary Spec's capabilities live on as `spec-pyforge-steward:CAP-132` to `CAP-138`; read the archived Spec's CAP-2 and find the steward capability with that intent, and if none carries it, say so and leave the line. For a line with no capability: add one only when the Story's spec or the Epic heading names it; a Story that realizes none (a retro, a research or a planning story) keeps its line. Only the citation token moves on a line.

Ledger key: `136-11-the-story-lines-the-page-did-not-resolve-name-their-capabilities`.

### Living CAP citations

- spec-pyforge-steward CAP-179 (the ids the station cites are the Spec's; realized, no text change); CHAIN-STANDARD section 2 (a citation names a defined capability, traced, never counted); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what is reported on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never guess an arrow: an id no record resolves stays as it is.
- Never renumber or reword a Story.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-136-5-1` lists the Story FR/AD lines of steward's `epics.md` that Story 136.5 could not resolve from the page
**When** each is traced through its story spec, its Epic's prose and the capability's intent, and re-keyed or qualified only where a record names the capability
**Then** every id written is a capability its Spec defines whose intent the Story's work matches, Stories 12.9 and 59.2 cite today's ids or record why not, and the lines still without a resolvable capability are counted by reason in the story's change log
**And** no Story key, heading, status or acceptance line changes, the chain detectors pass, and the row reads resolved, naming the counted remainder as lines that have no capability to cite

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

- Capabilities: spec-pyforge-steward CAP-179 (the ids the station cites are the Spec's; realized, no text change); CHAIN-STANDARD section 2 (a citation names a defined capability, traced, never counted); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the remainder of the rows a lapsed blocker held); operator ruling of 2026-11-25: "lets address these too".
- Epic: Epic 136.
- Ledger key: `136-11-the-story-lines-the-page-did-not-resolve-name-their-capabilities`.
- Deferred-work row: `DW-steward-136-5-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the remainder of the rows a lapsed blocker held) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: the counting rules. Two one-off scripts in the session's scratch folder, not committed: Story 136.5's classifier, unchanged, and a variant of it that reads a wrapped FR/AD segment whole (the label's line and the lines under it up to the next `**Label:**` line), takes `..` as a range, and keeps a tight continuation after a loose id or an arrow in that kind. The second exists because the first reads one line: the FR/AD segment of 21 of the *none* lines wraps, and on 18 of them the capability id sits on the next line, so the line counted as *none*.
- 2026-11-25: reproduction on the unchanged tree, by Story 136.5's classifier: 489 Story FR/AD lines; 2 absorbed, 46 bare (82 bare ids), 102 none, 339 qualified, as the row reports. By the wrap-aware variant the same tree reads 12 absorbed, 19 bare (30 bare ids), 84 none, 374 qualified: 10 of the 102 *none* lines cite an absorbed Spec's id across a line break (Stories 50.1, 50.3, 52.1, 53.1 to 53.6, 56.1), 8 cite a live Spec's id across one (Stories 54.1 to 54.5, 55.1 to 55.3; correct as written), and 27 of the 46 *bare* lines are ids that follow a Spec the line already names. One line outside the row's lists, Story 83.2, carries two bare ids on its wrapped line.
- 2026-11-25: the change. 123 lines of `epics.md` changed for 113 Stories: 112 FR/AD lines and 11 wrapped lines of an FR/AD segment (10 Stories change on both lines; Story 83.2 on its wrapped line only). 191 qualified ids written: 103 `spec-pyforge-steward`, 85 `spec-pyforge-unifying-strategy`, 2 `spec-one-chain-per-station`, 1 `spec-feature-flag-governance`; each resolves to a `- **CAP-n ` heading of the Spec it names. Checked by script: outside the FR/AD segment (or, for a wrapped line, outside its citation tokens) every changed line is identical; the `### Story`, `## Epic` and `**Status:**` lines, the 511 stories, the line count and every line from Epic 136's heading on are unchanged. The table of story, old text, new text and evidence path is kept with the scripts.
- 2026-11-25: Stories changed, by the evidence that names the capability. 26: the Story's own story spec names the Spec for each id in its Living CAP citations or Binding (13.5 to 13.7, 69.1, 70.1, 91.1, 102.3, 111.1, eleven of Epic 117, 118.1, 118.3, 122.1, 122.5, 124.5, 135.1, 135.2); the Spec's name is written once before each run of ids that followed it bare. 6: fix Stories whose story spec glosses each bare id with the capability's own title and which `spec-pyforge-steward/.memlog.md` records under that id (78.1, 79.1, 81.1, 82.1, 83.1, 83.2). 11: the red-team Stories of Epics 41 to 43, whose minting proposal carries `chain: spec-pyforge-unifying-strategy` and whose story specs list that Spec as context, each id checked against the capability's intent. 1: Story 32.1, named by `spec-pyforge-unifying-strategy` CAP-18's own correct-course note ("Epic 32"). 41: Canopy Stories of Epics 18 to 33 and 37 that cited only `canopy:FR-n`; the page's *Requirements Inventory (Canopy)*, under the heading that names the chain `spec-pyforge-unifying-strategy`, gives each `canopy:FR-n` its capability, and each was checked against the Story (Story 25.4 takes CAP-10 and not the inventory's CAP-8, because it touches no event backbone). 7: Stories 34.1 to 34.5, 36.1 and 36.2, from Epic 34's heading (CAP-19), Epic 36's prose and three story specs. 9: Stories 6.1 to 6.3, 7.1 to 7.5 and 8.1, whose story spec names the absorbed Spec, re-keyed by its one provenance heading where the capability's title is the Story's. 10: absorbed ids split over a line break, re-keyed by their one provenance heading as Story 136.5 did. 1 each: Story 12.9 and Story 114.9 (its story spec names `spec-feature-flag-governance` CAP-2, the gate).
- 2026-11-25: Story 12.9 reads `spec-pyforge-steward CAP-78, CAP-79, CAP-80 (parent spec-pyforge-steward CAP-103 / pap:AD-11)`. CAP-78 to CAP-80 are the provenance headings of `spec-ocp-as-a-portability-profile` CAP-1 to CAP-3, and their text is the smoke job, the Route and SCC proof and the runner class the Story builds. The parent: the Epic's *Spec binding (2026-08-24)* paragraph above the Story says "Parent `spec-python-agent-platform` CAP-6", and CAP-103 (air-gap parity) is that id's one provenance heading. The archived OCP Spec is a pointer with no body, so it gave no evidence.
- 2026-11-25: Story 59.2 is left as it is. `spec-vocabulary-one-name-one-job` CAP-2 (one declared vocabulary source the detectors and exit-code lattices read; text read from the Spec as it stood before the fold, `git show 97e0816ad2^`) was not carried by the 2026-09-17 fold: the fold's memlog minted capabilities for CAP-1, CAP-3 and CAP-5 to CAP-8 only, its heading being the one that wraps onto a second line; CAP-4 was added later. CAP-132 to CAP-138 are CAP-1 and CAP-3 to CAP-8, and none has CAP-2's intent (CAP-132 defines the Spec ladder; it does not say detectors read one declaration). No other Spec defines it; `spec-one-chain-per-station` CAP-9, `guild-roster.json` and doctor's `one_chain.py` still cite it by its old name. The Story is `done` and its behaviour ships, so the fix is a capability on `spec-pyforge-steward` through `bmad-spec`, which this Story may not mint. It needs a ruling and a row.
- 2026-11-25: after. By Story 136.5's classifier: 1 absorbed, 4 bare (6 ids), 44 none, 440 qualified. By the wrap-aware variant: 1 absorbed, 1 bare (1 id), 26 none, 461 qualified. The remainder, by reason. 26 lines cite no capability because the Story realizes none or no record names one: 2 Marshal-seam obligations (5.1, 5.2); 17 that bind to Spec Constraints, the Dream's Grounding, a deferred-work row or a readiness finding (43.1, 44.2, 48.1 to 48.5, 48.7, 48.8, 48.11, 49.1, 49.2, 49.9 to 49.13); 3 that bind to the AD-1 datastores exception, a Constraint (51.1 to 51.3); 2 with no capability by their own story spec (80.1, a defect of a CI lane; 122.4, a chore); 2 where no record names a capability (8.4; 33.2, whose `FR-10` is itself unqualified). 1 bare id is left on Story 41.4: its chain is `spec-pyforge-unifying-strategy`, but CAP-12's intent (IdP roles, secrets from a secret manager) is not broker TLS verification, which that Spec carries as a Constraint. 1 absorbed id is Story 59.2's. The other 3 lines Story 136.5's classifier still reads as *bare* are not unresolved: Story 122.1 (ranges written `CAP-152..CAP-164` after the Spec's name), Story 130.1 (the second id of `FR-8 ← CAP-2, CAP-168`, an in-station arrow in CHAIN-STANDARD section 2's form) and Story 136.2 (same-Spec ids after `spec-pyforge-steward`; Epic 136 is not this Story's to change). Its 44 *none* are the 26 above and the 18 lines whose id is on the wrapped line.
- 2026-11-25: found, not changed. Story 111.1's line cites `spec-foundry-regenerate-not-fold CAP-7 (B's starting discipline)`; that Spec defines CAP-1 to CAP-5 today. The id was on the line before this Story and no record says where it went.
- 2026-11-25: verdicts, each from its exit code: `chain-completeness-check` 0, `story-status-check` 0, `ledger-regression-check` 0, `dream-chain-check` 0, `chain-currency-sweep-check` 0. Not done here, left to the landing session: the deferred-work row, the memlog surface reconcile, the scoped stamps and the independent review.
- 2026-11-25: independent review (read-only): all 429 qualified ids on the changed lines resolve to a capability heading of the Spec they name; about 40 lines checked against their records; the Canopy inventory under `# Chain: spec-pyforge-unifying-strategy` is a record (the folded PRD's `##### canopy:FR-n` sections carry the same capability for every requirement), and 47 of the 48 lines it served equal its union. Applied: Story 117.12's trailing `CAP-174 (the Platform CI test job's budget)` now reads `spec-pyforge-steward CAP-174`, since it followed `spec-coverage-gate-independence`, which defines none. Kept: Story 25.4 cites `CAP-10` only where the inventory and `prd.md` name CAP-8 and CAP-10; the Story touches no event backbone, so CAP-8's intent does not match it.
- 2026-11-25: remainder carried by `DW-steward-136-11-1`: Story 59.2 cites `spec-vocabulary-one-name-one-job CAP-2` (one declared source for status sets and exit-code lattices; operator decision 2026-09-14 in the archived Spec's memlog), which the 2026-09-17 fold carried into no live Spec; Story 111.1 cites `spec-foundry-regenerate-not-fold CAP-7`, which that Spec no longer defines; Story 41.4 keeps a bare `CAP-12` whose intent is not what the Story does. 26 lines cite no capability because the Story binds to a Constraint, a deferred-work row, a seam obligation or a chore, or (8.4, 33.2) no record names one; they are not defects.
- 2026-11-25: closed. Implemented, independently reviewed against this spec, its findings applied; the deferred-work row is closed by the session lead; the full local `pr-preflight` gates the push to PR #2388.
