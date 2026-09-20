---
title: '46.7: The docs name marshal dispatch and spin the execution front door'
type: 'docs'
created: '2026-09-18'
status: 'done'
baseline_revision: 'ff2455866b'
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred:
  - summary: >-
      An advisory (never gating) doctor detector that could flag a bare `bmad-build-auto`
      dispatch was named in the Approach line but left unimplemented.
    evidence: >-
      No AC requires it, `pyforge-doctor` has no existing "bare invocation" signal to extend
      (verified by grep across `sources/`), and detecting a bare skill invocation from outside
      that session's own transcript is a separate, non-trivial design problem, not a same-sized
      docs edit. Belongs to a follow-on story with its own CAP.
    location: src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** As an agent choosing how to run a story, I want AGENTS.md / CLAUDE.md / station skill notes to name `marshal factory dispatch` / `spin` as the default execution path and bare `bmad-build-auto` as the sanctioned-but-unmeasured path, So that the instrumented path is the default and the bare path is a conscious choice.

**Approach:** AGENTS.md, CLAUDE.md, and the bmad-build-auto skill note; an advisory (never gating) doctor detector may flag a bare dispatch.

Ledger key: `46-7-the-docs-name-marshal-dispatch-and-spin-the-execution-front-door`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: docs / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-194 (fold remint of `spec-marshal-token-economy` CAP-21; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-194` ← `spec-marshal-token-economy CAP-21`.

## Acceptance Criteria

- Given an agent reads the repo's entry docs When it chooses an execution path for a story Then the docs point at marshal dispatch/spin as default and explain what the bare path forgoes (the layers, the journal, the benchmark) And nothing new turns red in CI because of this story

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not cite absorbed `spec-marshal-token-economy` CAP-19..24 as living numbers; use CAP-192..197.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| an agent reads the repo's entry docs | it chooses an execution path for a story | the docs point at marshal dispatch/spin as default and explain what the bare pat | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.7 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Code Map

- `.claude/skills/bmad-build-auto/SKILL.md` -- the skill note agents load on bare invocation; needed the default-vs-unmeasured contrast added directly after its render-command instructions.
- `CLAUDE.md` -- § Skill Reference, the `bmad-build`/`bmad-build-auto` table row, inside the existing `governance-currency:ignore-start`/`ignore-end` block (lines 153–157) — edited in place, block markers preserved verbatim.
- `AGENTS.md` -- § Dream-first workflow, numbered item 3 ("Autonomy") — amended in place rather than inserting a new list item, since item 5 ("Spec → Story before code") is cross-referenced by number from `docs/dreams/library-catalog-manifest-sync.md` and `docs/dreams/pyforge-marshal.md`; renumbering would have broken those citations.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/{main.py,spin.py,dispatch.py}` -- read-only: confirmed the real `marshal factory dispatch` (Story 22.1) / `drain` (Story 22.7) / `spin` (Story 3.3) grammar to cite accurately; not modified.

## Tasks & Acceptance

**Execution:**
- `.claude/skills/bmad-build-auto/SKILL.md` -- append a "Default execution path" note -- names `marshal factory dispatch`/`spin` as default and bare invocation as sanctioned-but-unmeasured, at the point an agent following this skill would read it.
- `CLAUDE.md` -- amend the `bmad-build`/`bmad-build-auto` row -- same contrast at the doc every Claude Code session loads by default.
- `AGENTS.md` -- amend Dream-first item 3 -- same contrast in the cross-tool contract every harness reads.

**Acceptance Criteria:**
- Given an agent reads `AGENTS.md`, `CLAUDE.md`, or the `bmad-build-auto` skill note, when it chooses how to run a story, then all three name `marshal factory dispatch` (single story) / `marshal factory spin` (multi-story) as the default execution path and state what bare `bmad-build-auto` invocation forgoes (the substrate/compression layers, the journal entry, the per-harness savings benchmark).
- Given this is a docs-only change to three already-tracked files, when the two named verification commands run, then neither turns red because of this story.

## Spec Change Log

## Review Triage Log

### 2026-09-20 — Review pass
- verdicts: 5 findings — high 0, medium 0, low 3, false 2, maybe-false 0
- findings:
  - `[low]` `[patch]` Design Notes described the advisory-doctor-detector scope-out only in prose; sibling specs (`spec-22-9-...`, `spec-28-2-...`) record such scope-outs as a `deferred:` frontmatter entry — added a `deferred:` list item for it.
  - `[false]` `[reject]` Claimed CLAUDE.md's new sentence sits inside a `governance-currency:ignore-start/end` block scoped to removed/renamed skill names while AGENTS.md's identical sentence is unguarded, creating a detection asymmetry — refuted: `scripts/governance_currency_check.py` does not pattern-match `` `marshal factory dispatch` ``/`` `marshal factory spin` `` in either file (it only resolves backticked `bmad-*`/`skf-*` skill tokens and specific repo-relative paths), so neither file is scanned for this phrasing and there is no asymmetry to fix.
  - `[low]` `[patch]` Code Map attributed `marshal factory spin`'s grammar to "Stories 22.1/22.7," but `cli/spin.py`'s own docstring cites Story 3.3 (22.1/22.7 belong to `dispatch`/`drain` per `cli/dispatch.py`'s docstring) — corrected the citation.
  - `[false]` `[reject]` Claimed `.claude/skills/bmad-build/SKILL.md` (the sibling `bmad-build` skill) has the same bare-invocation boilerplate and got no equivalent default-execution-path note — refuted: `marshal factory dispatch`/`spin` launch `bmad-build-auto` sessions specifically (`cli/dispatch.py` docstring: "launch exactly one detached bmad-build-auto story session"), not `bmad-build`, so that skill has no analogous bare-invocation gap to document, and the Approach line names this one skill by name.
  - `[low]` `[patch]` Design Notes claimed "No pytest in this repo asserts markdown prose content in `AGENTS.md`/`CLAUDE.md`/a skill note," but `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` does assert markdown-content properties of exactly these files (e.g. the bare `@AGENTS.md` import line, named team-memory paths, `bmad:context` block intactness) — reworded to name that test and clarify it doesn't cover this story's specific new phrasing.

## Design Notes

The Approach line names an optional advisory doctor detector ("may flag a bare dispatch") in
addition to the docs edits. Left out of scope for this story: no AC requires it, `pyforge-doctor`
has no existing "bare bmad-build-auto invocation" signal to extend (verified by grep across
`sources/`), and detecting a bare skill invocation from outside that session's own transcript is
a separate, non-trivial design problem — not a same-sized docs edit. If wanted, it belongs to a
follow-on story with its own CAP, not folded into this S-effort docs story; recorded structurally
in this spec's `deferred:` frontmatter.

The intent-contract's I/O & Edge-Case Matrix row (read-only, recovered verbatim from `epics.md`)
restates the AC as a table row rather than describing a runtime I/O scenario, and its "Expected
Output/Behavior" cell is truncated mid-word. `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`
asserts markdown-content properties of `AGENTS.md`/`CLAUDE.md` (the `@AGENTS.md` import line,
named team-memory paths, `bmad:context` block intactness) but has no assertion covering this
story's specific new "default execution path" / "marshal factory dispatch/spin" phrasing, and no
test in this repo touches `bmad-build-auto/SKILL.md` at all — so there is no dedicated automated
test to point the Matrix Test Audit at for this row. The audit for this row was performed by
direct inspection instead: the diff since `baseline_revision` was read in full and confirms the
required phrases land in all three files, which is the applicable check for a `type: docs` story
with no code-level I/O.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Auto Run Result

**Summary:** `AGENTS.md`, `CLAUDE.md`, and `.claude/skills/bmad-build-auto/SKILL.md` now name `marshal factory dispatch` (single story) / `marshal factory spin` (multi-story) as the default execution path for a story, and state what a bare `bmad-build-auto` invocation forgoes (the substrate/compression layers, the journal entry, the per-harness savings benchmark). No code, ledger, or CI-gate changes.

**Files changed:**
- `.claude/skills/bmad-build-auto/SKILL.md` — added a "Default execution path" paragraph after the render-command instructions.
- `CLAUDE.md` — amended the `bmad-build`/`bmad-build-auto` Skill Reference row (inside the existing `governance-currency` ignore-block, markers untouched) with the same contrast.
- `AGENTS.md` — amended Dream-first-workflow item 3 ("Autonomy") in place with the same contrast, preserving the existing item numbering that `docs/dreams/library-catalog-manifest-sync.md` and `docs/dreams/pyforge-marshal.md` cross-reference.
- This spec file — added `## Code Map` / `## Tasks & Acceptance` / `## Spec Change Log` / `## Review Triage Log` / `## Design Notes`, a `deferred:` frontmatter entry, and the frontmatter lifecycle fields (`baseline_revision`, `followup_review_recommended`, `status`).

**Review findings breakdown** (2026-09-20 pass, 5 findings, all from the Blind Hunter layer — Edge Case Hunter and Verification Gap Reviewer reported none; the Intent Alignment Auditor's descriptive report raised no separate finding):
- Patched (3, all `low`): the `deferred:` frontmatter entry for the out-of-scope advisory detector (previously prose-only); the Code Map's `spin` story citation (corrected from 22.1/22.7 to 3.3, its actual docstring citation); the Design Notes' test-coverage sentence (named `test_instruction_surface_parity.py` instead of claiming no such test exists, and clarified it doesn't cover this story's specific phrasing).
- Rejected (2, both `false`): a claimed governance-currency ignore-block detection asymmetry between CLAUDE.md and AGENTS.md — refuted, since that detector doesn't pattern-match this story's phrasing in either file; a claimed missing default-execution-path note on `bmad-build/SKILL.md` — refuted, since `marshal factory dispatch`/`spin` wrap `bmad-build-auto` sessions specifically, not `bmad-build`, so that sibling skill has no analogous gap.
- No `intent_gap` or `bad_spec` findings; no `defer`-routed findings.
- Process note: the 3 patches were applied directly rather than by re-engaging the step-03 subagent, since all three were self-contained edits to this spec file's own supporting sections (Code Map/Design Notes/`deferred:`) rather than to the three doc files the subagent had authored — re-engagement would have been redundant.

**Follow-up review recommendation:** `false`. All patched entries were `low` severity (none `high`, fewer than two `medium`), so no follow-up pass is warranted.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8329 passed, 1 skipped, 12 deselected, exit 0 (re-run after patches). `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped, exit 0 (re-run after patches). Both read directly from exit code, never through a pipe.

**Residual risks:** None identified beyond the deferred advisory-detector capability (recorded in frontmatter `deferred:`), which is explicitly out of scope for this docs-only story.
