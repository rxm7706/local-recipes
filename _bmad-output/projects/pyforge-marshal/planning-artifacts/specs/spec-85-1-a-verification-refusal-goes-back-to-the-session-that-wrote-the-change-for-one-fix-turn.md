---
title: "85.1: A verification refusal goes back to the session that wrote the change for one fix turn"
type: 'feature'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.verify_fix_loop
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "a verification refusal parks the story for the operator (Story 83.10), with no fix turn"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/cursor.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
  - src/shared/packages/pyforge-core/src/pyforge/core/flags.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Dispatch verification is the one authority on whether a finished story's tree is green, but it can only refuse. The session that wrote the change, and still holds its context, never sees the failure; the story is either relaunched as a fresh session or fixed by hand. On 2026-10-03 the Epic 83 campaign re-ran 83.2 three times as full sessions (24.7 + 10.3 + 13.4 min, the third floor-raised to opus by Story 33.6), each refused at verification on the same unformatted line; every other Cursor story refused at verification (83.3, 83.6, 66.2, 84.1) was fixed by hand and re-dispatched for land-only, each fix costing about four more full-suite runs. bmad-build-auto already tells the session to re-run the spec's verification after its review patches; Cursor sessions did not, and reported the checks green.

**Approach:** When dispatch verification refuses after a session finished its work, and the flag `pyforge.marshal.verify_fix_loop` reads on, dispatch gives the change back for exactly one bounded fix turn: it resumes the same harness session when the harness profile declares how to resume one, or otherwise launches a short fix-only session (not bmad-build-auto) in the same worktree. The turn's prompt carries only the failed command(s) and the tail of their output, and asks for the smallest fix, committed. Dispatch then re-verifies once: green lands as today; red parks the story for the operator (Story 83.10). The turn, its prompt size, its wall time and its outcome are journaled.

Ledger key: `85-1-a-verification-refusal-goes-back-to-the-session-that-wrote-the-change-for-one-fix-turn`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-286 (FR-233). Lands on AD-19 (how a harness resumes a session is profile data; no harness-name branch), AD-4 (the decision to run a fix turn, and the prompt built from the failure, are pure `core/` functions) and AD-8 (a fix turn that cannot run, times out or fails re-verification is a named refusal, never a pass). Flagged: `pyforge.marshal.verify_fix_loop`, OFF in production, ON in staging and dev.

## Acceptance Criteria

- Given the flag on and a finished session refused at dispatch verification When dispatch handles the refusal Then it runs exactly one fix turn in the story worktree, re-verifies once, and lands on green
- Given the fix turn's re-verification still refuses When dispatch handles it Then it parks the story for the operator with a finding naming the still-failing command and runs no second turn
- Given a harness profile that declares how to resume a session When the fix turn runs Then it resumes the same session; given a profile that declares none, it launches a fix-only session with the same bounded prompt
- Given the fix turn's prompt When it is built Then it holds the failed command(s) and at most a bounded tail of their output (a policy key, journaled), and never the full diff or any credential
- Given a fix turn that exceeds its wall-clock budget (a policy key) or cannot start When dispatch handles it Then it is stopped, journaled, and the story parks; nothing is reported green
- Given the flag off When verification refuses Then no fix turn runs and the story parks as Story 83.10 does
- Given the fix-turn rule removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Declare the resume form per harness in its profile (AD-19). Add the flag to the flagd tree (`src/platform/config/flags.json` and `flag-overlays.json`) with its owner, story and cleanup clock (steward Story 76.2's metadata). Keep the decision and the prompt rendering in `core/` with no I/O. Journal every fix turn.

**Never:** Never run more than one fix turn per refusal. Never relax, reorder or skip a verification command. Never put a credential or the full diff into the fix prompt. Never branch on a harness name. Never edit `.claude/skills/bmad-build-auto/` (installer-owned).

</intent-contract>

## Design notes (non-binding)

- The resume form is harness-specific CLI surface (for example a resume flag taking the session id the launch recorded); verify each harness's resume against its live CLI before declaring it, and leave a harness without a verified form on the fix-only session.
- Story 83.9 applies `ruff format` before verification, so the fix turn mostly sees mypy, `ruff check` and test failures.
- Once the fix turn is proven, a later story can tell sessions to run only the tests covering their own files and leave the full suite to dispatch, removing duplicated in-session suite runs. Not this story.

## Binding

Parent: `spec-pyforge-marshal` CAP-286 (FR-233).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (evening) entry.
Ledger key: `85-1-a-verification-refusal-goes-back-to-the-session-that-wrote-the-change-for-one-fix-turn`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request, from the verification cost analysis of that date.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
