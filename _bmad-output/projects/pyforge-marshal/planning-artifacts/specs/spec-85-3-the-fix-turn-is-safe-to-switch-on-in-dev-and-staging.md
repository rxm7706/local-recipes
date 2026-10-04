---
title: "85.3: The fix turn is safe to switch on in dev and staging"
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
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-1-a-verification-refusal-goes-back-to-the-session-that-wrote-the-change-for-one-fix-turn.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verify_fix.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Before the fix turn can run on operator hosts, the safety findings from the two Story 85.1 reviews must close: redaction misses `DATABASE_PASSWORD=`, `AWS_SECRET_ACCESS_KEY=`, short `sk-ant-` keys, YAML and JSON `password:`, `Authorization: Basic`, URL passwords containing `/`, and it runs after the tail is cut, so a cut mid-URL leaks part of a credential; the prompt travels on argv (visible in `ps`) (M7). The timeout kill sends SIGTERM to the leader only, with no bounded wait, SIGKILL or reap (M4). No publisher heartbeat is sent during the turn or the second verification, so the portal marks the run `heartbeat_lost` after 300 s, while the journal heartbeat writes every second (M3). `--continue` resumes the most recent session, not this one, and the `{{session_id}}` token is always empty (L1); the resolved profile is not compared with the launch profile before resume (L3); MRS-GATE-018 still feeds a pseudo-command into the prompt (L4). An unreadable or malformed `flags.json` journals nothing (M2). Unset `PYFORGE_ENVIRONMENT` reads `dev`, so turning the flag on in dev turns it on for every operator host (N8).

**Approach:** Close those findings, then set the flag ON in dev and staging (OFF in production), as the CAP-286 rollout says.

Ledger key: `85-3-the-fix-turn-is-safe-to-switch-on-in-dev-and-staging`.
Type / Effort / Deps: feature / M / S-85.2.

### Living CAP citations

- `spec-pyforge-marshal` CAP-286 (FR-233), split by operator ruling 2026-10-03 after two independent reviews of Story 85.1; same flag `pyforge.marshal.verify_fix_loop`.

## Acceptance Criteria

- Given output tails carrying each credential shape above, including one cut mid-URL When the tail is journaled and the prompt is built Then no credential survives, and the prompt is passed by file or stdin, never argv
- Given a fix session that ignores SIGTERM and has children When its budget runs out Then its process group is terminated, waited on, killed and reaped, and the outcome is journaled
- Given a fix turn of more than 300 s When the portal sweeps Then the run is not `heartbeat_lost`; the journal heartbeat writes at the tick rate
- Given a profile that declares resume When the fix turn runs Then it resumes the recorded session id with the launch profile's own harness, else it launches a fix-only session
- Given an unreadable or malformed flag tree When verification refuses Then a warning is journaled and no turn runs
- Given the change When the flag is read with `PYFORGE_ENVIRONMENT` unset, `dev`, `staging` and `production` Then it reads on, on, on and off, and pyforge-core's `test_flags.py` and Platform CI's `test_openfeature_file_flags.py` pin that

## Boundaries & Constraints

**Always:** Redact before truncating. Keep production OFF. Fix each defect where it lives and pin it with a test that fails without the fix.

**Never:** Never put a prompt or a credential on argv. Never resume a session other than the one recorded at launch.

</intent-contract>

## Design notes (non-binding)

- Both live CLIs offer a session-id form (`claude --session-id/--resume <id>`, `cursor-agent --resume [chatId]`); verify the form on each before declaring it, else keep fix-only.
- Story 80.1's `_WaitHeartbeat` is the pattern for the publisher heartbeat during a wait.
- Deploy note: OFF in production relies on `PYFORGE_ENVIRONMENT=production` being set on production hosts.

## Binding

Parent: `spec-pyforge-marshal` CAP-286 (Story 85.1, split 2026-10-03).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (85.1 split) entry.
Ledger key: `85-3-the-fix-turn-is-safe-to-switch-on-in-dev-and-staging`.
Ledger status at mint: `backlog`.
Deps: S-85.2.
Minted 2026-10-03 at the operator's request (split 85.1, keep Cursor).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
