---
title: '139.1: The session hook reads the commands inside a substitution'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 139-1-the-session-hook-reads-the-commands-inside-a-substitution
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.claude/hooks/pre-shell.py'
  - 'tests/scripts/test_pre_shell_hook.py'
context:
  - .claude/hooks/pre-shell.py
  - docs/governance/guild-roster.json
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-134-2-the-session-hook-reads-every-form-of-a-command-its-rules-name.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** found 2026-11-25 by the analysis of `DW-steward-134-2-1`'s patch, which probed the hook on `main`: `cat $(bash scripts/submit_pr.sh)` and its backtick form are allowed, because `_split_respecting_quotes` keeps a substitution inside one token and no rule reads into it. The same holds for every rule that reads `ctx.subcommands`.

**Approach:** Add a linear scanner for the bodies of `$(...)` (balanced, with nested parentheses and quotes respected), backticks, `<(...)` and `>(...)` outside single quotes, skipping a backslash-escaped opener and an arithmetic `$((`. Strip here-document bodies before scanning. Feed each body to `normalised_subcommands` at the next depth (its existing cap of 8 bounds the recursion), so every rule sees the inner commands beside the outer ones. Write the failing cases first.

Ledger key: `139-1-the-session-hook-reads-the-commands-inside-a-substitution`.

### Living CAP citations

- spec-pyforge-steward CAP-5 (the closed `session_denials` list: each denial refuses every form of the command its reason names; realized, no text change) and CAP-165 (the protected refs; realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Write each new case first and see it fail on the unchanged hook; record that run in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never loosen a rule or change `session_denials`; never read a here-document body as a command line.
- Never add a flag, a capability or an architecture decision; a change that would need one stops and is reported.

## Acceptance Criteria

**Given** the session hook splits a command line on `&&`, `||`, `;`, `|` and newlines and reads a `bash -c` payload, but never the command inside `$(...)`, backticks, `<(...)` or `>(...)`, so `cat $(bash scripts/submit_pr.sh)`, its backtick form and `x=$(pixi add numpy)` pass a hook that denies the same command written plainly
**When** the hook also reads the body of every command substitution and process substitution outside single quotes and outside here-document bodies, and gives each body the rules a plain command gets
**Then** each such form is denied with the reason its plain form gets, a nested substitution is read at every level, and a substitution in single quotes, an escaped `\$(`, an arithmetic `$((...))` or a here-document body (a commit message or PR body that only mentions a command) is still allowed
**And** every existing case of `tests/scripts/test_pre_shell_hook.py` keeps its result and `session_denials` is unchanged: the change only adds denials

- **AC1 — The hook's whole suite holds, the new cases included.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py -q -n auto
  ```

- **AC2 — The new cases fail on the unchanged hook.** Expected: exit 1, run with only the test file changed (recorded in the Spec Change Log).

  ```bash
  pixi run -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py -q -k substitution
  ```

- **AC3 — The denial list is unchanged and its forms still hold.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-guild python -m pytest tests/scripts/test_session_denial_forms.py -q
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-5 (the closed `session_denials` list: each denial refuses every form of the command its reason names; realized, no text change) and CAP-165 (the protected refs; realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the session hook reads the commands inside a substitution); operator rulings of 2026-11-25: "Fix it as a Story" (asked whether the hook's gap inside command substitution should be fixed) and "do the hook-gap tightening story".
- Epic: Epic 139, minted with this story.
- Ledger key: `139-1-the-session-hook-reads-the-commands-inside-a-substitution`.
- Deferred-work row: none; found by the analysis of `DW-steward-134-2-1`'s patch.
- Surface: `marshal-policy.toml` `[epic_surfaces]."139"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the session hook reads the commands inside a substitution) and the operator's rulings of the same date. Not implemented.
- 2026-11-25: AC2 run first, with only the test file changed: exit 1, 10 failed and 7 passed (the six allowed forms, and `echo $(echo ')' ; pixi add numpy)`, which the `;` split already exposed). Then the fix: `_without_heredoc_bodies` and `_substitution_bodies` beside `_heredoc_bodies`, and `normalised_subcommands` reads each body at the next depth. AC1 exit 0 (561 passed, the 544 of `main` plus 17); AC3 exit 0 (17 passed). Timed on adversarial input: 2,000 nested `$(` 0.016 s, an unterminated backtick over 200,000 characters 0.67 s, 20,000 substitutions 0.11 s, a 50,000-line here-document 0.18 s.
- 2026-11-25: session lead: AC3 corrected to `-e pyforge-guild`. As minted it named `-e pyforge-ci`, where `test_session_denial_forms.py` skips (it needs PyYAML, which only `scripts-lib-test`'s environment carries); the criterion is unchanged.
