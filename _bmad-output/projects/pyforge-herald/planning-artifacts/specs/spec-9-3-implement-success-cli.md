---
title: 'Implement Success CLI (review/publish/list/get)'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 6.3 (Epic 6) shipped `herald success` with `success publish <claim-id>`
as a write-gated *stub* -- `auth.require_operator_role` runs, then the handler prints
"authorized: would publish" and does nothing real. `herald success` with no subcommand
prints a "not yet implemented" placeholder. Epic 9's own Story 9.3
(`epics-with-stories.md` lines 680-733) specs the real CLI surface: `review`, `publish`
(now actually persisting), `list`, and `get`, all against a `Claims` database table via an
ORM.

**Approach:** Replace the two Epic 6 placeholders with real behavior, wired to `claims.py`
(Story 9.1) instead of a database. `herald success review <claim-id>` (also specified by
Story 9.2's own AC) displays a claim's evidence read-only. `herald success publish
<claim-id> [--thesis "..."]` keeps Story 6.3's exact gate (`auth.require_operator_role`
before anything else, then `auth.confirm`) and now calls `claims.publish`, which validates
every evidence link (Story 9.5's wiring) before persisting. `herald success list
[--status draft|published|closed]` (also `herald success` bare, unchanged entry point)
and `herald success get <claim-id>` are both read-only, reusing the existing
`--json`/`--date-range`/`--station` global flags already on the `success` parser (Epic 6,
Story 6.2).

## Boundaries & Constraints

**Always:**
- `herald success review <claim-id>`: prints project name, status, shipped date, thesis,
  and each evidence entry's validated/unvalidated state; if the claim is still `draft`,
  prints the `herald success publish <id> --thesis "..."` follow-up. Read-only -- never
  calls `auth.require_operator_role`.
- `herald success publish <claim-id> [--thesis "..."]`: **keeps Story 6.3's exact gate
  order** -- `auth.require_operator_role(auth.resolve_auth_context(), ...)` runs before
  anything else in the closure, then `auth.confirm(...)`, then (this story's addition)
  `claims.publish(...)`. A caller without the `operator` role never reaches the real
  publish logic, same as the Epic 6 stub.
- `herald success list [--status draft|published|closed]` and bare `herald success` (no
  subcommand, unchanged since Epic 6): both call the same `_run_success_list`, filtered by
  `--status` (via `getattr(args, "status", None)` so the bare form -- whose namespace never
  set `status` -- still works) and the existing `--date-range` (matched against
  `shipped_date`). `--json` emits one `claims.to_dict(...)` object per line (NDJSON-shaped,
  matching the AC's "NDJSON with `--json`").
- `herald success get <claim-id>`: full detail (every `Claim` field, evidence, edit
  history) in either plain-text or `--json`.
- Every handler resolves `.herald/claims.json` via the `success` parser's own
  `--repo-root` (Story 9.2) -- consistent across `create`/`review`/`publish`/`list`/`get`/
  `validate`.

**Block If:** N/A -- publish's evidence validation is Story 9.5's live-network concern,
covered there; this story's own tests stub `evidence.validate_for_publish` throughout.

**Never:**
- `publish` never republishes an already-`published`/`closed` claim in place --
  `claims.publish` raises `errors.ClaimStateError`, surfaced as exit 1 with the error type
  named on stderr (`dispatch`'s existing rendering, unchanged).
- `publish` never persists with an empty thesis -- `claims.publish` raises `HeraldError`
  when neither `--thesis` nor the claim's existing thesis is set.
- No interactive `$EDITOR` launch for multi-line thesis entry (the original AC's "CLI
  opens text editor... for multi-line input") -- `--thesis "..."` is a single flag value;
  an operator composing a longer thesis writes it elsewhere and passes it as one string.
  No AC-blocking need demonstrated yet for a `$EDITOR` subprocess dependency.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Notes |
|---|---|---|---|
| `review`, unknown claim | bogus id | exit 1, `ClaimNotFoundError` on stderr | |
| `review`, no auth | `HERALD_TOKEN` unset | exits 0 -- read-only | |
| `publish`, viewer role | `HERALD_TOKEN=viewer:tok` | exit 1, `unauthorized` | claim stays `draft` on disk |
| `publish`, no auth context | `HERALD_TOKEN` unset | exit 1, names `HERALD_TOKEN`/`/design-login`-style remediation | Story 6.3's unchanged message |
| `publish`, operator + confirm declined | `auth.confirm` returns `False` | exit 0, "aborted", nothing published | |
| `publish`, operator + confirmed, valid evidence | operator role, `--thesis` | exit 0, claim `status="published"` on disk | |
| `publish`, broken evidence | `validate_for_publish` raises | exit 1, "Evidence link broken" on stderr | claim stays `draft` |
| `publish`, no thesis anywhere | no `--thesis`, claim has none | exit 1, "thesis" named on stderr | |
| `publish`, already published | second `publish` on same id | exit 1, `ClaimStateError` on stderr | |
| `list --status draft` | mixed draft/published claims | only drafts printed | |
| `list --json` | any claims | one JSON object per line, each a `to_dict()` shape | |
| bare `success` | no claims yet | "success: no claims found" | preserves Epic 6's exit-0 read-only contract |
| `get <id> --json` | valid id | one JSON object, `to_dict()` shape | |
| `get`, unknown id | bogus id | exit 1 | |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `_run_success_review`,
  `_run_success_publish` (real, was Story 6.3's stub), `_run_success_list` (real, was Story
  6.1's placeholder), `_run_success_get` (new); `success list`/`success get` subparsers;
  `_success_claims_path` helper shared by every `success` handler.
- `src/shared/packages/pyforge-herald/tests/test_cli_epic6.py` -- edit --
  `test_success_publish_with_operator_role_proceeds_to_the_real_publish` and
  `test_success_publish_confirmation_declined_takes_no_action` updated from asserting the
  old "authorized: would publish" stub text to the new real-publish behavior (both now
  seed a real draft claim via `claims.create` first).
- `src/shared/packages/pyforge-herald/tests/test_cli_success.py` -- create (shared with
  Stories 9.2/9.5) -- `review`/`publish`/`list`/`get` coverage.

## Design Notes

**Judgment call: `review` never inlines an interactive publish prompt.** The original AC
describes `review` itself prompting "Publish? [Y/n]" and proceeding. This implementation
keeps `review` strictly read-only and directs the operator to run `success publish`
separately. Rationale: `auth.require_operator_role` is Story 6.3's one gate boundary for
every write subcommand in this package; folding a publish path into `review` too would
create a second entry point that has to independently remember to call the gate, doubling
the surface a future bug (or bypass) could hide in. Keeping `publish` as the sole path
through the gate means there is exactly one place to verify it is enforced -- which is
also why this story's own tests re-verify Story 6.3's gate-before-work ordering rather than
assuming it still holds.

**Judgment call: no `$EDITOR` launch.** Documented in Boundaries & Constraints. A future
story can add it without touching this one's contract -- `--thesis` stays valid input
either way.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 611 passed, 2 skipped
  (whole-package total).
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `herald success publish <id> --thesis "x"` without `HERALD_TOKEN` set -- refused,
  `.herald/claims.json` unchanged (confirmed via `git diff`-equivalent byte comparison in
  the test suite, not by hand for this report).

## Spec Change Log

## Review Triage Log
