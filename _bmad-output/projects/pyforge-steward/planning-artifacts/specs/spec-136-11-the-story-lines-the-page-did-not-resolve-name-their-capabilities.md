---
title: '136.11: The Story lines the page did not resolve name their capabilities'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
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
