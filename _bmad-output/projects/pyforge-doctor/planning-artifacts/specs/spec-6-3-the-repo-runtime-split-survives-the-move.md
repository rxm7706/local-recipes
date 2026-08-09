---
title: 'Story 6.3: The repo/runtime split survives the move'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '6d5d2e09ed7c82e6cc1f894bc9aa4d88b7e1c341'
final_revision: 'b44e1216dfbc4a84d5603508efb715b56bf53b24'
---

<intent-contract>

## Intent

**Problem:** Epic 6 moves 10 conformance detectors into Doctor's own
`sources.REGISTRY` (Story 6.2). One of them (`dashboard_drift`, Story 6.5)
reads host state (tmux, `~/.bmad-loops`) that is absent in CI, and
`sources/__init__.py`'s `scope` field ("repo"/"runtime") already exists to
mark that — but nothing yet *acts* on it: Doctor's `check` verb has no way
to select the CI-safe subset, and there is no reusable "cannot evaluate
here" degrade path for a host-state source to use.

**Approach:** Give `doctor check` a `--scope {repo,runtime,all}` filter
driven by each category's already-declared `sources.REGISTRY` scope
(default `all`, matching today's behavior), and add one reusable
`sources.degrade_on_exception` helper that converts any exception from a
gather call into a single WARN `Finding` rather than letting it propagate —
ready for Story 6.5's `dashboard_drift` (and later runtime sources) to call
around their own host-state reads.

## Boundaries & Constraints

**Always:** Omitting `--scope` (or passing `all`) behaves exactly as today
— all three `check` categories (engines/env/durability) run. `--scope`
filtering reads each category's scope from `sources.REGISTRY`, never a
second hardcoded scope list. WARN findings never change the exit code
(existing `verdict.exit_code_for` contract, unmodified).

**Block If:** implementing this reveals `report-schema.json`/`DoctorReport`
must change to represent scope in JSON output, or that scope must change
for one of today's 9 registered sources.

**Never:** add a new `Source`/`REGISTRY` entry or move a real detector
(`dashboard_drift` etc.) — that is Stories 6.4-6.9's own job. Add `--scope`
to `monitor`/`diagnose` (out of this story's surface). Add a new
`DoctorStatus` member for "unknown" — WARN is Doctor's existing
cannot-evaluate status. Wire `degrade_on_exception` into today's three
existing (repo-scope) dispatch calls — their own "never raises" contract
must stay enforced by letting an unexpected exception there propagate to
`main()`'s existing top-level net, never masked as WARN.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No `--scope` | `doctor check <dir>` | all 3 categories run (unchanged) | none |
| `--scope repo` | `doctor check <dir> --scope repo` | all 3 categories run (all are repo-scope today) | none |
| `--scope runtime` | `doctor check <dir> --scope runtime` | 0 findings, exit 0; none of the 3 gathers invoked | none |
| `--scope` + `--list` | `doctor check --list --scope runtime` | full static catalog printed; `--scope` ignored | none |
| unknown `--scope` value | `doctor check --scope bogus` | usage error | exit 2 |
| `degrade_on_exception`, gather succeeds | a gather callable returning findings | those findings, unchanged | none |
| `degrade_on_exception`, gather raises | a gather callable raising any `Exception` | one WARN `Finding` naming the exception | never raises |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- add `scope_for(source)` lookup + `degrade_on_exception(source, check, gather)` helper.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- add `--scope` to the `check` subparser; filter `run_engines`/`run_env`/`run_durability` by scope in `_run_check`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` -- `--scope` CLI tests.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py` -- `scope_for`/`degrade_on_exception` unit tests.

## Tasks & Acceptance

**Execution:**
- [x] `sources/__init__.py` -- add `scope_for(source: Source) -> str` (loops `REGISTRY`, raises `ValueError` if absent) -- one canonical per-source scope lookup, replacing hand-rolled loops at every call site.
- [x] `sources/__init__.py` -- add `degrade_on_exception(source, check, gather) -> tuple[Finding, ...]` (try/except around `gather()`, converting any `Exception` into one `Finding(status=DoctorStatus.WARN, ...)`) -- the reusable "cannot evaluate here" path Story 6.5+ needs.
- [x] `__main__.py` -- add `--scope {repo,runtime,all}` (default `"all"`) to the `check` subparser; add `_CATEGORY_SOURCE` (category name -> `Source`) and `_category_in_scope(category, requested_scope)`; apply it to narrow `run_engines`/`run_env`/`run_durability` after the existing default/explicit-flag resolution in `_run_check`. Update `--list`'s help text to note it also ignores `--scope`.
- [x] `tests/unit/test_cli_check.py` -- add: `--scope repo` matches default; `--scope runtime` yields 0 findings/exit 0 with none of the three gathers invoked (mirror the existing `_forbid_*` idiom); unknown `--scope` value is a usage error (exit 2); `--list --scope runtime` still prints the full catalog.
- [x] `tests/unit/test_sources_registry.py` -- add: `scope_for` resolves a known `Source`'s registered scope and raises for a non-`Source` misuse path already covered by `SourceRegistration`; `degrade_on_exception` passes through a successful gather's findings unchanged; `degrade_on_exception` converts a raised exception into exactly one WARN `Finding` carrying the given `source`/`check` and mentioning the exception in `message`.

**Acceptance Criteria:**
- Given the monorepo root, when `doctor check --scope runtime` runs today, then it exits 0 with zero findings and never invokes the engines/env/durability gathers (all three are registered `scope="repo"`).
- Given `sources.degrade_on_exception` wraps a gather callable that raises, when it runs, then it returns exactly one `Finding` with `status=DoctorStatus.WARN`, never propagates the exception, and the exit-code projection for that finding stays `0`.
- Given `doctor check --scope bogus`, when parsed, then it is a usage error (exit 2), matching `--engines`/`--env`'s existing unknown-value handling.

## Spec Change Log

(none — no `bad_spec`/`intent_gap` findings this pass)

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 0, medium 1, low 5)
- defer: 1 (medium 0, low 1)
- reject: 2 (low 2)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both) found `doctor check --engines --scope runtime` (an explicit category flag whose registered scope contradicts `--scope`) silently narrowed to zero findings/exit 0 — indistinguishable from "ran clean" for an automated `--json` consumer. Fixed: added `_validate_scope_against_explicit_categories` (raises a usage error, exit 2, before dispatch) in `__main__.py`, wired into `main()`'s existing validate phase; added 4 new tests covering the error path, the matching-scope non-error path, and the untouched implicit-default path. Updated `--scope`'s help text to document the new behavior and that no runtime-scope check exists yet.
  - `[low]` `[patch]` `sources/__init__.py`'s `SourceRegistration` docstring and the `REGISTRY` inline comment both still claimed "Story 6.3 is what introduces the first runtime member" — false now that this diff (Story 6.3) is mechanism-only by design. Reworded both to say Story 6.3 builds the mechanism without registering one, and Story 6.5's `dashboard_drift` is the first.
  - `[low]` `[patch]` The new module-docstring paragraph's "see that story's Design Notes" citation grammatically pointed at Story 6.5 (the example just named) instead of this story's own spec. Reworded to name Story 6.3 explicitly.
  - `[low]` `[patch]` `_validate_check_names`'s docstring listed `--list`'s ignored flags as `--engines`/`--env`/`--json`/`path`, already stale (missing `--durability`) and now also missing this diff's own `--scope` addition to the real help text. Synced both.
  - `[low]` `[patch]` The `--scope runtime` zero-findings scenario was only asserted via `--json`; `_emit_text`'s own zero-finding header path was untested for this flag. Added a companion non-JSON test.
  - `[medium]` `[defer]` `sources/__init__.py`'s `__all__` tuple is not alphabetically sorted (ruff `RUF022`); this diff extended the same already-unsorted tuple. Confirmed pre-existing via `git show <baseline>:... | ruff check - --select RUF022`. Logged to `deferred-work.md`, not fixed here (touches a line this story didn't otherwise need to change).
  - `[low]` `[reject]` "`degrade_on_exception` ships with zero production callers" — expected for a mechanism-only story whose consuming source (Story 6.5's `dashboard_drift`) doesn't exist yet; precedented by Story 6.2's own accepted rejection of the analogous "no coupling test forcing a future REGISTRY entry to have a real gather() dispatch" finding.
  - `[low]` `[reject]` "`_category_in_scope` trusts an already-argparse-validated `requested_scope` with no internal guard" — matches this file's existing style (e.g. `_gather_engines`/`_gather_env` trust their own already-validated category dispatch); not a new anti-pattern.

## Design Notes

`degrade_on_exception` is deliberately NOT wired into today's three dispatch
calls: each of `warden_source.gather`, `env_hygiene.gather`, and
`marshal_source.gather` already documents its own "degrades, never crashes"
contract (see `sources/marshal.py`'s module docstring) — an exception
escaping one of those today would be a real bug, and should keep propagating
to `main()`'s existing top-level net (exit 2), not get silently reclassified
as WARN. The helper exists for the population that has no such gather() yet:
a `scope="runtime"` source whose inputs (tmux, `~/.bmad-loops`) are expected
to be absent outside an operator's own machine.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: all pass, including the new scope/degrade tests.
- `python -m pyforge.doctor check --scope runtime --json` (from a directory with no findings expected) -- expected: `{"findings": []}` shape, exit 0.

## Auto Run Result

**Summary.** `doctor check` gained `--scope {repo,runtime,all}` (default `all`,
today's behavior unchanged), filtering the three existing categories
(engines/env/durability) by each one's `sources.REGISTRY`-declared scope via
a new `sources.scope_for` lookup. `sources.degrade_on_exception` is a new
reusable "cannot evaluate here" wrapper (converts any exception into one WARN
`Finding`) for a future `scope="runtime"` source's own gather — deliberately
unused in production by this story, since no such source exists yet (Story
6.5's `dashboard_drift` is the first). Adversarial review caught one real
gap: an explicit category flag contradicting `--scope` used to silently
report a zero-finding, exit-0 result indistinguishable from "ran clean" —
fixed with a usage-error guard before dispatch.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- `scope_for`, `degrade_on_exception`, doc fixes.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- `--scope` flag, `_CATEGORY_SOURCE`, `_category_in_scope`, `_validate_scope_against_explicit_categories`, help-text updates.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` -- 8 new tests (scope filtering, the new usage error, the matching/non-error path, non-JSON render).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py` -- 5 new tests (`scope_for`, `degrade_on_exception`).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md` -- Story 6.3 marked `done` with a dated Outcome note.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml` -- promoted via `scripts/promote_sprint_status.py --project doctor` (never hand-edited).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- 1 new entry (pre-existing `__all__` sort lint finding).

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, deduplicated,
both independently caught the same core gap): 0 intent_gap, 0 bad_spec, 6
patch (0 high / 1 medium / 5 low -- all applied), 1 defer (pre-existing
`__all__` sort, logged to `deferred-work.md`), 2 reject (both precedented by
Story 6.2's own accepted rejects for analogous findings). No loopback needed.

**Follow-up review recommendation:** `false`. The one medium patch (the
usage-error guard) is a localized, well-tested addition to the same two
files this story already owns, verified by 5 new tests covering the error
path, the matching-scope non-error path, and the untouched default-run path;
no new external API, security, or data-model surface. The full suite (449
tests) and the `test_doctor_check_completes_within_the_five_second_budget`
gate both pass after every change.

**Verification performed:** `pixi run -e pyforge-doctor pyforge-doctor-test`
-> 449 passed (10 new). Live CLI smoke tests: `doctor check --scope runtime
--json` -> `{"findings": []}`, exit 0; `doctor check --scope bogus` -> usage
error, exit 2; `doctor check --engines --scope runtime` -> usage error, exit
2 (post-patch). `ruff check` on both touched source files shows only
pre-existing findings (confirmed via `git show <baseline> | ruff check`),
none newly introduced.

**Residual risks:** `degrade_on_exception`'s interface is unproven against a
real call site until Story 6.5's `dashboard_drift` lands (accepted, mirrors
Story 6.2's own accepted equivalent risk for its registry mechanism).
