---
title: 'Notice Authoring Workflow (CLI)'
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

**Problem:** Epic 6's `herald notice author <name>` was a write-gated stub (positional `name`
only, prints "would author" and stops). Epic 10 needs the real authoring workflow: full field
capture, interactive prompting for anything missing, and a draft/publish choice -- all still
behind the operator-role gate Epic 6 already wired.

**Approach:** `herald notice author --type --component --what --why --migration [--deadline]
[--reason-link] [--publish]`. `auth.require_operator_role` still runs first, unchanged from Epic
6. Any of `--type`/`--component`/`--what`/`--why`/`--migration` left unset is filled by an
interactive prompt (`cli._prompt`, mirroring `auth.confirm`'s injectable-`reader=input`
convention so a test never blocks on real stdin); `--deadline` prompts too but accepts a blank
answer (optional); `--reason-link` is never prompted (optional, silently absent if unset). The
usual `"Continue? [Y/n]"` confirmation gate runs after prompting, before `notices.author_notice`
is called. `--publish` publishes immediately (equivalent to a following `notice publish` call).

**Judgment call: `--component` is a flag, not the Epic 6 stub's positional `name`.** The task's
own worked example (`herald notice author --type deprecation --component <name> ...`) fixes this
shape; keeping the Epic 6 positional would have made every other new flag's parsing ambiguous
about which token is the component. This intentionally breaks the Epic 6 stub's exact CLI
surface -- expected and pre-authorized: Story 6.1's own AC says the stub exists only until "the
real Moment logic is Epics 8/9/10's scope", and `test_cli_epic6.py`'s notice-author tests are
updated in the same commit to the new flag shape rather than left stale.

## Boundaries & Constraints

**Always:**
- `auth.require_operator_role` is the first statement in `_run_notice_author`'s `operation`
  closure -- unchanged from Epic 6, still the CLI's one write gate.
- A viewer-role (or missing) auth context refuses before any prompting or writing: "unauthorized"
  / "auth context missing" on stderr, exit 1, no notice written.
- Re-authoring an existing **draft** component updates it in place and appends a `"re-authored"`
  revision (Story 10.1's storage semantics); authoring over an existing **published/closed**
  component is refused (`notices.author_notice` raises) -- an operator must close it first or
  choose a different component.
- Declining the `"Continue? [Y/n]"` prompt prints `"aborted: notice not authored"` and writes
  nothing (no index entry, no markdown file).

**Block If:** N/A -- no spike gate, purely local CLI + storage.

**Never:**
- No bypass of the operator-role gate via any argument combination.
- `--reason-link` is never required or prompted -- an evidence link is optional per the original
  AC's own `[--reason-link <url>]` bracket notation.

## I/O & Edge-Case Matrix

| Scenario | Auth | Expected | Exit |
|---|---|---|---|
| All fields on the command line, operator role, confirmed | operator | `"authored notice '<component>' (draft) -> <path>"` | 0 |
| `--publish` set | operator | status `published` in the same call | 0 |
| Missing `--what` | operator | interactive prompt `"what: "`, re-prompts on blank | 0 |
| Missing `--deadline` | operator | prompt, blank accepted (optional) | 0 |
| Viewer role | viewer | `"unauthorized"` on stderr, nothing written | 1 |
| No auth context | none | `"auth context missing"` on stderr | 1 |
| Confirmation declined | operator | `"aborted: notice not authored"`, nothing written | 0 |
| Re-author an already-published component | operator | `HeraldError` -> nonzero exit, message names the status | 1 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- edit -- `notice author`
  subparser flags (`--type`/`--component`/`--what`/`--why`/`--migration`/`--deadline`/
  `--reason-link`/`--publish`, replacing the Epic 6 positional `name`), `_run_notice_author`
  (now composes `notices.author_notice`), the new `_prompt` helper.
- `src/shared/packages/pyforge-herald/tests/test_cli_epic6.py` -- edit -- the two notice-author
  tests updated to the new flag shape (gate-refusal + happy-path), `weekly-update` now a
  `--component` value instead of a positional.
- `src/shared/packages/pyforge-herald/tests/test_cli_notice_epic10.py` -- create (shared with
  Story 10.4/10.6) -- write-gate coverage on every notice write subcommand, the author happy
  path, confirmation-declined no-op, and interactive-prompting coverage (monkeypatches
  `cli._prompt` directly -- see Design Notes).

## Design Notes

**Why monkeypatch `cli._prompt` in tests instead of `builtins.input`?** `_prompt`'s default
`reader=input` parameter is bound to the real `input` function object once, at function
*definition* time (module import) -- the same convention `auth.confirm`'s own `reader=input`
default already uses. Monkeypatching `builtins.input` afterward does not change an already-bound
default parameter, so a test exercising the interactive-prompt path patches `cli._prompt` itself
(the bound function `_run_notice_author` actually calls), exactly mirroring how existing tests
patch `auth.confirm` rather than `builtins.input` for the confirmation prompt.

**Why does `--deadline`'s prompt accept blank but `--what`/`--why`/`--migration` don't?** The
Notice schema's `deadline` field is `str | None` (Story 10.1) -- a notice can legitimately have no
deadline (e.g. a `fix` notice) -- while `what`/`why`/`migration` are the substantive content the
whole notice exists to convey; an empty `what` would be a useless notice. `_prompt`'s
`required=False` parameter encodes exactly this distinction, reused as-is by `--reason-link`'s
absence of any prompt at all (a link is opt-in, not merely optional-with-a-default).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 595 passed, 2 skipped.
- `ruff format --check` / `ruff check` -- clean.

**Manual checks:**
- `HERALD_TOKEN=operator:x herald notice author --type deprecation --component demo --what w
  --why w --migration m <<< y` -- exit 0, draft written under `notices/`.

## Spec Change Log

## Review Triage Log
