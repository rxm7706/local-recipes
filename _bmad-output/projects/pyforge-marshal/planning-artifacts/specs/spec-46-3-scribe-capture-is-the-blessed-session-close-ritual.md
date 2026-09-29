---
title: '46.3: `scribe capture` is the blessed session-close ritual'
type: 'docs'
created: '2026-09-18'
status: 'done'
baseline_revision: 'e0b6b3ffa8'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As an operator who wants memory write-back from every harness, I want `scribe capture` named in the front-door docs as the harness-neutral session-close ritual, So that what a session learned lands in the shared substrate no matter which harness ran it.

**Approach:** AGENTS.md / CLAUDE.md / the station skill notes — the same docs that name the front door — plus one line in each harness profile's notes.

Ledger key: `46-3-scribe-capture-is-the-blessed-session-close-ritual`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: docs / S / S-46.7.

### Living CAP citations

- `spec-pyforge-marshal` CAP-192 (story slice CAP-19(c) of the reminted CAP-192). Fold remint: `spec-marshal-token-economy` CAP-19 → CAP-192 (`spec-marshal-token-economy` absorbed).
- Living: `spec-pyforge-marshal CAP-192` ← `spec-marshal-token-economy CAP-19`.

## Acceptance Criteria

- Given a session closes in any harness When the operator or agent follows the front-door docs Then the close ritual is `scribe capture` with decision-grade facts, and the docs say so in one place And capture hygiene is stated: no secrets, decision-grade facts only

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
| a session closes in any harness | the operator or agent follows the front-door docs | the close ritual is `scribe capture` with decision-grade facts, and the docs say | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.3 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Code Map

- `AGENTS.md` § *Team memory — read at session start, every harness* -- the ONE canonical place the
  session-close ritual is stated (governed by `spec-pyforge-scribe`'s `surface:`; CAP-27's
  duplication-guard meta-test forbids restating this in any pointer file, so every other file below
  is a one-line pointer here, not a restatement).
- `CLAUDE.md` § *Team Memory* -- one-line pointer added; `CLAUDE.md` already imports `AGENTS.md`
  via the bare `@AGENTS.md` line (`test_claude_md_imports_agents_md_as_a_bare_line`), so the pointer
  is redundant-on-purpose the same way its sibling lines already are. Ungoverned (no spec surface
  lists `CLAUDE.md`), so no memlog reconcile applies to this edit.
- `GEMINI.md` -- one-line pointer added after the existing worktree/PR bullet. Governed by
  `spec-pyforge-scribe`'s `surface:`; reconciled via that spec's `.memlog.md` (see below).
- `.github/copilot-instructions.md` -- one-line pointer added after the existing verification
  bullet. Same governance as `GEMINI.md`.
- `.cursor/rules/trunk-worktree-pr.mdc` -- new numbered step 4 ("Close the session") inserted before
  the existing "Clean" step (renumbered 5); no other `.mdc` in `.cursor/rules/` cross-references
  this file's step numbers (checked via repo-wide grep), so renumbering is safe. Ungoverned by any
  spec surface.
- `.claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md` `<!-- [MANUAL:additional-notes] -->`
  carve-out -- one-line pointer added; this region is the sanctioned hand-edit surface that survives
  SKF regeneration. Ungoverned by any spec surface. Satisfies the Surface's "station skill notes"
  clause for this story's own station; does NOT itself name the execution front door -- that
  referent is `_bmad/custom/bmad-build-auto.toml` (see below), per Story 46.7's own landing history.
- `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md` `<!-- [MANUAL:additional-notes] -->`
  carve-out -- one-line pointer added, a pure pointer with no restatement (matches every other
  pointer file's shape). Ungoverned by any spec surface.
- `_bmad/custom/bmad-build-auto.toml` `[workflow] persistent_facts` -- a second fact appended naming
  the session-close ritual, mirroring the existing dispatch/spin fact's own style. This is the
  file the Approach's "the same docs that name the front door" actually refers to: Story 46.7's
  front-door fact was moved here from the installer-owned `.claude/skills/bmad-build-auto/SKILL.md`
  (landing commit `f72b82e7d5d`, fallout commit `fb2c96f6acd`) because `bmad-method install
  --action update` overwrites that installer-owned file. Ungoverned by any spec surface (confirmed
  via `python scripts/spec_surface_reconcile.py`, which allowlists it with no drift).
- `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` -- the CAP-27
  gate that pins `AGENTS.md` as the single substantive location and every other file as a thin
  pointer (`POINTER_MAX_LINES = 60`, the H2-duplication guard); also edited, adding
  `test_agents_md_states_the_session_close_ritual_with_hygiene` and
  `test_harness_profile_points_at_the_session_close_ritual` (the latter's parametrize matrix
  covering every pointer file and station skill note this story touches) for Matrix Test Audit
  coverage of this story's own I/O row (no change to the guard's existing logic). Not covered:
  `_bmad/custom/bmad-build-auto.toml`'s `persistent_facts` content has no automated test anywhere
  in the tree (same as the pre-existing dispatch/spin fact it now sits beside) -- a residual risk,
  not this story's to close.
