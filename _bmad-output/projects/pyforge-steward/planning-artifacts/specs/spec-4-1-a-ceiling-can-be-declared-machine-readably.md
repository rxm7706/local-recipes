---
title: 'Story 4.1: A ceiling can be declared, machine-readably'
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

**Problem:** This repo's own doctrine — "the ceiling is $1500/month" — lives only as prose in a Dream file the operator has to remember to reread. Nothing machine-readable records it.

**Approach:** `steward budget set --cap <amount><currency>/<period>` (e.g. `1500usd/month`) parses the cap string, validates it, and records the amount/currency/period to `.steward/budget.yaml` — the tracked, repo-root config location `ARCHITECTURE-SPINE.md`'s Consistency Conventions table already reserves for FR-16. `budget.py` mirrors `keys.py`'s `.steward/keys-inventory.yaml` read/write pattern (Epic 1) verbatim: `yaml.safe_load`/`safe_dump` only, atomic temp-file + `os.replace` write — never a direct `open("w")` on the real path (AD-1: reuse the same discipline, don't invent a second one).

## Boundaries & Constraints

**Always:**
- `parse_cap` validates the ENTIRE cap string — shape (`<amount><currency>/<period>`) and a strictly-positive amount — before `set_ceiling` ever opens `.steward/budget.yaml` for writing. A malformed `--cap` therefore raises `CapParseError` with the file completely untouched: missing if it never existed, byte-for-byte unchanged if it did (proven by a dedicated before/after test, not just claimed).
- `set_ceiling` REPLACES any prior declaration — `.steward/budget.yaml` records ONE doctrine at a time (`ceilings: [<the one ceiling>]`), not a growing history of every value ever set. This is a documented judgment call: the AC's own framing ("the ceiling is $1500/month," singular) is a replace-in-place doctrine, not an append-only log — see Design Notes.
- The write is atomic: a pid+thread-id-suffixed temp file, then `os.replace` — mirrors `keys.py::save_inventory`'s identical rationale (a concurrent `budget show` must never observe a partially written file).

**Block If:** `--cap` doesn't match `<amount><currency>/<period>` (missing unit, missing `/`, unparsable amount) or the amount is not strictly positive — both raise `CapParseError`, reported as a duty-level failure (`EXIT_FAILED`), never a corrupt or partial write.

**Never:**
- No second cap-parsing/config-write implementation anywhere in this package — `parse_cap`/`load_budget`/`save_budget` ARE the schema; there is no parallel/simplified version.
- No `yaml.load`/`yaml.unsafe_load` anywhere — `safe_load`/`safe_dump` only (mirrors `keys.py`'s inventory precedent).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Well-formed cap, no prior declaration | `--cap 1500usd/month`, `.steward/budget.yaml` absent | File created; records amount `1500.0`, currency `usd`, period `month`, a `declared_at` timestamp | No error |
| Well-formed cap, prior declaration exists | `--cap 2000usd/month` after an earlier `1500usd/month` | File now holds ONLY the new ceiling (`2000usd/month`) — the prior one is replaced, not appended | No error |
| Missing unit | `--cap 1500usd` (no `/period`) | Clear usage error naming the expected shape; no file written/changed | `CapParseError` → `DutyResult(ok=False, ...)` |
| Unparsable amount | `--cap usd/month` (no amount) | Same as above | `CapParseError` |
| Zero/negative amount | `--cap 0usd/month` / `--cap -5usd/month` | Same as above (not one of the AC's literal examples, but the same "malformed cap" class — see Design Notes) | `CapParseError` |
| Malformed cap against an EXISTING valid file | `--cap garbage` when `.steward/budget.yaml` already holds a valid prior declaration | The prior declaration survives byte-for-byte unchanged | `CapParseError`, no write attempted |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/budget.py` -- NEW: `repo_root`, `default_budget_path`, `CapParseError`, `Ceiling`, `parse_cap`, `BudgetError`, `load_budget`, `save_budget`, `set_ceiling`, `BudgetDuty` (verb dispatch scaffold; `show`/`check` land in Stories 4.2/4.3 but the class and its degrade-on-bare-invocation branch are established here)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- EDIT: `_add_budget_subparsers` (`set --cap`), `resolve_duty("budget")` now returns a real `BudgetDuty`
- `src/shared/packages/pyforge-steward/tests/conformance/test_budget_set.py` -- NEW: full I/O matrix, primitive + CLI level, incl. the no-partial-write proof

## Tasks & Acceptance

**Execution:**
- [x] `budget.py` -- `parse_cap(cap) -> (amount, currency, period)`, `CapParseError`
- [x] `budget.py` -- `Ceiling`, `BudgetError`, `load_budget`/`save_budget` (`.steward/budget.yaml`, atomic write)
- [x] `budget.py` -- `set_ceiling(path, cap) -> Ceiling` (validate-then-write ordering)
- [x] `budget.py` -- `BudgetDuty` (verb dispatch: `set` real, bare invocation degrades per AD-7)
- [x] `cli.py` -- `_add_budget_subparsers`, `resolve_duty("budget")` wired to `BudgetDuty`
- [x] `tests/conformance/test_budget_set.py` -- full matrix incl. `test_set_ceiling_with_a_malformed_cap_never_writes_the_file` / `..._never_corrupts_an_existing_file`

**Acceptance Criteria:**
- Given `.steward/budget.yaml` (the tracked, repo-root config location), when `steward budget set --cap 1500usd/month` is run, then the file records the amount, currency, and period in a stable, documented schema.
- Given a malformed cap value (e.g. missing unit, unparsable amount), when `steward budget set --cap garbage` is run, then it reports a clear usage error and does not write a corrupt entry to the config file.

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done, run jointly across Stories 4.1–4.3)
- intent_gap: 0
- bad_spec: 0
- patch: 1 (found and fixed during this same session — see Story 4.2's spec, which is where the affected verb's flag lives)
- defer: 0
- reject: 0
- **Checked**: malformed-`--cap` ordering. `set_ceiling` calls `parse_cap` BEFORE `save_budget` is ever reached — confirmed by reading the function body (validation is the first statement) AND by execution: `test_set_ceiling_with_a_malformed_cap_never_writes_the_file` (no prior file) and `test_set_ceiling_with_a_malformed_cap_never_corrupts_an_existing_file` (prior valid file, byte-for-byte unchanged after a rejected `set`) both pass.
- **Checked**: zero/negative amount. The AC's own examples ("missing unit, unparsable amount") don't literally cover `0usd/month`, but a zero/negative ceiling is the same malformed-input class in spirit — added the check and its test rather than leaving a silent footgun (`0` would otherwise parse "successfully" and write a ceiling that can never be complied with).
- **Checked**: exception hierarchy. `CapParseError`/`BudgetError` both extend `ValueError` but are distinct sibling classes (neither is a subclass of the other) — `BudgetDuty.run`'s two `except` clauses can never shadow each other, and nothing outside those two exception types is caught here (an unexpected `OSError`, e.g. a permission-denied write, correctly propagates to `cli.main()`'s generic handler and reports as `EXIT_INTERNAL`, never silently swallowed as a duty-level failure).
- **Checked**: replace-vs-append semantics for `set`. Chose "replace" (see Design Notes) — deliberate, not a default fallen into; documented in `set_ceiling`'s own docstring so a future story can't silently assume append-only history.

**Follow-up review recommendation: false** — straightforward, closely mirrors `keys.py`'s already-reviewed inventory read/write pattern; the one real finding (the `--json`-on-error-path bug class) was caught and fixed live during this same session (see Story 4.2's Review Triage Log for the fix itself, since it lives on `show`'s flag).

## Design Notes

**Why `set` REPLACES rather than appends.** The epic's own framing is a single doctrine ("the ceiling is $1500/month"), not a log of every ceiling ever declared. `epics-with-stories.md`'s Story 4.2 AC uses "ceiling(s)" (plural-safe wording), which could be read as inviting multiple simultaneous ceilings — but no AC anywhere describes a SECOND `--cap` composing with a first (e.g. one for `usd/month` and a separate one for `eur/year` coexisting), and `.steward/budget.yaml`'s schema already stores a list (`ceilings: [...]`) for forward compatibility without committing to that shape now. Replacing is the simpler, more conservative reading (Simplicity First / AD-6's "conservative" framing) and is what "the ceiling is X" plain-English doctrine actually means when re-declared. Reject alternative considered: appending every `set` as a growing history — rejected because nothing in the epic asks for a ceiling *history*, and an unbounded-growth config file is exactly the kind of speculative complexity CLAUDE.md's Simplicity First principle rules out.

**Why `budget.py` defines its own `repo_root()` rather than importing `provision.py`'s.** Mirrors the existing precedent: `keys.py` and `provision.py` each already define an independently-walking `repo_root()` (different markers, same destination) rather than one importing the other's. "One module per duty" (the architecture spine's own structural seed) means a duty module's primitives are self-contained; `budget.py` continues that pattern rather than introducing the first cross-duty import for a filesystem-resolution helper.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass
- `pixi run --frozen -e pyforge-steward steward budget set --cap 1500usd/month` -- expected: writes `.steward/budget.yaml` and reports the declared ceiling

**Results (2026-08-07):**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 197 passed (full Epic 4 suite, run together with Stories 4.2/4.3 in the same session; this story's own share is `test_budget_set.py`'s tests plus its slice of `BudgetDuty`/`cli.py`).

## Adversarial review pass (2026-08-07, Blind Hunter + Edge Case Hunter)

Dispatched with the diff file path only, no shared context. Two findings landed here (both
in `load_budget`, shared by every story that reads `.steward/budget.yaml`):

- `medium` `patch` **A non-list `ceilings` value crashed with a raw, unformatted `TypeError` instead of a clean `BudgetError`.** `for raw in document.get("ceilings") or []:` raises a bare `TypeError` when "ceilings" is a truthy non-iterable-of-entries scalar (e.g. `ceilings: 5`) -- that isn't caught by the surrounding `except (KeyError, TypeError, ValueError)` (which only wraps `Ceiling(...)` construction, not the loop's own iteration), so it propagates past every duty-level handler to `cli.main()`'s generic `except Exception`, printing a raw Python traceback and never honoring `--json`. Fixed: `document.get("ceilings")` is now type-checked (`isinstance(..., list)`) before iterating, raising a clean `BudgetError` otherwise. New test: `test_budget_show_json_via_cli_renders_a_non_list_ceilings_error_as_json`.
- `low` `patch` **`declared_at` wasn't actually validated as a required field, despite the module's own docstring promising it was.** `amount`/`currency`/`period` are read via `raw["..."]` (raises on absence), but `declared_at` used `raw.get("declared_at")`, silently defaulting to `None` -- even though `Ceiling.declared_at` is typed `str` (non-optional). Fixed: `declared_at` now reads via `raw["declared_at"]`, consistent with the other three required fields. New test: `test_budget_show_reports_a_load_error_when_declared_at_is_missing`.

**Re-verification (2026-08-07, after both patches):** `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- **200 passed** (full suite).

**Follow-up review recommendation (updated): false** -- both findings are narrow, each covered by a dedicated regression test.
