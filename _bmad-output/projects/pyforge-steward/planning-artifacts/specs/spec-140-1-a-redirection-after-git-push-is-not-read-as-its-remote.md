---
title: '139.1: A redirection after git push is not read as its remote'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 140-1-a-redirection-after-git-push-is-not-read-as-its-remote
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.claude/hooks/pre-shell.py'
  - 'tests/scripts/test_pre_shell_hook.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - .claude/hooks/pre-shell.py
  - docs/governance/guild-roster.json
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-134-2-the-session-hook-reads-every-form-of-a-command-its-rules-name.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-134-2-1`. `_parse_git_push_repository` reads the first token after `git push` that is not an option as the remote, so a redirection (`2>&1`, `> push.log`) is read as one and the push is denied as outward work to a foreign remote. Loosening the session hook is the operator's act, never an agent's.

**Approach:** The operator's patch, which the operator ruled ("Push half only") and applied (`git apply DW-steward-134-2-1-push-half.patch`): `_redirection_span` names how many tokens a redirection takes, and the remote reader skips them. Land it unchanged through this story, with its eight cases, and close the row; the `submit_pr.sh` half is declined (the script is read with the Read tool).

Ledger key: `140-1-a-redirection-after-git-push-is-not-read-as-its-remote`.

### Living CAP citations

- spec-pyforge-steward CAP-5 (the closed `session_denials` list: a denial refuses the command its reason names and nothing else; realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Land the operator's patch byte for byte; run each case on the unpatched hook and record which fail there.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never loosen anything beyond the patch; never let the hook pass reading or running `submit_pr.sh`; never change `session_denials`.
- Never add a flag, a capability or an architecture decision; a change that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-134-2-1` reports that the session hook reads a redirection after `git push` (`git push -h 2>&1`, `git push 2>&1 origin HEAD`) as the remote and denies it as an outward push to a foreign remote
**When** `_parse_git_push_repository` skips each redirection token, and the token after a redirection operator that stands alone, before it reads the remote (the operator's patch, applied by the operator)
**Then** a redirection after `git push` is no longer read as the remote, and a push to a foreign remote written beside a redirection (`git push 2>&1 https://github.com/someone/else.git main`, `git push > push.log <url> main`) is still denied
**And** the other half of the row (reading `submit_pr.sh` is denied) is declined by the same ruling and stays denied, `session_denials` is unchanged, and the row reads resolved

- **AC1 — The hook's whole suite holds, the new cases included.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py -q -n auto
  ```

- **AC2 — The allowed cases fail on the unpatched hook.** Expected: exit 1, run with only the test file changed (recorded in the Spec Change Log).

  ```bash
  pixi run -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py -q -k dw_134_2_1
  ```

- **AC3 — The denial list is unchanged and its forms still hold.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-guild python -m pytest tests/scripts/test_session_denial_forms.py -q
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-5 (the closed `session_denials` list: a denial refuses the command its reason names and nothing else; realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the operator lands the push half of the hook patch); operator rulings of 2026-11-25: "Push half only" (asked what should happen to the DW-steward-134-2-1 patch; the operator applied it with `git apply DW-steward-134-2-1-push-half.patch`) and "Yes, land it".
- Epic: Epic 140, minted with this story.
- Ledger key: `140-1-a-redirection-after-git-push-is-not-read-as-its-remote`.
- Deferred-work row: `DW-steward-134-2-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."140"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the operator lands the push half of the hook patch) and the operator's rulings of the same date. Not implemented.
- 2026-11-25: the operator applied the patch in the primary checkout; this story applied the same file in its worktree, and the two diffs are byte-identical (`cmp` exit 0). AC2 on the unpatched hook: exit 1, 2 failed and 6 passed (the two false denials the row reports, `git push -h 2>&1` and `git push 2>&1 origin main`, fail there; `git push --help 2>/dev/null`, `git push --dry-run origin main > push.log 2>&1` and the four foreign-remote denials already held). With the patch: AC1 exit 0 (584 passed), AC3 exit 0 (17 passed).
- 2026-11-25: closed. The operator's patch landed unchanged and `DW-steward-134-2-1` reads resolved; the `submit_pr.sh` half stays denied by the operator's ruling. The full local `pr-preflight` gates the PR that lands it (branch `hook-push-redirect-2026-11-25`).
