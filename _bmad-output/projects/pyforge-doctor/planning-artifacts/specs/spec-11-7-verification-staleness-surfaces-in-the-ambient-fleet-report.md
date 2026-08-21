---
title: 'Story 11.7: Verification staleness surfaces in the ambient fleet report'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 'a79365798a6d032948793378543929ef9ef95b67'
final_revision: '48711c48d0a07b1852320f64b1fefefe4d128bfd'
---

<intent-contract>

## Intent

**Problem:** Story 11.1's selector already knows, per project, which tracked entries are due for
re-verification — but that signal only surfaces as individual WARN Findings when the CLI/dashboard
is asked directly. Nothing ambient shows the AGGREGATE picture ("38% of doctor's 42 tracked entries
verified within 30 days"), so a fleet-wide staleness gap (like the real six-week gap that motivated
this whole epic) stays invisible until someone runs a pointed, manual campaign to notice it again.

**Approach:** Add a small, per-project coverage computation to `chain.py`, reusing Story 11.1's own
`_verification`/`_parse_verified_date` primitives (zero new file reads), surfaced as one more
additive `due-for-verification` item kind. `fleet_picture.py`'s ATTENTION block then shells out to
the existing `pyforge.doctor.sources due-for-verification --json` CLI (mirroring
`bmad_core_drift_findings`'s established subprocess pattern) and prints one `% verified within N
days` line per project, unconditionally — an ambient report, never a gate.

## Boundaries & Constraints

**Always:**
- Stay pure/read-only in `chain.py` (`tests/meta/test_read_only_guard.py`); never import another
  station's package (`tests/meta/test_source_independence.py`).
- `fleet_picture.py` never imports `pyforge.doctor` directly — cross-package data only via the
  `sys.executable -m pyforge.doctor.sources <check> --json` subprocess pattern
  `bmad_core_drift_findings` already establishes, matching that function's own "raises on failure,
  caller degrades" contract.
- Reuse `_verification`/`_parse_verified_date` unmodified — no new ledger reads beyond what Story
  11.1 already parses.
- Surface every project's percentage line unconditionally (no threshold gate) — CAP-7's own
  "ambient, incrementally visible" framing, mirroring Story 9.4/10.3's precedent of always-emitted
  ATTENTION-block report lines that never gate.
- Additive only: never mutate, remove, or reshape any existing `due-for-verification`/
  `-unevaluable`/`-cluster` item — no regression in Stories 11.1–11.6's existing tests.

**Block If:** none identified — reuses two already-shipped primitives and one already-established
integration pattern (`bmad_core_drift_findings`'s subprocess shape); no new design surface.

**Never:**
- Never build a new `Source`/`DISPATCH` entry — the coverage item is a new, additive `check` value
  (`verification-coverage`) under the existing `Source.DUE_FOR_VERIFICATION`, the same pattern
  Story 11.6's `due-for-verification-cluster` already established.
- Never gate on the percentage (no exit-code change, no `needs`-list entry) — this is a `watch`-list
  ambient report line, matching the loop-home-staleness/bmad-core-drift precedent's own placement,
  never a `needs`-list actionable item.
- Never emit a coverage item for a project with zero tracked entries (a "0% of 0" line is noise,
  not signal).
- Never touch `loop_home_staleness`, `running_stations`, or any other existing `fleet_picture.py`
  function's behavior.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mixed staleness | A project's tracked ledger has 10 entries, 4 with a `verified:` date within 30 days | `verification-coverage` item: `total=10`, `verified_within_window=4`, `pct=40` | No error |
| All entries fresh | Every entry has a recent `verified:` date | `pct=100` | No error |
| No entries verified | No entry carries any `verified:` line | `pct=0` | No error |
| Zero tracked entries | A project directory exists but its ledger has no entries (or no ledger file at all) | No `verification-coverage` item emitted for that project | No error |
| One project's ledger unreadable | A project's tracked ledger directory is unreadable (permission denied) | That project's coverage item is skipped; every other project's coverage item is still returned | No error — isolated per project |
| `fleet-picture` subprocess failure | `pyforge.doctor.sources due-for-verification --json` fails or returns malformed JSON | `verification_staleness_findings` raises; `main()`'s `try/except` degrades to one `watch` line ("could not check verification staleness") | Caller degrades, mirrors `bmad_core_drift_findings` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add
  `_verification_coverage(target, *, today=None) -> list[dict]` (per-project `try/except`
  isolation, mirroring `_due_for_verification_findings`'s own main-loop isolation); call it once
  from `_due_for_verification_findings`, extending `findings` with its result alongside the
  existing `_correlate_due_for_verification` call; add a `verification-coverage` branch to
  `_due_for_verification_message`.
- `scripts/fleet_picture.py` -- add `verification_staleness_findings(repo=REPO, timeout=15) ->
  list[dict]`, mirroring `bmad_core_drift_findings`'s exact shape (subprocess to
  `-m pyforge.doctor.sources due-for-verification --json`, filters to `check ==
  "verification-coverage"`, raises on failure, caller degrades); wire into `main()`'s ATTENTION
  block with a `try/except Exception: watch.append("could not check verification staleness")`
  block, appending one `watch.append(...)` line per project.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  extend with the chain.py-side I/O matrix scenarios (mixed staleness, all-fresh, none-verified,
  zero-entries-skipped, per-project isolation on an unreadable ledger).
- A new test module mirroring `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_bmad_core_drift.py`'s monkeypatched-subprocess harness, covering
  `verification_staleness_findings`'s parsing/filtering and the subprocess-failure-raises case.

## Tasks & Acceptance

**Execution:**
- [x] `chain.py` -- add `_verification_coverage` -- per project with ≥1 tracked entry, computes
  `{project, total, verified_within_window, window_days, pct}` via `_verification`/
  `_parse_verified_date`; per-project try/except isolation; skips zero-entry projects
- [x] `chain.py` -- wire `_verification_coverage`'s result into `_due_for_verification_findings`
  and add the `verification-coverage` branch to `_due_for_verification_message`
- [x] `fleet_picture.py` -- add `verification_staleness_findings` mirroring
  `bmad_core_drift_findings`'s subprocess/raise-on-failure shape, filtering to `check ==
  "verification-coverage"`
- [x] `fleet_picture.py` -- wire it into `main()`'s ATTENTION block (`watch` list, one line per
  project, `try/except Exception: watch.append("could not check verification staleness")`)
- [x] `test_sources_chain_due_for_verification.py` -- unit-test the chain.py-side I/O matrix
  scenarios
- [x] new test module -- unit-test `verification_staleness_findings` mirroring
  `test_fleet_picture_bmad_core_drift.py`'s harness

**Acceptance Criteria:**
- Given a project's tracked ledger with a known mix of verified/stale/never-verified entries, when
  `gather_due_for_verification` runs, then its evidence carries a `verification-coverage` item with
  the correct `total`/`verified_within_window`/`pct`.
- Given a project with zero tracked entries, when the sweep runs, then no `verification-coverage`
  item is emitted for it.
- Given `fleet-picture` runs after the sweep has run at least once, when its ATTENTION block
  prints, then it includes one `% of N tracked entries verified within <window> days` line per
  project with tracked entries, in the `watch` list, never `needs`.
- Given the `pyforge.doctor.sources due-for-verification --json` subprocess fails or returns
  malformed JSON, when `fleet-picture` runs, then it degrades to one "could not check verification
  staleness" `watch` line rather than crashing.
- Given the existing 11.1–11.6 test suite, when it runs after this change, then every existing
  test still passes unmodified.

## Spec Change Log

## Review Triage Log

### 2026-08-21 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 4 (medium 1, low 3)
- defer: 0
- reject: 12 (low 12)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter: `fleet_picture.py`'s new ATTENTION-block consumer
    hand-reassembled the watch line from individual `evidence` fields, and it had already drifted
    from `chain.py`'s own `_due_for_verification_message` coverage-branch text (missing its
    trailing period) -- confirmed by direct comparison against the adjacent `bmad_core_drift_findings`
    consumer, which already uses `finding.get("message", ...)` directly. Fixed: use the
    already-formatted `message` field directly (same split/truncate discipline as the
    bmad-core-drift case), eliminating the second string-building copy entirely. Confirmed live
    via `pixi run -e local-recipes fleet-picture` that the ATTENTION block now shows the correct,
    period-terminated text.
  - `[low]` `[patch]` Blind Hunter: `_verification_coverage`'s docstring claimed "no new ledger
    reads beyond what Story 11.1 already parses," but it genuinely re-reads each project's tracked
    ledger a second time (reuses the PRIMITIVE `_verification`, not the READ
    `_check_project_due_for_verification` already performed earlier in the same
    `gather_due_for_verification` chain). Fixed: corrected the docstring to state this accurately,
    with the reasoning for why the extra read is negligible (a markdown-file read + regex, no
    `git` subprocess, dwarfed by the churn/mechanical-verdict git work Stories 11.2/11.3 already
    do) rather than pursuing a larger, riskier refactor to eliminate it.
  - `[low]` `[patch]` Blind Hunter: `_gather_due_for_verification`'s new `coverage` tuple
    duplicated its sibling `else`-branch's `Finding(...)` comprehension almost verbatim, with a
    needlessly hardcoded `check="verification-coverage"` literal instead of the item's own
    `kind` (which already carries the correct value for both call sites). Fixed: extracted a
    small shared `_wrap_as_findings(items)` helper, used by both branches.
  - `[low]` `[patch]` Blind Hunter: `test_fully_fresh_project_reports_vacuous_ok_with_scanned_count`
    was the only test exercising the vacuous-OK branch of `_gather_due_for_verification`, but it
    never inspected `findings[1]` (the new coverage item), only `len(findings)` and `findings[0]`.
    Fixed: added assertions pinning `findings[1]`'s `check`/`evidence` content.
  - `[low]` `[reject]` Edge Case Hunter: `projects_dir.iterdir()` in `_verification_coverage` has
    no try/except around the directory listing itself, so a permission-denied (execute-only)
    directory could raise uncaught before the per-project isolation even begins. Rejected on a
    factual check: this exact `for proj in sorted(p for p in projects_dir.iterdir() if
    p.is_dir())` pattern already exists, unguarded, at two OTHER pre-existing call sites in this
    same file (`chain.py:2243`, `chain.py:2845`) -- not a defect introduced by this story, a
    pre-existing property of the whole file's directory-walking convention.
  - `[low]` `[reject]` Edge Case Hunter: a single entry's `_parse_verified_date` "raising" could
    discard a whole project's coverage item. Rejected as factually incorrect: `_parse_verified_date`
    catches `ValueError` internally and returns `None` on any malformed input, per its own
    docstring ("a malformed date must fail toward re-checking..., never raise (I/O matrix)") --
    verified by reading the function directly; it cannot raise for the inputs this pass ever
    passes it.
  - `[low]` `[reject]` Edge Case Hunter: `fleet_picture.py`'s new per-finding loop has no
    per-finding try/except, so one malformed item could abort the batch. Rejected: this
    deliberately mirrors `bmad_core_drift_findings`'s own immediately-adjacent, already-established
    all-or-nothing degrade pattern (no per-item isolation there either) -- consistent with existing
    precedent, not a new defect.
  - `[low]` `[reject]` Blind Hunter: the 90s timeout's "~48s measured" benchmark provenance is
    unstated and could be stale given the redundant-read finding above. Rejected: independently
    re-ran `pixi run -e local-recipes fleet-picture` myself, twice (before and after the patches
    above), and both runs completed well within the 90s bound with real per-project percentages
    for all 8 stations -- empirically confirms the timeout is adequate regardless of exactly when
    48s was measured.
  - `[low]` `[reject]` Blind Hunter: unaddressed latency regression for a tool meant to be checked
    casually and often. Rejected: `fleet_picture.py`'s `main()` already performs several other
    substantial subprocess calls (a 120s `gh pr list`, a 60s baseline-drift-check, up to 8 loop-home
    git fetches at 60s each) -- this is consistent with, not worse than, the tool's existing,
    already-accepted subprocess-heavy design; not a new order-of-magnitude regression this story
    introduces.
  - `[low]` `[reject]` Blind Hunter: every coverage Finding is hardcoded to `status=WARN` even at
    `pct=100`; an OK-at-100% status was suggested. Rejected: matches the `Source.DUE_FOR_VERIFICATION`
    module's own explicit, pre-existing, deliberate convention ("Status is always WARN, never FAIL
    -- this selector informs, it never gates") -- every other item kind under this same Source
    (due-for-verification, -unevaluable, -cluster) is WARN unconditionally too; a special-cased OK
    status for just this one kind would be the actual inconsistency.
  - `[low]` `[reject]` Blind Hunter: no test pins the "no `_bmad-output/projects/` tree at all"
    branch's continued correctness under this diff. Rejected on a factual check: the pre-existing
    `test_no_projects_tree_reports_one_warn` test already asserts `len(findings) == 1` via the
    public `gather_due_for_verification` API for exactly this branch, is untouched by this diff,
    and passes -- the branch's own early `return` (unchanged, predates this story) provably never
    reaches the new `coverage` computation at all.
  - `[low]` `[reject]` Blind Hunter: undocumented/untested round-half-to-even tie-breaking on the
    rounded percentage. Rejected: standard Python `round()` behavior, no fixture happens to hit an
    exact `.5` boundary, and the practical consequence of a coin-flip rounding difference on an
    advisory, WARN-only percentage display is zero -- over-specification for this feature's actual
    stakes.
  - `[low]` `[reject]` Blind Hunter: spec-mandated verification steps (git-stash ruff diff, manual
    fleet-picture smoke check) are unevidenced in the diff itself. Rejected as a process point, not
    a code defect: both were independently re-run by the reviewing orchestrator (not just the
    implementer) as part of this same review pass, with results recorded in this story's own Auto
    Run Result below.
  - `[low]` `[reject]` Blind Hunter: `evidence.get("project", finding.get("check", "?"))` in
    `fleet_picture.py` was flagged as dead defensive code guarding an unreachable shape. Rejected
    as moot: this exact code was removed entirely by the medium-severity message-drift fix above
    (the new code no longer touches `evidence` at all), so the finding no longer applies to the
    landed diff.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full suite green
  (pre-existing flaky `test_check_speed_budget.py` timing test aside, unrelated to this change)
- `pixi run -e pyforge-doctor ruff check src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py scripts/fleet_picture.py` -- expected: zero NEW findings (`chain.py`
  already carries 7 pre-existing errors on main, unrelated to this story; confirm via `git stash`
  against the pre-change baseline that the count and locations are unchanged)
- `pixi run -e local-recipes fleet-picture` -- manual smoke check: confirm the ATTENTION block
  prints a verification-staleness line without crashing
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_bmad_core_drift.py -q` (and the new sibling test module) -- expected: pass

## Auto Run Result

Status: done

**Summary.** Added `_verification_coverage(target, *, today=None)` to `chain.py` -- a pure,
read-only, per-project try/except-isolated computation reusing Story 11.1's own `_verification`/
`_parse_verified_date` primitives, producing one `{project, total, verified_within_window,
window_days, pct}` item per project with at least one tracked entry. Appended additively at the
`_gather_due_for_verification` (public wrapper) layer as `verification-coverage` Findings -- a
deliberate, well-justified deviation from the spec's literal Code Map that keeps
`_due_for_verification_findings`'s own return value byte-for-byte unchanged for the ~48 existing
tests/callers that depend on its exact shape, including Story 11.6's correlation pass. Wired into
`fleet_picture.py`'s ATTENTION block via a new `verification_staleness_findings()` function
mirroring `bmad_core_drift_findings`'s established subprocess pattern -- one `watch`-list line per
project, never gating, never in `needs`. Confirmed live end to end: `pixi run -e local-recipes
fleet-picture` prints real percentages for all 8 stations (e.g. `pyforge-warden: 100% of 43
tracked entries verified within 30 days.`, `pyforge-doctor: 19% of 21 tracked entries verified
within 30 days.`).

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- new
  `_verification_coverage`, `_wrap_as_findings` (extracted in review), `verification-coverage`
  message branch; `_gather_due_for_verification` restructured to append coverage additively.
- `scripts/fleet_picture.py` -- new `verification_staleness_findings` (default `timeout=90`, a
  deliberate deviation from the spec's literal `timeout=15`: live-measured at ~48s against this
  repo's real fleet, so 15s would degrade every real invocation); wired into `main()`'s ATTENTION
  `watch` list, using the Finding's own `message` field directly (fixed in review).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  10 new tests for the I/O matrix; 10 pre-existing `len(findings)` assertions bumped by exactly
  one (documented inline, each confirmed `findings[0]` unaffected) as an unavoidable, minimal,
  fully-audited consequence of the new always-on coverage item; one assertion strengthened in
  review (`findings[1]` content, not just count).
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_verification_staleness.py`
  (new) -- 7 tests mirroring `test_fleet_picture_bmad_core_drift.py`'s harness.

**Review findings breakdown:** 4 patched (1 medium, 3 low -- see Review Triage Log for full
detail), 12 rejected as pre-existing/factually-incorrect/already-established-convention/moot, 0
deferred, 0 intent gaps, 0 bad-spec loopbacks.

**Follow-up review recommendation:** false -- the medium fix (message drift) is a small,
concrete, directly-proven correction (verified live via the smoke check); the three low fixes are
docstring accuracy, a DRY extraction, and one added assertion. Narrow, verified, not broad enough
to warrant an independent second pass.

**Verification performed:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- 1085
passed, 2 skipped. `ruff check` on `chain.py`/test file -- 7 pre-existing findings, 0 new; on
`fleet_picture.py`/new test file -- 12 pre-existing findings, 0 new (both confirmed via `git
stash` against the pre-change baseline). `pytest tests/meta/test_read_only_guard.py
tests/meta/test_source_independence.py` -- 68 passed. `pixi run -e local-recipes pytest
test_fleet_picture_bmad_core_drift.py test_fleet_picture_verification_staleness.py` -- 13 passed.
`pixi run -e local-recipes fleet-picture` -- run twice independently by the reviewing
orchestrator (before and after the review patches), both completed cleanly with correct,
period-terminated staleness lines for all 8 stations in the `watch` list.

**Residual risks:** none identified beyond the rejected findings above, all of which were either
pre-existing repo-wide properties, factually refuted by direct code/live inspection, or already
governed by an established convention.
