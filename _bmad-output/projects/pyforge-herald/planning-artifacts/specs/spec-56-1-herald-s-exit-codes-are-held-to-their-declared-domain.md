---
title: '56.1: Herald''s exit codes are held to their declared domain'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 56-1-herald-s-exit-codes-are-held-to-their-declared-domain
spec: spec-pyforge-herald
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-herald/tests/meta/test_exit_codes_match_the_exit_declaration.py'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/auth.py'
  - 'src/shared/packages/pyforge-herald/tests/unit/test_auth.py'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Herald's exit codes were left out of the one exit-code declaration. The operator-role refusal says to configure with `herald auth login`; `TOP_LEVEL_COMMANDS` has no `auth`.

**Approach:** Add a package-half meta-test holding `errors.exit_code_for`, its map and its default to the `herald` domain. Change the refusal text to name the two places `resolve_auth_context` reads, and the test that pinned the old wording.

Ledger key: `56-1-herald-s-exit-codes-are-held-to-their-declared-domain`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (amended 2026-11-26; the declaration this story binds to).
- spec-pyforge-steward:CAP-184 (the declaration; amended 2026-11-26), spec-pyforge-herald CAP-62 (the public contract; realized, no text change) and CAP-13 (the operations surface; realized, no text change).

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every exit number the station returns today.

**Never:**
- Never change an exit number.
- Never edit the SKF-compiled station skill.

## Acceptance Criteria

**Given** herald's exit codes are declared only in herald, and the role refusal names `herald auth login`, which is not a command
**When** the meta-test is added and the refusal names `HERALD_TOKEN` and `~/.herald/config`
**Then** the test fails when the error map or the default code differs from the `herald` domain, and `test_auth.py` fails when the refusal names a `herald auth` command
**And** no exit number changes, and a refused write still raises `OperatorAuthorizationError` and exits 1

- **AC1 — Herald's meta-test and auth tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_exit_codes_match_the_exit_declaration.py src/shared/packages/pyforge-herald/tests/unit/test_auth.py -q
  ```

- **AC2 — Herald's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-test
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent and not the implementer's reasoning. Fourteen findings; all accepted and applied in the same change. For this story: the meta-test also holds every integer literal `cli.py` returns (usage, flag-off, failure, interrupt) to the domain; the refusal names the JSON form `~/.herald/config` must have; `docs/how-to/troubleshoot-herald-moments.md` quotes the new message.
