---
title: '33.4: The warden station skill cites the schema''s urn and the parser''s prog'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 33-4-the-warden-station-skill-cites-the-schema-s-urn-and-the-parser-s-prog
spec: spec-pyforge-warden
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
surface:
  - '.claude/skills/pyforge-warden/0.1.2/pyforge-warden/SKILL.md'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** DW-warden-33-3-1 (written by Story 33.3 from the independent skill check) said two citations in the compiled skill `pyforge-warden` 0.1.2 point a few lines off.

**Approach:** Read each against main: `report.py:192` is `REPORT_SCHEMA_VERSION = "1.1.0"` and `report.py:193` is `TOOL_NAME = "warden"`, so both cite what they claim (the check counted one line off). Add the two citations the skill lacked for facts it states: the schema's urn at `data/report-schema.json:3` and `prog=TOOL_NAME` at `cli.py:446`. The provenance map holds the nine API exports, not prose citations, so it does not move. Close the row with the corrected evidence.

Ledger key: `33-4-the-warden-station-skill-cites-the-schema-s-urn-and-the-parser-s-prog`.

### Living CAP citations

- spec-pyforge-warden CAP-8 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Check every citation in the skill resolves.

**Never:**
- Never change a fact the skill states, only where it cites it.
- Never edit inside a `[MANUAL]` block or an export the provenance map holds.

**Deviation (recorded):** Epic 33's boundary says the compiled skill is not hand-edited. This story edits two prose
citation lines outside every `[MANUAL]` block, on the operator's ruling "close DW-warden-33-3-1 too": the provenance map
holds API exports only, `manual-verify` hashes only `[MANUAL]` interiors, and `skf-update-skill`'s merge step carries
prose lines through a regeneration, so the edit survives it and desynchronises nothing.

## Acceptance Criteria

**Given** two citations reported a line off and two stated facts uncited
**When** each is read against main and the missing two are added
**Then** the existing two are confirmed and `data/report-schema.json:3` and `cli.py:446` are cited
**And** every citation resolves and the row is closed

- **AC1 — Warden's meta-tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta -q -m "live_tree or not live_tree"
  ```

</intent-contract>

## Review (2026-11-26)

An independent `bmad-review` pass confirmed every claim against the files: lines 192 and 193 of `report.py` were the same at the Story 33.3 commit and the skill's source commit, so the row counted one line off; the two new citations hit the urn and `prog=TOOL_NAME`; all 38 citations resolve; the provenance verifier exits 0 on the edited skill (15 matched, 0 stale, 0 citation findings); `manual-verify` hashes only `[MANUAL]` interiors. Findings and what was done: (1) Epic 33's boundary contradicted this story; an amendment line and the deviation above record it. (2) Prose citations match no provenance entry, so no tool re-checks them when the source moves; the row's resolution now says the check was by hand at `afdc9099df`. (3) `SKILL.md:70` cites pyforge-core's `dispatch.py` from the repository root while the others are package-relative; it resolves from the root, and the skill's cross-package citations have no other form, so it stays. (4) A wording nit in the resolution, fixed.
