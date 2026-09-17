---
title: 'Story 24.1: mcp-builder is atlas-wielded for the MCP face'
type: 'chore'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      test_adoption_register.py's persona-mention check only verifies the skill name
      substring appears in a persona SKILL.md, never that the routing line's stated
      grammar constraint text is present.
    evidence: |-
      _persona_mentions (test_adoption_register.py:145-151) does `name in
      path.read_text(...)` -- a bare substring match. A future edit could delete the
      "pyforge atlas ... verbs only" constraint sentence while leaving a stray mention
      of `mcp-builder` elsewhere in bmad-agent-atlas/SKILL.md and this test would still
      pass. Pre-existing design from Story 46.1, unchanged by this diff -- not this
      story's surface to fix.
    location: >-
      src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py:145
    severity: medium
  - summary: >-
      The eventual integration PR for this branch needs the `maintenance` label
      (none of this diff's three changed files are under recipes/).
    evidence: |-
      CLAUDE.md's always-on PR-gate rule: any change outside recipes/ requires
      `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance` at PR
      open/update time. This task run does not open a PR -- the orchestrating session
      merges this branch -- so the labeling step belongs to whichever later PR wraps
      it.
    location: >-
      .claude/skills/bmad-agent-atlas/SKILL.md, src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py, _bmad-output/projects/pyforge-atlas/planning-artifacts/sprint-status-ledger.yaml
    severity: low
baseline_revision: '317228f3a382bc11453440362726c4ae6d84374c'
---

<intent-contract>

## Intent

**Problem:** Steward Story 46.5 provisioned the `mcp-builder` labs skill by consent under
`.claude/skills/mcp-builder`, and `adoption-register.md` § 1/§ 2 already name Atlas its sole
wielder, but the Atlas persona skill itself carries no routing line recording that ownership or
the grammar constraint generated MCP tools must honor.

**Approach:** Add a "Labs skill routing (AD-2)" section to `.claude/skills/bmad-agent-atlas/SKILL.md`
(mirroring the existing "Utility skill routing (AD-2)" sections other station personas already
carry) naming `mcp-builder` as atlas-wielded and stating that any tool it scaffolds must call
`pyforge atlas …` verbs only. Remove the now-landed `mcp-builder` entry from the cross-station
AD-2 meta-test's not-yet-landed carve-out so that test's exclusivity/positive checks fully cover
this row going forward.

## Boundaries & Constraints

**Always:**
- Keep the routing line's grammar constraint explicit: MCP tools `mcp-builder` scaffolds for
  atlas call `pyforge atlas …` CLI verbs only — never import `pyforge.atlas` internals, never a
  second MCP server or port for the station.
- Remove the `"mcp-builder": "atlas 24.1"` entry from `_ROUTING_STORY_NOT_YET_LANDED` in
  `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` (its own docstring:
  "Remove a name from this set the same day its own cited story lands the persona mention, never
  before") and trim its surrounding comment to name only the two still-pending entries
  (`slides-generator` → herald 18.3, `multi-repo-git-ops` → marshal 31.6).
- Flip `24-1-mcp-builder-is-atlas-wielded-for-the-mcp-face` from `blocked` to `done` in the Tier-3
  `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml`, then promote
  via `pixi run -e local-recipes sprint-ledger-sync -- --project atlas` (never hand-edit the
  tracked `sprint-status-ledger.yaml`, which is generated).
- Verify (do not restate) that `adoption-register.md` § 2 row 43 and § 1 row 10 already name atlas
  sole wielder, and that `AGENTS.md`'s existing single pointer line to the register already covers
  this row.

**Never:**
- Never edit `CLAUDE.md` (routing notes never live there).
- Never touch `_bmad/**` provisioning code or any other labs-skill's carve-out entry
  (`slides-generator`, `multi-repo-git-ops` — their own stories haven't landed).
- Never restate the routing table itself in `AGENTS.md` beyond its existing one pointer line.

</intent-contract>

## Code Map

- `.claude/skills/bmad-agent-atlas/SKILL.md` -- add a new `## Labs skill routing (AD-2)` section
  directly after `## Overview` and before `## Conventions` (same placement as the sibling
  `## Utility skill routing (AD-2)` sections in `bmad-agent-herald`, `-doctor`, `-steward`,
  `-marshal`, `-warden`, `-scribe` SKILL.md files, each a single short paragraph).
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` lines ~207-228 --
  `_ROUTING_STORY_NOT_YET_LANDED` dict (currently `{"mcp-builder": "atlas 24.1", "slides-generator":
  "herald 18.3", "multi-repo-git-ops": "marshal 31.6"}`) and its preceding comment block naming all
  three: remove the `mcp-builder` key/comment mention, keep the other two, keep the module
  docstring's own historical note about Story 46.5 (that describes what 46.5 did, not current
  carve-out state, so it stays).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`
  § 2 row 43 (`mcp-builder | labs | atlas | bmad-agent-atlas | atlas 24.1`) -- already correct,
  read-only reference.
- `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml` line 236
  (`24-1-mcp-builder-is-atlas-wielded-for-the-mcp-face: blocked`) -- flip to `done` (Tier-3,
  backlinked; edit via Bash, not the Write/Edit tools).
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/sprint-status-ledger.yaml` line 79 --
  regenerate via `sprint-ledger-sync`, never hand-edit.

## Tasks & Acceptance

**Execution:**
- `.claude/skills/bmad-agent-atlas/SKILL.md` -- add `## Labs skill routing (AD-2)` section naming
  `mcp-builder` and the grammar constraint -- records the routing home (AD-2).
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` -- drop the
  `mcp-builder` carve-out entry and its comment mention -- keeps the cross-station meta-test
  accurate the same day the persona mention lands, per its own instruction.
- `_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml` -- flip
  `24-1-...` to `done` -- Tier-3 intent record.
- Run `pixi run -e local-recipes sprint-ledger-sync -- --project atlas` -- promotes the tracked
  twin.

**Acceptance Criteria:**
- Given the labs skill installed by name, when the atlas persona routes new MCP tool scaffolding
  to `mcp-builder` with the constraint that generated tools call `pyforge atlas …` verbs only,
  then the register names atlas as sole wielder, the routing line states the grammar constraint,
  and `CLAUDE.md` is untouched.
- Given `test_adoption_register.py`'s `_ROUTING_STORY_NOT_YET_LANDED` carve-out, when
  `mcp-builder`'s persona mention lands, then that test's single-station positive assertion
  actually runs for `mcp-builder` (no longer skipped) and still passes.

## Spec Change Log

## Review Triage Log

### 2026-09-07 -- Review pass
- verdicts: 8 findings -- high 0, medium 1, low 5, false 2, maybe-false 0
- findings:
  - `[low]` `[patch]` bmad-agent-atlas/SKILL.md's new routing line omits the register row-number citation and uses the full package name (`bmad-labs-skills`) instead of the short alias, unlike the same-day sibling precedent `bmad-agent-steward/SKILL.md:16` (`` `release-please` (labs; see adoption-register.md sec 2, row 46) ``) -- verified: `mcp-builder` is at adoption-register.md line 43; fix is a direct wording correction.
  - `[low]` `[patch]` The new heading `## Labs skill routing (AD-2)` diverges from the only existing precedent for the same AD-2 convention, `bmad-agent-steward/SKILL.md:12` `## Utility skill routing (AD-2)`, which steward already reuses for its own labs-sourced `release-please` line (steward/SKILL.md:16) as well as builder and skf routing -- verified by reading steward's SKILL.md; fix is a direct heading rename to match the established pattern.
  - `[low]` `[patch]` test_adoption_register.py's rewritten inline comment above `_ROUTING_STORY_NOT_YET_LANDED` says "removed that entry here the same day" with an ambiguous "here" that a reader could misread as the register table itself rather than this dict -- verified the wording is workable but improvable; fix is a direct clarifying rewording (name the dict, not just "here").
  - `[low]` `[patch]` test_adoption_register.py module docstring (lines 25-33) still reads "Its three sibling labs skills (`mcp-builder`, `slides-generator`, `multi-repo-git-ops`) ... routed by three OTHER, not-yet-landed station stories (atlas 24.1, herald 18.3, marshal 31.6)" -- now factually wrong: `mcp-builder`'s routing landed in this very diff and the carve-out set the docstring points to (`_ROUTING_STORY_NOT_YET_LANDED`) now holds two entries, not three -- verified by reading the docstring and the current dict; fix is a direct three-line text update, no new surface.
  - `[medium]` `[defer]` `_persona_mentions`/`test_skill_routing_matches_ad2_for_every_currently_provisioned_row` only checks that the literal substring `mcp-builder` appears anywhere in `bmad-agent-atlas/SKILL.md`, never that the routing line's grammar-constraint sentence itself is present -- a future edit could delete the constraint text while leaving a bare mention and this test would still pass -- verified by reading `_persona_mentions` (test_adoption_register.py:145-151), unchanged by this diff. Pre-existing test-design gap from Story 46.1, not introduced by Story 24.1's narrow surface (`.claude/skills/bmad-agent-atlas/SKILL.md` + the carve-out dict); no fix applied here.
  - `[low]` `[false]` Ledger flip of `24-1-...` from `blocked` to `done` "carries no accompanying evidence (commit hash, PR reference)" -- checked: no entry in `sprint-status-ledger.yaml` (137 stories) carries inline evidence; the file's own header states it is machine-generated from the Tier-3 feed via `sprint-ledger-sync`, and the script's own monotonic guard is the safeguard against false-dones, not per-row annotation. Not a defect of this diff.
  - `[low]` `[defer]` None of this diff's three changed paths are under `recipes/`, so the eventual integration PR needs the `maintenance` label per CLAUDE.md's always-on PR-gate rule -- real, but this task run does not open a PR (explicit instruction: the orchestrating session merges this branch), so the labeling step belongs to that later PR, not this diff. Flagged in the final report for the orchestrating session.
  - `[low]` `[false]` Intent-alignment auditor noted the Tier-3 `implementation-artifacts/sprint-status.yaml` flip (the source `sprint-ledger-sync` promotes from) never appears in a version-control diff since that tree is excluded from tracking -- checked: confirmed on disk the Tier-3 file already reads `done` at line 236, consistent with the tracked ledger's promoted value; the invisibility is the intended Tier-3/tracked-twin boundary, not a defect.
- patches applied (all 4 `patch`-routed findings, re-engaged step-03 implementer, re-verified):
  - `.claude/skills/bmad-agent-atlas/SKILL.md` heading renamed `## Labs skill routing (AD-2)` -> `## Utility skill routing (AD-2)` to match the `bmad-agent-steward` precedent.
  - Same file: routing line reworded to the short-alias + row-number citation style (`` `mcp-builder` (labs; see adoption-register.md § 2, row 43) ``).
  - `test_adoption_register.py` inline comment: ambiguous "here" replaced with an explicit "this carve-out dict"; register row 43 noted as unchanged.
  - `test_adoption_register.py` module docstring: corrected from the stale three-sibling/three-not-yet-landed claim to the current two-remaining-sibling state.
  - Re-ran `pixi run -e pyforge-steward pyforge-steward-test -- -k test_adoption_register` (8 passed) and the full `pyforge-steward-test` suite (1161 passed) after the patches; diff file rewritten and re-read.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test -- -k test_adoption_register` -- expected: all
  pass, including the now-unskipped `mcp-builder` single-station branch.
- `pixi run -e pyforge-atlas pyforge-atlas-test` (or `kedro-test` if that task name does not exist)
  -- expected: pass, unaffected by this docs-only change.
- `grep -n "mcp-builder" .claude/skills/bmad-agent-atlas/SKILL.md` -- expected: routing line present.
- `grep -n "mcp-builder" CLAUDE.md` -- expected: no output.

**Manual checks (if no CLI):**
- Confirm `adoption-register.md` § 1 row 10 and § 2 row 43 already read `atlas` as wielder (no
  edit needed, read-only check).

## Auto Run Result

**Summary:** Added a routing line to `.claude/skills/bmad-agent-atlas/SKILL.md` naming Atlas as
the wielder of the `mcp-builder` labs skill and stating the `pyforge atlas …`-only grammar
constraint on tools it scaffolds; removed the now-landed `mcp-builder` entry from
`test_adoption_register.py`'s `_ROUTING_STORY_NOT_YET_LANDED` carve-out (updating its comment and
module docstring to match); flipped the story's ledger entry from `blocked` to `done`.

**Files changed:**
- `.claude/skills/bmad-agent-atlas/SKILL.md` -- new `## Utility skill routing (AD-2)` section
  naming `mcp-builder` and the grammar constraint.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` -- removed the
  `mcp-builder` carve-out entry; corrected its inline comment and module docstring to the
  now-current two-remaining-sibling state.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/sprint-status-ledger.yaml` -- `24-1-...`
  flipped `blocked` -> `done` (promoted via `sprint-ledger-sync --project atlas` from the Tier-3
  `implementation-artifacts/sprint-status.yaml`, which is not tracked in version control).

**Review findings breakdown (8 total):**
- Patched (4, all `low`): SKILL.md heading renamed to match steward's precedent; SKILL.md
  citation reworded to the short-alias + row-number style; test file's ambiguous "here" pronoun
  clarified; test file's stale module-docstring cardinality claim corrected.
- Deferred (2): a pre-existing (Story 46.1) `medium`-severity test-design gap -- the AD-2
  persona-mention check only verifies a substring match, never the constraint sentence itself;
  and a `low`-severity note that the eventual integration PR needs the `maintenance` label
  (this run does not open a PR).
- Rejected as `false` (2): the ledger-flip "no evidence citation" claim (no ledger entry among
  137 carries one; not a defect); the intent-alignment auditor's note that the Tier-3 source file
  never appears in the tracked diff (expected Tier-3/tracked-twin boundary, confirmed correct on
  disk).

**Follow-up review recommendation:** false. All patched findings this pass were `low`; no `high`
patched and fewer than two `medium` patched (the one `medium` finding was deferred, not patched).

**Verification performed:**
- `pixi run -e pyforge-steward pyforge-steward-test -- -k test_adoption_register` -- 8 passed
  (before and after the patch pass).
- `pixi run -e pyforge-steward pyforge-steward-test` (full suite) -- 1161 passed, no regressions.
- `pixi run -e pyforge-atlas kedro-test` -- 1726 passed, 23 skipped, 2 failed
  (`test_dashboard_e2e.py`'s two Playwright cases -- pre-existing environmental gap, missing
  `chrome-headless-shell` browser binary in this worktree; unrelated to this docs-only diff, which
  touches no dashboard/persona runtime code).
- `grep -n "mcp-builder" .claude/skills/bmad-agent-atlas/SKILL.md` -- routing line present.
- `grep -n "mcp-builder" CLAUDE.md` -- no output (untouched, as required).
- Manual check: `adoption-register.md` § 1 row 10 and § 2 row 43 already name `atlas` sole
  wielder -- confirmed, no edit needed.

**Residual risks:** none from this change's own surface. The two deferred findings are recorded
above and in frontmatter `deferred`; the Playwright browser-binary gap is a pre-existing
environmental limitation of this worktree, not introduced by this story.
