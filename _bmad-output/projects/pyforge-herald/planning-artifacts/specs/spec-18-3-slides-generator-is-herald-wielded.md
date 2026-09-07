---
title: 'slides-generator is herald-wielded'
type: 'feature'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      Story 18.2 (sibling branch herald-r2a, not present in this branch's
      history) already rewrites the same "Utility skill routing (AD-2)"
      section this story appends to, into a numbered procedure -- landing
      both branches will need manual re-threading, not a mechanical git
      merge.
    evidence: |-
      Confirmed via `git show --stat` / `git log` against
      `origin/bmad/adoption-readiness-2026-09-06-herald-r2a` commit
      de771710fa (Story 18.2), which is not an ancestor of this branch: it
      replaces the pre-existing one-line "Herald wields
      `bmad-os-changelog`..." sentence in
      `.claude/skills/bmad-agent-herald/SKILL.md` with a multi-paragraph
      explanation plus a 4-step numbered procedure. This story's diff
      instead appends its new `slides-generator` paragraph directly after
      that soon-to-be-replaced one-liner. Out of this dispatch's own
      explicit scope (instructed not to touch herald-r2a) -- the
      orchestrating session that merges both branches into the integration
      branch needs to manually re-thread the slides-generator paragraph
      into 18.2's rewritten section rather than relying on a mechanical
      merge/rebase.
    location: >-
      .claude/skills/bmad-agent-herald/SKILL.md (## Utility skill routing
      (AD-2) section)
    severity: medium
baseline_revision: '317228f3a382bc11453440362726c4ae6d84374c'
---

<intent-contract>

## Intent

**Problem:** `bmad-labs-skills`' `slides-generator` skill was provisioned onto disk by
steward Story 46.5 (`.claude/skills/slides-generator/`), and adoption-register.md § 2
row 44 already names herald as its sole wielding station and cites this story, but
`bmad-agent-herald/SKILL.md` has no routing note for it yet — so the persona's own
AD-2 gate (`test_adoption_register.py::test_skill_routing_matches_ad2_for_every_currently_provisioned_row`)
is only passing today because of a story-cited carve-out
(`_ROUTING_STORY_NOT_YET_LANDED["slides-generator"] = "herald 18.3"`) that must be
removed the same day this lands.

**Approach:** Add a routing note to `bmad-agent-herald/SKILL.md` naming
`slides-generator` and stating the CAP-6 boundary verbatim (draft only; the
Claude-Design → Vite deck pipeline in `docs/specs/presentation-deck.md` stays the
deck source of record, never forked or superseded). Remove `slides-generator` from
steward's `_ROUTING_STORY_NOT_YET_LANDED` carve-out now that the mention exists, and
add a herald-local meta-test proving the routing note, the boundary language, and
CLAUDE.md's continued silence.

## Boundaries & Constraints

**Always:** Routing note lives only in `bmad-agent-herald/SKILL.md` (AD-2's one
durable home). State the boundary explicitly: `slides-generator` produces quick
draft slides only; it is never a deck head and never replaces the Claude-Design →
Vite pipeline. Use only FR-13/CAP-16-compatible framing — `slides-generator` is an
ordinary Claude Code skill invoked by whoever drafts quick slides, not part of the
persona's CAP-16 action set (it writes files directly; mirrors 18.2's precedent for
the two changelog skills). Remove the `slides-generator` entry from steward's
`_ROUTING_STORY_NOT_YET_LANDED` dict in the same change (the dict's own comment
requires this the same day the mention lands).