- `scripts/spec_surface_reconcile.py` / `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md` (`surface:` list, read-only) -- `AGENTS.md`, `GEMINI.md`,
  `.github/copilot-instructions.md` are governed by `spec-pyforge-scribe`, the sole co-governor
  `spec-surface` names for this story's edits; reconciled by appending to
  `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md`
  (never `--write-baseline` from this dispatch, per this story's own constraint -- that stamp is a
  separate pass).
- Prior art: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-46-7-the-docs-name-marshal-dispatch-and-spin-the-execution-front-door.md`
  -- sibling story that named the execution front door in the same docs; this story is its
  session-close counterpart and follows the same Code Map / checkpoint-in-place shape.

## Tasks & Acceptance

**Execution:**
- `AGENTS.md` -- add one unconditional statement naming `scribe capture` as the session-close ritual
  for every harness, with capture hygiene stated ("no secrets, decision-grade facts only") -- the
  single place the docs say so.
- `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/trunk-worktree-pr.mdc`
  -- add a one-line pointer to that `AGENTS.md` statement in each harness's own session-lifecycle
  notes; no restatement of the hygiene rule itself in any pointer file.
- `.claude/skills/pyforge-marshal/.../SKILL.md` and `.claude/skills/pyforge-scribe/.../SKILL.md`
  `[MANUAL:additional-notes]` -- add a one-line pointer, satisfying the Surface's "station skill
  notes" clause for the story's own station (marshal) and the station that owns the `scribe capture`
  command itself (scribe).
- `_bmad/custom/bmad-build-auto.toml` `persistent_facts` -- add a second entry naming the
  session-close ritual, mirroring the existing dispatch/spin entry's style; this is "the same docs
  that name the front door" per Story 46.7's own landing (the front-door fact lives here, not in an
  installer-owned `SKILL.md`, because `bmad-method install --action update` overwrites the latter).
- `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` -- extend
  `test_harness_profile_points_at_the_session_close_ritual`'s parametrize matrix to cover every
  pointer file and station skill note this story touches, not just `GEMINI.md` /
  `.github/copilot-instructions.md`.
- Reconcile: append the changed-paths memlog entry to `spec-pyforge-scribe`'s `.memlog.md` (the
  co-governor `spec-surface` names for `AGENTS.md` / `GEMINI.md` / `.github/copilot-instructions.md`);
  do not run `--write-baseline`.

**Acceptance Criteria:**
- Given a session closes in any harness, when the operator or agent follows the front-door docs,
  then the close ritual is `scribe capture` with decision-grade facts, stated in exactly one place
  (`AGENTS.md`), and capture hygiene is stated there: no secrets, decision-grade facts only.
- Given `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`, when run
  after this story's edits, then it still passes (no new H2 duplicated across `AGENTS.md` and any
  pointer file; every pointer file stays under 60 lines and still names `AGENTS.md`), and its
  parametrize matrix now covers every file this story touched, not only the two it covered before.
- Given `python scripts/spec_surface_reconcile.py`, when run after the memlog append, then it exits
  0 (no unreconciled drift for `AGENTS.md` / `GEMINI.md` / `.github/copilot-instructions.md`).

## Spec Change Log

## Review Triage Log

### 2026-09-24 — Review pass

4 active layers (blind-hunter, edge-case-hunter, verification-gap, intent-alignment) ran in
parallel over the diff vs. baseline `e0b6b3ffa8`. 13 findings total: 6 medium, 6 low, 1 false —
all resolved this pass (7 groups patched, 1 group rejected `false`). `review_loop_iteration`
stays 0 — no `intent_gap` or `bad_spec` route fired.

| # | Finding(s) | Verdict | Route | Fix |
|---|---|---|---|---|
| 1 | BH1, EC1, VG1, IA-b, IA-c, IA-d — the new tests only covered `GEMINI.md` / `.github/copilot-instructions.md`, leaving `CLAUDE.md`, `.cursor/rules/trunk-worktree-pr.mdc`, and both edited `SKILL.md` files with no coverage | medium | patch | Extended `test_harness_profile_points_at_the_session_close_ritual`'s parametrize matrix to all six touched files; docstring updated. |
| 2 | BH2 — spec cited `CAP-192(c)` in a test docstring; the story's own citation form is `CAP-192` (no letter suffix) | low | patch | Dropped the `(c)` from the docstring in `test_agents_md_states_the_session_close_ritual_with_hygiene`. |
| 3 | EC2 — scribe's `SKILL.md` restated the hygiene phrase verbatim, contradicting the AC's "stated in exactly one place (`AGENTS.md`)" | low | patch | Reduced scribe's `SKILL.md` note to a pure pointer, no restatement. |
| 4 | BH3, IA-e — the new `AGENTS.md` paragraph duplicated the pixi command and "never left... auto-memory" phrasing already present in the "Add to it" / "Before a session ends" bullets immediately below it | low | patch | Trimmed the paragraph to the ritual statement + hygiene clause, referencing "Add to it" below instead of restating its command. |
| 5 | BH4 — `declared_low_risk: true` has zero live effect once `classify_review_tier` sees >3 changed files (`_LOW_RISK_MAX_CHANGED_FILES = 3`; this diff touches 11) | low | patch | Removed the inert `declared_low_risk: true` frontmatter field. |
| 6 | VG1 — the diff edits `test_instruction_surface_parity.py`, but `## Tasks & Acceptance` never declared that file as part of Execution scope | low | patch | Added an Execution bullet naming the test-file edit; extended the related AC bullet to say the parametrize matrix now covers every touched file. |
| 7 | IA-a — neither edited `SKILL.md` literally satisfies the Approach's "the same docs that name the front door" (per Story 46.7, that referent is `_bmad/custom/bmad-build-auto.toml`'s `persistent_facts`, not an SKF station `SKILL.md`) | medium | patch | Added a second `persistent_facts` entry to `_bmad/custom/bmad-build-auto.toml` naming the session-close ritual; corrected the Code Map's rationale for the two `SKILL.md` edits and added a Code Map bullet for the `.toml` edit. |
| 8 | IA-f — governance-completeness caveat: worried the surface-drift scan might not be exhaustive across all projects | false | reject | Disproven: `spec_surface_reconcile.py` already scans every project's `surface:` list, not one spec, and returned exit 0 on the current tree both before and after this pass's edits. |

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py -q` — expected: pass (CAP-27 duplication/pointer-shape guard over the exact files this story edits).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 after the `spec-pyforge-scribe` memlog append naming `AGENTS.md` / `GEMINI.md` / `.github/copilot-instructions.md` (S-13.7 guard; never `--write-baseline` from this dispatch).

## Auto Run Result

**Summary:** `scribe capture` is now named once, in `AGENTS.md`, as the harness-neutral
session-close ritual with capture hygiene stated alongside it; every harness profile and the two
relevant station skill notes (marshal, scribe) carry a one-line pointer, and the execution-front-door
fact file (`_bmad/custom/bmad-build-auto.toml`) carries a matching second `persistent_facts` entry.

**Files changed (11):**
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`,
  `.cursor/rules/trunk-worktree-pr.mdc` — the ritual statement + pointers.
