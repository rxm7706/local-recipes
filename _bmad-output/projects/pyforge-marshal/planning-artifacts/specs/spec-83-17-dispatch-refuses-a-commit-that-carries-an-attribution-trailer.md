---
title: "83.17: Dispatch refuses a commit that carries an attribution trailer"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verification.py
  - .pre-commit-config.yaml
  - scripts/commit_msg_hook.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-03 a Cursor session's commit on `dispatch/pyforge-mason/27.1` (`dad089fe03`) carried `Co-authored-by: Cursor <cursoragent@cursor.com>`. AGENTS.md forbids AI attribution in commit messages and the `commit-msg` hook refuses it, but the session's commit did not go through the hook, and dispatch verification never reads commit messages, so a `--merge` landing would have put the trailer on `main`. The operator could not rewrite the branch's history.

**Approach:** Dispatch verification runs the same check as the `commit-msg` hook (`scripts/commit_msg_hook.py`) over every commit on `origin/main..HEAD` and refuses, naming each commit, before it pushes or lands. Where the Cursor harness profile can switch off the CLI's commit attribution, the dispatch launch does so.

Ledger key: `83-17-dispatch-refuses-a-commit-that-carries-an-attribution-trailer`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- the dispatch verification gate (Stories 79.2, 83.2). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a story branch with a commit whose message carries `Co-authored-by:` or another AI-attribution line the hook refuses When dispatch verifies it Then verification refuses (MRS-GATE-001 or a new named code) naming the commit, and nothing is pushed or landed
- Given a branch whose commits pass the hook When dispatch verifies it Then this check passes
- Given the check removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Reuse `scripts/commit_msg_hook.py`'s rule; one owner of the pattern.

**Never:** Never rewrite a branch's history automatically; the refusal tells the operator which commit to fix.

</intent-contract>

## Binding

Parent: AGENTS.md § Policy (commit messages carry no AI attribution).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, latest) entry.
Ledger key: `83-17-dispatch-refuses-a-commit-that-carries-an-attribution-trailer`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
