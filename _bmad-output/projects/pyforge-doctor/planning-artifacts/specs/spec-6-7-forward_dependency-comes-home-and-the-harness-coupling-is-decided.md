---
title: "Story 6-7: `forward_dependency` comes home, and the harness coupling is decided"
type: "change"
created: "2026-08-09"
status: "done"
recovery_tier: 0
recovery_source: "authored first-hand during implementation (no bmad-loop run; hand-driven per operator instruction)"
recovery_date: "2026-08-09"
baseline_revision: "81c9364e3b^ (main at 57bf8a9b1b)"
final_revision: "81c9364e3b"
---

## Intent

Re-home `scripts/forward_dependency_check.py` into Doctor as `sources/deps.py`. FR-15.

This is the only detector in Epic 6 whose move requires a **decision rather than a port**.
It imports `bmad_loop.sprintstatus.ACTIONABLE_STATUSES` deliberately — *derived, never
restated*, so the check cannot drift from real engine behaviour. Adding the harness to
Doctor's lean env couples Doctor to Marshal's toolchain; restating the enum breaks the
invariant that makes the check trustworthy. Neither is free.

**Surface:** `sources/deps.py`, `pixi.toml`, `tests/`

## Acceptance Criteria

- **Given** the two options are stated with their costs, **When** one is chosen, **Then**
  the decision is recorded as an AD with its rejected alternative.
- **And** if the enum is restated, a conformance test fails when it diverges from the
  installed library — the invariant is preserved by a different mechanism, not dropped.

## The decision

**Option B chosen by the operator, 2026-08-09.** Recorded as **AD-13** in
`architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md`, with the rejected
alternative stated in full.

`sources/deps.py` defines `ACTIONABLE_STATUSES = frozenset({"backlog", "ready-for-dev"})`
locally and imports nothing from `bmad_loop`. The invariant is not dropped — it **moves**,
from a runtime import to test-time set equality.

**Rejected alternative — add `bmad-loop` to `[feature.pyforge-doctor.dependencies]`.** It
preserves the invariant most directly, and on a strict reading of S-6.10 it is not even
barred: `bmad_loop` is an upstream harness Marshal *wraps*, not the `pyforge.marshal`
package. Rejected on three grounds:

1. **It contradicts AD-11's own rationale**, which is about *machinery*, not package names:
   a verdict assembled from the judged station's machinery fails exactly when that
   machinery is what broke — the only case worth checking. `bmad_loop` **is** the machinery
   whose blindness this source reports on.
2. **Blast radius.** It expands a 3.3 MB / 33-module git-pinned harness into a 7-dependency
   environment whose contract is a five-second pre-flight (NFR-4, counter-metric SM-C1), and
   converts one check's dependency into a **whole-CLI** dependency: a `bmad-loop` resolution
   failure would take `check`, `monitor` and `diagnose` down together.
3. **It defers a cost to S-6.10**, which would need a second `sources/warden.py`-style
   allowlist entry whose stated reason — *relays an instrument's self-report about its own
   environment* — does not transfer, because `deps.py` judges an artifact.

**What Option B buys, measured rather than assumed.** CI's `detectors.yml` runs on plain
`setup-python` with `pip install pyyaml playwright` — no pixi, no `bmad_loop` — so
`forward_dependency_check.py` reports UNKNOWN (`exit 2`) in CI *today*, and would continue
to under the rejected alternative, since CI does not use Doctor's environment either.
Dropping the import is what lets this check **run in CI at all**.

## How the invariant survives

`.claude/skills/conda-forge-expert/tests/meta/test_actionable_statuses_conformance.py`
imports the INSTALLED `bmad_loop.sprintstatus` and asserts **set equality** against the
literal parsed out of `deps.py` by `ast` — never by importing `pyforge.doctor`, which is
not installed in `local-recipes` where that suite runs.

Three properties, each **mutation-tested before landing**:

| mutation | required behaviour | observed |
|---|---|---|
| constant drifts from harness | fail with a both-directions diff | ✅ names `only in doctor` / `only in harness` |
| constant edited to a computed value | fail with the AD-13 reason | ✅ `not a literal (…)` |
| harness absent from the env | **fail, never skip** | ✅ `ModuleNotFoundError` at collection |

The third is a **deliberate deviation** from the sibling `test_forward_dependency_check.py`,
which guards the same import with `pytest.importorskip`. That is correct there (it skips a
module's worth of behavioural tests) and would be fatal here: a conformance assertion that
skips when its comparand is missing evaporates in exactly the environment where nobody is
watching — the failure class `unpushed_work_check.py` names as *"a gate reporting success
because it is standing somewhere the failure cannot occur."*

**Known limitation, recorded rather than papered over.** The conformance test cannot run in
CI: no workflow runs the meta-suite, and CI has no `bmad_loop` to compare against. It runs
under `pixi run -e local-recipes test`, which the landing protocol already invokes. Same
*missing observation plane* the `scope="runtime"` detectors live with — a named condition in
this repo, not a new one. Divergence is caught at landing time, not push time.

## Parity

The port reproduces the origin script's verdict on the **live repo** exactly — not against
fixtures:

```
2 measured, 3 partial, 3 no-dispatch, 0 unmeasured
partial: atlas 7/43, mason 7/30, steward 6/7
forward-dep failures: 0
```

## Two deliberate departures from a pure port

1. **No-dispatch stations are emitted as findings, not merely counted.** The origin script
   printed them as its own `○` class; folding them into a number would make a station that
   *cannot* suffer this defect indistinguishable from one that was never looked at.
2. **The coverage summary is emitted unconditionally**, including on a red run — a red
   result over 2 measured stations means something different from one over 8.

## Delivery Record

Merged via PR #353, merge commit `81c9364e3b`, 2026-08-09.
https://github.com/rxm7706/local-recipes/pull/353

Gates: `pyforge-doctor-test` **739 passed** / 1 skipped · meta-suite **2386 passed** (was 3
failed) · `detectors` **13/13 pass, exit 0** · `spec_surface_check` clean.

`pixi.toml` is **untouched**, though this story's stated surface anticipated it — the
visible signature of Option B, since the rejected alternative was the one needing a manifest
change.

## Notes

Also fixed en route, unrelated and pre-existing: `.gitignore`'s VisualStudio template block
contributes a blanket `*.log`, so `.claude/skills/conda-forge-expert/tests/fixtures/error_logs/`
could never hold a fixture — `test_failure_analyzer.py`'s two unmatched-log cases had been
running against a missing file since they were written, asserting on `"Log file not found"`
instead of the no-match contract. Narrowly negated for that fixture tree; fixture authored.
Fourth instance recorded of a broad ignore rule hiding a file nobody could see was missing.

`tests/unit/test_sources_deps_independence.py` goes one step further than every sibling
independence test: it bars `bmad_loop` as well as `pyforge.marshal`, at module scope,
lazily, and as a string constant. S-6.10 generalises that shape across every source.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `2e24406414` (2026-08-09, "doctor 6.7: forward_dependency comes home, and the harness coupling is decided"); also `451ba02272` (2026-08-07, "marshal: Story 6.7 — Entry-file family drift check, detect-only"). Ledger row `6-7-forward_dependency-comes-home-and-the-harness-coupling-is-decided: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/conda-forge-expert/tests/fixtures/error_logs/unmatched.log`, `.claude/skills/conda-forge-expert/tests/meta/test_actionable_statuses_conformance.py`, `.gitignore`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/.memlog.md`, `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-packaging-factory/.memlog.md`, `docs/dashboard/data.js`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` (+5 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
