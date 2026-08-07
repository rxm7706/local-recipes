---
title: 'Story 4.2: The declared ceiling is one command away'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 4.1 makes the ceiling machine-readable, but "machine-readable" still means opening a YAML file by hand today.

**Approach:** `format_ceilings` renders `load_budget`'s own output (Story 4.1) for `steward budget show` — a human-readable line per ceiling, or `--json` for the same data machine-readably. Mirrors `format_inventory`'s (`keys.py`, Story 1.5) and `format_environments`'s (`provision.py`, Story 3.3) identical shape: `as_json=True` → a JSON array (`[]` for none, never a misleading `0`), `as_json=False` → a stable text line (or a plain sentence for none).

## Boundaries & Constraints

**Always:**
- `--json` output is a JSON array, one object per ceiling — `[]`, not `null`/`{}`, for "no ceiling ever declared" (the correct machine-parseable empty state, matching `format_inventory`'s `[]`-not-`{}` precedent for an equivalent empty-list case).
- Text output for "no ceiling ever declared" is a clear sentence ("no ceiling has ever been declared"), never a bare `0` or an empty string a caller could misread as "the ceiling is zero."
- `show` is a pure read of `.steward/budget.yaml` — no write under any outcome.

**Block If:** N/A — `show` has no invalid-input state of its own (no flags beyond `--json`, which argparse itself validates); its only failure mode is a corrupt `.steward/budget.yaml` (`BudgetError`, propagated as a duty-level failure).

**Never:**
- No second rendering implementation — `format_ceilings` is the only place `show`'s text/JSON shape is decided.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| A ceiling was declared (Story 4.1) | `steward budget show` | One human-readable line: `<amount> <currency>/<period> (declared <timestamp>)` | No error |
| Same, `--json` | `steward budget show --json` | A JSON array with the identical amount/currency/period/declared_at fields | No error |
| No ceiling ever declared | `steward budget show` | "budget show: no ceiling has ever been declared" — not a crash, not `0` | No error (`ok=True`) |
| Same, `--json` | `steward budget show --json` | `[]` | No error |
| Corrupt `.steward/budget.yaml` | `steward budget show` | Clear error naming the malformed field | `BudgetError` → `DutyResult(ok=False, ...)` |
| Same, `--json` | `steward budget show --json` | The SAME error, rendered as a parseable JSON object (`{"error": "..."}`), never plain text a `--json` caller's `json.loads()` would choke on | `BudgetError`, rendered via `_render_error` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/budget.py` -- EDIT: `format_ceilings`, `BudgetDuty.run`'s `show` branch, `BudgetDuty._render_error` (new — see Review Triage Log)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- EDIT: `show`'s `--json` flag (declared alongside Story 4.1's `set --cap` in `_add_budget_subparsers`)
- `src/shared/packages/pyforge-steward/tests/conformance/test_budget_show.py` -- NEW: full I/O matrix, primitive + CLI level, incl. the `--json`-on-error-path regression test

## Tasks & Acceptance

**Execution:**
- [x] `budget.py` -- `format_ceilings(ceilings, *, as_json) -> str`
- [x] `budget.py` -- `BudgetDuty.run`'s `show` branch; `_render_error` added so `show`'s error path honors `--json` too (review finding, see below)
- [x] `cli.py` -- `show --json` flag
- [x] `tests/conformance/test_budget_show.py` -- full matrix incl. `test_budget_show_json_via_cli_renders_a_load_error_as_json_not_plain_text`

**Acceptance Criteria:**
- Given a ceiling declared via Story 4.1, when `steward budget show` is run, then it prints the ceiling in a human-readable form, and `steward budget show --json` prints the same data as machine-readable JSON.
- Given no ceiling has ever been declared, when `steward budget show` is run, then it reports that clearly (not a crash, not a misleading zero).

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 1
- defer: 0
- reject: 0
- **Patch (found live in this session, not deferred)**: the class of bug the task brief explicitly named — Epic 3's own closing review found and fixed `ProvisionDuty`'s identical gap (`--list --json` against a malformed `pixi.toml` fell back to a plain-text summary). The first draft of `BudgetDuty.run` had the SAME shape: `show`'s happy path called `format_ceilings(..., as_json=ns.json)`, but the `except BudgetError` branch below it returned a bare `str(exc)` regardless of `ns.json` — so `budget show --json` against a corrupt `.steward/budget.yaml` would emit unparseable plain text on stderr to a caller that specifically asked for JSON. Fixed by adding `BudgetDuty._render_error` (mirrors `ProvisionDuty._render_error`'s exact shape: `getattr(ns, "json", False)` → `json.dumps({"error": message})` or the plain message) and routing both `CapParseError` and `BudgetError` through it. Regression-tested by `test_budget_show_json_via_cli_renders_a_load_error_as_json_not_plain_text`, which plants a `.steward/budget.yaml` missing a required `amount` field and asserts the stderr output is `json.loads()`-able and contains an `"error"` key.
- **Checked**: `set`'s and `check`'s error paths correctly stay plain text through the SAME `_render_error` call — `getattr(ns, "json", False)` returns `False` for both (neither verb's subparser declares `--json`), so there is no flag value for their error paths to silently disagree with; `_render_error` is one shared function, not two, so this can't drift.
- **Checked**: the empty-state distinction (`[]` for JSON, a sentence — never `0` — for text) by execution in both `format_ceilings` unit tests and the CLI-level "never declared" tests, not just by reading the function.

**Follow-up review recommendation: false** — the one real finding was caught and fixed within this same self-review pass, with a regression test proving the fix.

## Design Notes

**Why `_render_error` lives on `BudgetDuty` rather than as a free function in `budget.py`.** Mirrors `ProvisionDuty._render_error`'s exact placement (a `@staticmethod` on the duty class) — `budget.py` follows the same precedent Epic 3 already established for this identical problem shape, rather than inventing a differently-shaped fix for what is structurally the same bug.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass
- `pixi run --frozen -e pyforge-steward steward budget show` -- expected: reports the real repo's current declared-ceiling state (or "no ceiling has ever been declared" if none)

**Results (2026-08-07):**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 197 passed (full Epic 4 suite, run together with Stories 4.1/4.3 in the same session).
- **Live verification (real, not faked):** `steward budget show` was run against this repo's REAL, checked-out state (no `.steward/budget.yaml` exists in this worktree prior to this session's tests, all of which use `tmp_path`-scoped monkeypatched roots — no real repo-root `.steward/budget.yaml` was created by this story's own test suite) -- output: `budget show: no ceiling has ever been declared`, exit 0, matching the real repo state.
