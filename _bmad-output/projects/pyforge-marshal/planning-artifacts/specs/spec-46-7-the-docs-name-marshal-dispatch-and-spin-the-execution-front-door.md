---
title: '46.7: The docs name marshal dispatch and spin the execution front door'
type: 'docs'
created: '2026-09-18'
status: 'in-review'
baseline_revision: 'ff2455866b'
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

## Design Notes

The Approach line names an optional advisory doctor detector ("may flag a bare dispatch") in
addition to the docs edits. Left out of scope for this story: no AC requires it, `pyforge-doctor`
has no existing "bare bmad-build-auto invocation" signal to extend (verified by grep across
`sources/`), and detecting a bare skill invocation from outside that session's own transcript is
a separate, non-trivial design problem — not a same-sized docs edit. If wanted, it belongs to a
follow-on story with its own CAP, not folded into this S-effort docs story.

The intent-contract's I/O & Edge-Case Matrix row (read-only, recovered verbatim from `epics.md`)
restates the AC as a table row rather than describing a runtime I/O scenario, and its "Expected
Output/Behavior" cell is truncated mid-word. No pytest in this repo asserts markdown prose content
in `AGENTS.md`/`CLAUDE.md`/a skill note, so there is no dedicated automated test to point the
Matrix Test Audit at. The audit for this row was performed by direct inspection: the diff since
`baseline_revision` was read in full and confirms the required phrases land in all three files,
which is the applicable check for a `type: docs` story with no code-level I/O.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