**Never:** Do not touch `CLAUDE.md`. Do not touch `_bmad/**` or any steward-owned
provisioning surface. Do not touch adoption-register.md § 2 row 44 (already correct)
or § 1 row 10 (steward-owned, deliberately stays "documented"). Do not install,
invoke, or exercise `slides-generator` itself — this story is a routing-note change
only (no live-fire requirement, per Epic 18's compiled context). Do not touch
`bmad-os-changelog`/`-social` routing (Story 18.2, a separate branch, out of scope
here).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Producer present | `.claude/skills/slides-generator/SKILL.md` exists | AD-10-style check passes | N/A |
| Producer missing (synthetic) | fixture root without the skill dir | check reports the missing path | assertion names it explicitly |
| Carve-out still present | `_ROUTING_STORY_NOT_YET_LANDED` still has `slides-generator` after this story | steward's own meta-test would silently skip the positive assertion | this story's own test must fail if the carve-out entry is still present once the persona mentions it |

</intent-contract>

## Code Map

- `.claude/skills/bmad-agent-herald/SKILL.md` -- add a `slides-generator` routing note under (or beside) the existing `## Utility skill routing (AD-2)` section; keep the section name stable since `test_release_comms_routing.py` (a sibling branch's test, not present here) also anchors on it, but this branch does not carry that file — anchor only on what exists here.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` lines 224-228 -- `_ROUTING_STORY_NOT_YET_LANDED` dict; remove the `"slides-generator": "herald 18.3"` entry per its own comment ("Remove a name from this set the same day its own cited story lands the persona mention, never before").
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` line 44 -- already correct (`slides-generator | labs | herald | bmad-agent-herald | herald 18.3`); read-only reference, not edited.
- `.claude/skills/slides-generator/SKILL.md` -- read-only reference for what the skill does (React+Tailwind quick slide drafts, standalone HTML export).
- `docs/specs/presentation-deck.md` -- read-only reference for the deck-pipeline boundary language ("the deck pipeline it must not fork").
- New: `src/shared/packages/pyforge-herald/tests/meta/test_slides_generator_routing.py` -- herald-local meta-test mirroring the shape of Story 18.2's `test_release_comms_routing.py` pattern (producer-on-disk check + synthetic missing-producer proof, routing-section token check, boundary-language check, CLAUDE.md silence check).

## Tasks & Acceptance

**Execution:**
- `.claude/skills/bmad-agent-herald/SKILL.md` -- add a `slides-generator` routing note stating: the skill is wielded for quick slide drafts, it never becomes a deck head, and the Claude-Design → Vite pipeline (`docs/specs/presentation-deck.md`) remains the deck source of record -- so `bmad-agent-herald` carries a concrete, checkable boundary statement, not a bare "wields" mention.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` -- remove `"slides-generator": "herald 18.3"` from `_ROUTING_STORY_NOT_YET_LANDED` -- so steward's own generic AD-2 gate now asserts the positive "herald mentions it" half for this row instead of skipping it.
- `src/shared/packages/pyforge-herald/tests/meta/test_slides_generator_routing.py` (new) -- machine-check the routing note's presence, the boundary language, the producer-on-disk state (+ a synthetic missing-producer proof), and CLAUDE.md's continued silence on `slides-generator` -- so `pyforge-herald-test` alone proves this story's acceptance criteria.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml` -- flip the `18-3-slides-generator-is-herald-wielded` row from `blocked` to `done`.

**Acceptance Criteria:**
- Given the labs skill installed by name, when the herald persona routes quick slide drafts to `slides-generator`, then `bmad-agent-herald/SKILL.md` names it and states the boundary (draft only; never a deck head; the Claude-Design pipeline stays the deck source of record).
- Given steward's `test_skill_routing_matches_ad2_for_every_currently_provisioned_row`, when it runs against this branch's tree, then it exercises (not skips) the positive single-station assertion for `slides-generator` and passes.
- Given `pyforge-herald-test`, when it runs, then the new meta-test module passes and CLAUDE.md still never mentions `slides-generator`.
- Given adoption-register.md, when inspected, then row 44 (§ 2) still names herald as sole wielder unchanged (this story adds no new row, edits none).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 10 findings — high 0, medium 3, low 3, false 4, maybe-false 0
- findings:
  - `[medium]` `[defer]` Story 18.2 (sibling branch `herald-r2a`, commit `de771710fa`) already rewrote the same "## Utility skill routing (AD-2)" section this diff appends to, into a numbered procedure; this branch's paragraph is appended after the pre-rewrite one-liner, so landing both branches will need manual re-threading, not a mechanical merge — real, but out of this dispatch's own scope (explicit instruction: do not touch `herald-r2a`); recorded in frontmatter `deferred` for the orchestrating session. (blind-hunter)
  - `[low]` `[patch]` Module docstring and comment above `_ROUTING_STORY_NOT_YET_LANDED` in `test_adoption_register.py` still said "three" sibling skills and listed `slides-generator -> herald 18.3` as not-yet-landed after the dict entry was removed, contradicting the code three lines below — fixed: both prose spots now say "two" and drop the `slides-generator`/`herald 18.3` mention. (blind-hunter)
  - `[medium]` `[patch]` This story's spec lived only in Tier-3 `implementation-artifacts` (gitignored, not git-tracked), reopening the "story specs are durable" promotion gap CLAUDE.md's convention exists to prevent, and diverging from Story 18.2's own precedent of committing its promoted spec in the same commit — fixed: spec copied verbatim to the tracked `planning-artifacts/specs/spec-18-3-slides-generator-is-herald-wielded.md`. (blind-hunter)
  - `[false]` `[reject]` Claimed the ledger flipping `18-3` to `done` while `18-1`/`18-2` remain `blocked` is unsound because the stories aren't really independent — refuted: Epic 18's own compiled context states verbatim "18.1, 18.2, and 18.3 have no dependencies on each other — each is an independent relay that only needs its own steward-side producer to have landed first"; the shared-SKILL.md-section concern this finding also raises shares its root cause with the deferred sibling-branch-overlap finding above. (blind-hunter)
  - `[false]` `[reject]` Claimed `test_steward_carve_out_no_longer_lists_slides_generator`'s regex text-scrape of `_ROUTING_STORY_NOT_YET_LANDED` is needlessly brittle versus importing the real dict — refuted: `pyforge-herald` and `pyforge-steward` are separate pixi environments/packages, so importing steward's test module from herald's test suite would fail at collection time (steward is not installed in the herald environment); reading the sibling file's source text directly is the only feasible, environment-agnostic check, consistent with Story 18.2's own precedent of keeping `pyforge-herald-test` self-contained. (blind-hunter)
  - `[low]` `[patch]` The new test module never stated that AD-2 exclusivity (no other station's persona also mentions `slides-generator`) is covered elsewhere, which a future reader of only this module might mistake for an oversight — fixed: added a docstring paragraph noting it is deliberately left to steward's `test_skill_routing_matches_ad2_for_every_currently_provisioned_row`, which already covers it unconditionally. (blind-hunter)
  - `[low]` `[patch]` Same stale "three sibling skills" / `slides-generator -> herald 18.3` prose identified independently — same fix as above, carried in the same edit. (edge-case-hunter)
  - `[false]` `[reject]` Noted the diff resolves the AC's "the herald persona routes quick slide drafts to slides-generator" language by stating the skill is invoked directly by whoever drafts slides rather than by the persona itself, framing this as a possible divergence — refuted: the persona's own pre-existing Forbidden Actions/CAP-16 constraints (no direct filesystem, only `consult_content_skill`/`grammar`/`mcp` action kinds) foreclose the persona ever invoking a file-writing skill directly, and Story 18.2 resolved the identical "routes to X" AD-2 pattern for the changelog skills the same way — the established, correct reading, not a gap. (intent-alignment)
  - `[false]` `[reject]` Noted the AC clause "the register names herald as sole wielder" is satisfied only by pre-existing infrastructure (the already-populated register row 44 plus steward's own generic AD-2 test) rather than by a new assertion in this diff — refuted: the verification-gap layer independently ran `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` and confirmed it now checks row 44 against the live persona file and passes; relying on the pre-existing cross-station gate for this half of AD-2 is the register's designed architecture (routing lives with the wielder; the generic check lives in steward), not a gap this diff needed to re-implement. (intent-alignment)
  - `[medium]` `[defer]` Separately noted this diff marks `18-3` done in the ledger while the section it edits is also being rewritten by sibling Story 18.2 on another branch not present here — shares its root cause with the sibling-branch-overlap finding above; carried there, not a second entry. (intent-alignment)

## Design Notes

Mirrors Story 18.2's precedent (same epic, same routing-note-only shape) without
depending on it: 18.2 lives on a sibling branch (`herald-r2a`) not present in this
worktree's history, so this story's new meta-test module is self-contained and does
not assume `test_release_comms_routing.py` exists. `slides-generator`'s own
`SKILL.md` triggers on "slides"/"presentation"/"PPT" keywords and produces a
standalone React+Tailwind HTML export in a project-local folder -- an entirely
separate artifact shape from the Claude-Design `.dc.html` → Vite deck engine
pipeline, which is why the boundary statement is load-bearing rather than
decorative: nothing about the two pipelines' outputs is compatible, so "draft only,
never a deck head" is a factual boundary, not a style preference.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: all tests pass, including the new `test_slides_generator_routing.py`.
- `pixi run -e pyforge-steward pyforge-steward-test -- -k test_adoption_register` -- expected: `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` passes with `slides-generator` no longer carved out.

## Auto Run Result

**Summary:** Implemented Story 18.3 in full: `bmad-agent-herald/SKILL.md` now
carries a concrete AD-2 routing note for `slides-generator` (quick draft slides
only; never a deck head; the Claude-Design → Vite pipeline in
`docs/specs/presentation-deck.md` stays the deck source of record), steward's
`_ROUTING_STORY_NOT_YET_LANDED` carve-out no longer lists this row, a new
herald-local meta-test proves the routing note and the carve-out removal, and the
sprint ledger flips `18-3` to `done`. A four-layer review found 10 findings across
blind-hunter, edge-case-hunter, verification-gap, and intent-alignment; 3 patched,
1 deferred (as 2 grouped raw findings), 6 rejected as false.

**Files changed:**
- `.claude/skills/bmad-agent-herald/SKILL.md` -- added the `slides-generator` AD-2 routing note.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` -- removed the `slides-generator` entry from `_ROUTING_STORY_NOT_YET_LANDED`; patched two stale prose spots referencing it.
- `src/shared/packages/pyforge-herald/tests/meta/test_slides_generator_routing.py` (new) -- 6 tests: producer-on-disk + synthetic missing-producer, routing-section presence, boundary-language, CLAUDE.md silence, carve-out-removal; docstring patched to note exclusivity is covered by steward's own suite.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml` -- flipped `18-3-slides-generator-is-herald-wielded` from `blocked` to `done`.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-18-3-slides-generator-is-herald-wielded.md` (new, tracked) -- promoted copy of this spec, per the "story specs are durable" convention.

**Review findings breakdown:**
- Patches applied (3): stale "three sibling skills" prose in `test_adoption_register.py` (low); missing spec promotion to tracked `planning-artifacts/specs/` (medium); missing exclusivity-coverage note in the new test module's docstring (low).
- Deferred (1, from 2 grouped raw findings — see frontmatter `deferred` and Review Triage Log): Story 18.2's sibling branch (`herald-r2a`) rewrites the same SKILL.md section this story edits; the two branches will need manual re-threading at merge time, not a mechanical merge. Out of this dispatch's scope (explicit instruction not to touch `herald-r2a`) — flagged for the orchestrating session.
- Rejected as false (6, see Review Triage Log for full evidence): ledger-independence claim (refuted by Epic 18's own no-cross-dependency text); regex-scrape-brittleness claim (refuted by the two stations' separate pixi environments); AC "routes" wording divergence (refuted by CAP-16's Forbidden Actions and Story 18.2's identical precedent); half-AC-untested claim (refuted by verification-gap's own passing run of steward's pre-existing test).

**Follow-up review recommendation:** `false`. Only one `medium`-verdict finding was patched (the spec-promotion gap); the rule requiring `true` needs either a patched `high` or two-or-more patched `medium` findings, and neither threshold was met.

**Verification performed:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- 1247 passed, 4 skipped (both before and after the review patches).
- `pixi run -e pyforge-steward pyforge-steward-test -- -k test_adoption_register` -- 7 passed, 1 skipped (unrelated, pre-existing share-tree-dependent skip), before and after the review patches.
- Full `pyforge-steward-test` suite also re-run clean: 1158 passed, 3 skipped.
- Matrix Test Audit: all three I/O & Edge-Case Matrix rows (producer present, producer missing, carve-out still present) are each covered by a passing test in `test_slides_generator_routing.py`.

**Residual risks:** the deferred sibling-branch-overlap item above is the only
open item — a real merge-reconciliation cost for the orchestrating session, not a
defect in this branch's own diff. Nothing else outstanding.