- `.claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md`,
  `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md` — station skill note pointers.
- `_bmad/custom/bmad-build-auto.toml` — second `persistent_facts` entry.
- `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` — two new
  tests, one with an extended parametrize matrix.
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md` —
  reconcile entry naming `AGENTS.md` / `GEMINI.md` / `.github/copilot-instructions.md`.
- This spec file — Code Map, Tasks & Acceptance, frontmatter, and this review's own log entries.

**Review findings breakdown:** 13 findings from 4 active layers — 7 groups patched (2 medium, 5
low), 1 group (`false`) rejected with a concrete refutation. No `intent_gap` or `bad_spec` route
fired; `review_loop_iteration` stays 0. Full per-finding table: `## Review Triage Log` above.

**Follow-up review recommended:** `true` — two medium-severity groups were patched this pass
(rule: any `high`, or 2+ `medium`, patched entries force a recommendation). **Specific unverified
risk:** `_bmad/custom/bmad-build-auto.toml`'s `persistent_facts` list has no automated test
anywhere in the tree covering its content (confirmed via a repo-wide grep for
`bmad-build-auto.toml` / `persistent_facts` under every package's `tests/`) — the same gap the
pre-existing dispatch/spin fact already had. A future edit to either entry's wording would go
undetected by any test.

**Verification performed:** all four `## Verification` commands re-run against the fully patched
tree and passed clean: `pyforge-marshal-test` (8635 passed, 1 skipped), `pyforge-deps-test` (130
passed, 3 skipped), `test_instruction_surface_parity.py` (32 passed — includes the two new tests
and the extended matrix), `spec_surface_reconcile.py` (exit 0, no drift).

**Residual risks:** the unverified `persistent_facts` content noted above; and this story does not
itself add coverage for that gap (out of scope — a future story or a `bmad-build-auto.toml`-owning
spec would need to mint that test, per the Code Map's own note).
