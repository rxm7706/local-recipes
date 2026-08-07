---
title: 'Story 4.3: Asking "am I under budget?" never lies'
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

**Problem:** v1 has no metered spend source wired in anywhere (PRD explicit non-goal: no Kubecost/OpenCost/Infracost-class integration). A `budget check` command that silently defaulted to "pass" (or fabricated a number) when there is nothing to compare against would be worse than no command at all — a script trusting it could act on a lie.

**Approach:** `steward budget check` ALWAYS reports "no metered spend source configured," via the dedicated `cli.EXIT_BUDGET_NOT_CONFIGURED` exit code — regardless of whether a ceiling was ever declared (Story 4.1). AD-6's triad (not-configured / under-budget / over-budget) is honored structurally: `EXIT_BUDGET_NOT_CONFIGURED` is a NEW, distinct constant, never colliding with `EXIT_OK`(0, hypothetical future "under budget") or `EXIT_FAILED`(1, a generic duty failure that must stay distinguishable from a specific "over budget" a later story would add). `cli.main()` gains a small, generic exit-code-override mechanism (`DutyResult.details["exit_code"]`) rather than a budget-specific special case, so any future duty needing a documented non-binary exit code reuses the same seam — the duty still never calls `sys.exit()` itself (AD-8 stays fully intact; `main()` remains the sole ACTOR on the exit code, a duty only REQUESTS one via its own returned data).

## Boundaries & Constraints

**Always:**
- `budget check`'s output and exit code are IDENTICAL whether or not a ceiling has been declared — `_run_check` does not call `load_budget` at all, structurally proving indifference to that state rather than merely documenting it.
- `EXIT_BUDGET_NOT_CONFIGURED` is a fixed, documented integer (`3`), distinct from `EXIT_OK`(0), `EXIT_FAILED`(1), `EXIT_USAGE`(2, argparse's own), `EXIT_INTERRUPTED`(130), and `EXIT_INTERNAL`(70) — no collision with any existing documented code.
- No cloud-cost SDK or Kubecost/OpenCost/Infracost-class client import exists ANYWHERE in the package (not just `budget.py`) — proven by `tests/meta/test_invariants.py::test_no_cost_integration_sdk_imported_in_budget`, an AST import-scan (not a text/docstring grep — `budget.py`'s own module docstring and its `_NOT_CONFIGURED_MESSAGE` NAME every one of these products in prose, which a naive text scan would misflag).

**Block If:** N/A — `check` takes no flags and has no invalid-input state; it is a pure, fixed report.

**Never:**
- No real spend-comparison logic anywhere in `budget.py` — that is explicitly future-story scope, gated on a real metered spend source existing.
- No duty module (including `budget.py`) calls `sys.exit()` — the exit-code override travels through `DutyResult.details`, read and acted on only inside `cli.main()` (already pinned repo-wide by `test_no_duty_module_calls_sys_exit`, which this story does not need to touch — it already covers `budget.py` for free once the file exists).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No ceiling ever declared | `steward budget check` | "no metered spend source configured", exit `EXIT_BUDGET_NOT_CONFIGURED` (3) | `DutyResult(ok=True, details={"exit_code": 3})` |
| A ceiling IS declared (Story 4.1) | `steward budget check` | IDENTICAL output/exit code to the row above — the ceiling's presence changes nothing | Same |
| Codebase reviewed for imports | any state | No cloud-cost-SDK or Kubecost/OpenCost/Infracost client import anywhere in `budget.py` (or the package) | Proven by AST scan, not by inspection alone |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/budget.py` -- EDIT: `_NOT_CONFIGURED_MESSAGE`, `_run_check`, `BudgetDuty.run`'s `check` branch
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- EDIT: `EXIT_BUDGET_NOT_CONFIGURED` constant, `check` verb wired in `_add_budget_subparsers`, `main()`'s generic `details["exit_code"]` override read
- `src/shared/packages/pyforge-steward/tests/conformance/test_budget_check.py` -- NEW: both declared/undeclared rows, exit-code distinctness, message content
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- NEW: `test_no_cost_integration_sdk_imported_in_budget` (AST import-scan)

## Tasks & Acceptance

**Execution:**
- [x] `cli.py` -- `EXIT_BUDGET_NOT_CONFIGURED = 3`, documented distinct from `EXIT_OK`/`EXIT_FAILED`/`EXIT_USAGE`/`EXIT_INTERRUPTED`/`EXIT_INTERNAL`
- [x] `cli.py` -- `main()` reads `result.details.get("exit_code")` as a generic override (still sole-owned: `main()` is the only place that RETURNS a code; a duty only requests one via data, never `sys.exit()`)
- [x] `budget.py` -- `_run_check`, `BudgetDuty.run`'s `check` branch (ignores `load_budget` entirely — structural indifference to ceiling state)
- [x] `cli.py` -- `check` verb wired (no flags)
- [x] `tests/conformance/test_budget_check.py` -- both rows + exit-code distinctness + message assertion
- [x] `tests/meta/test_invariants.py` -- `test_no_cost_integration_sdk_imported_in_budget`

**Acceptance Criteria:**
- Given no metered spend source is wired into Steward (true for all of v1 — per the PRD's explicit non-goal on Kubecost/OpenCost/Infracost-class integration), when `steward budget check` is run, regardless of whether a ceiling was declared (Story 4.1), then it prints "no metered spend source configured" and exits with a dedicated, documented exit code distinct from a hypothetical future "under budget" (0) or "over budget" (non-zero-and-different) code.
- Given the codebase at the end of this story, when it is reviewed for imports, then no cloud-cost-SDK or Kubecost/OpenCost/Infracost client import exists anywhere in `budget.py` — the honest-stub property is structural, not just behavioral.

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- **Checked**: "regardless of whether a ceiling was declared" is proven by EXECUTION, not just by `_run_check` not calling `load_budget` — `test_budget_check_always_reports_not_configured_with_no_ceiling_declared` and `test_budget_check_always_reports_not_configured_even_with_a_ceiling_declared` both assert the IDENTICAL exit code from the IDENTICAL command, one with a prior `budget set` in the same test and one without.
- **Checked**: the AST-scan test's banned-module list intentionally over-includes plausible cost-SDK names beyond the AC's literal three examples (Kubecost/OpenCost/Infracost) — `boto3`/`google`/`azure`/`stripe` etc. — because a future accidental import of ANY cloud billing API would violate the same "honest stub" property the AC states, even if it isn't literally one of the three named products. Scoped the scan to the WHOLE `steward/` package (not just `budget.py`) for the same reason `test_no_third_party_provider_api_client_imported` scans the whole package rather than just `keys.py` — a helper module quietly carrying the import would be just as much of a structural lie.
- **Checked**: exit-code plumbing doesn't weaken AD-8. Confirmed `budget.py` contains no `sys.exit`/`sys` import at all (grep + the existing repo-wide `test_no_duty_module_calls_sys_exit` AST test, which already covers every file under `steward/` including this new one) — the override is pure data (`DutyResult.details`) that `cli.main()` alone reads and acts on; a duty requesting a code and a duty enforcing one are kept structurally distinct.
- **Checked**: `result.ok=True` for the not-configured report (rather than `False`) is a deliberate choice — "no data" is not a Steward-level failure (the duty ran correctly and told the truth), so the happy-path stdout stream is correct for it; the exit-code OVERRIDE is what actually makes a calling script able to tell "no data" apart from "ok"/"fail" without needing to also inspect the `ok` field. Documented in `_run_check`'s module-level comment block so a future reader doesn't "fix" this into `ok=False` and accidentally collapse the not-configured/failed distinction back down to two states.

**Follow-up review recommendation: false** — a small, fixed, single-branch report function; no real comparison logic exists yet to have subtle bugs in.

## Design Notes

**Why a generic `details["exit_code"]` override in `cli.py` rather than a budget-specific branch.** AD-6 explicitly anticipates a FUTURE under/over-budget pair once a real metered spend source exists — hardcoding a `if ns.duty == "budget" and ...` branch into `main()` today would need to be revisited (and re-reviewed against AD-8) the moment that future story lands. A generic, duty-agnostic override read from `DutyResult.details` is available to ANY future duty with the same "the plain ok/not-ok binary can't express this" need, without `cli.py` growing per-duty special cases. AD-8 stays intact because `main()` remains the only code that RETURNS an exit code — a duty requests one via ordinary returned data, never via `sys.exit()`.

**Why `EXIT_BUDGET_NOT_CONFIGURED = 3` specifically.** No architectural significance is claimed for the number `3` itself (unlike `EXIT_INTERRUPTED=130`/`EXIT_INTERNAL=70`, which follow real Unix conventions — 128+SIGINT and EX_SOFTWARE respectively) — it is simply the next unused small integer after `EXIT_USAGE=2` (argparse's own convention). This is stated explicitly in `cli.py`'s own comment so nobody later reverse-engineers false meaning from the value. A future "under budget"/"over budget" pair is NOT reserved by number here (e.g. `4`/`5`) — that decision belongs to the story that actually implements them, once a real metered spend source's failure modes are known.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass
- `pixi run --frozen -e pyforge-steward steward budget check` -- expected: reports "no metered spend source configured", exits 3

**Results (2026-08-07):**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 197 passed (full Epic 4 suite, run together with Stories 4.1/4.2 in the same session; this story's own share is `test_budget_check.py`'s 5 tests plus `test_no_cost_integration_sdk_imported_in_budget`).
- **Live verification (real, not faked):** `steward budget check` was run against this repo's real, unmodified checkout state — output: the exact `_NOT_CONFIGURED_MESSAGE` text, process exit code `3` (confirmed via `echo $?` immediately after, not inferred).
