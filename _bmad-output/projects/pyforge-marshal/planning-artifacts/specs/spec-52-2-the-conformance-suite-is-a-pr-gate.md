---
title: '52.2: The conformance suite is a PR gate'
type: 'infra'
created: '2026-09-19'
status: 'done'
baseline_revision: '9390a5e24982bf8be431933025cb0761237acd15'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** No CI workflow invokes the `pyforge-core-test` pixi task, so the four `tests/meta/*_sole_ownership.py` meta-tests (CAP-5/CAP-7's enforcement) have never run on a PR: `.github/workflows/pyforge-station-tests.yml` has eight station jobs and no core job (it lists `pyforge-core/**` only as a shared-surface *trigger* for the eight), `pyforge-pip-install.yml` runs a hand-enumerated subset (`tests/unit` + three named meta files) while its header claims the station-tests workflow "already runs every one of the tests below", and the local `pyforge-station-tests` aggregate (what `pr-preflight` depends on) lists the eight station tasks only. Six CAP-5/CAP-7 violations accumulated unseen between 09-07 and 09-15 and were cleared by Story 52.1 — the gate must exist so it cannot happen again.

**Approach:** Add a `core-test` job beside the eight station jobs in `pyforge-station-tests.yml`, gated by a new `core` output of the `changes` filter that is true whenever ANY `src/shared/packages/` path changed (the shared-surface set or any station — the meta-tests scan every sibling station's tree, so any station change can introduce a violation), running exactly `pixi run --frozen -e pyforge-core pyforge-core-test` (the whole `tests/` tree, meta included — never an enumerated file list); add `{ task = "pyforge-core-test", environment = "pyforge-core" }` as the first leg of the `pyforge-station-tests` depends-on so `pr-preflight` inherits it; correct `pyforge-pip-install.yml`'s header claim and the two CLAUDE.md sentences that describe the lane set; regenerate `environment.yaml` (pixi.toml moved).

## Boundaries & Constraints

**Always:**
- The CI job and the local task both invoke the pixi task `pyforge-core-test` — no `pytest <file list>` anywhere (enumeration is how the meta-tests were lost).
- The `core` filter output is true when `SHARED_CHANGED` is true OR any station's `src/shared/packages/pyforge-<s>` diff is non-empty OR `.github/workflows/pyforge-station-tests.yml` changed; the job runs on `pull_request` and `push: main` exactly like its siblings (`needs: changes`, `if: needs.changes.outputs.core == 'true'`, `prefix-dev/setup-pixi@v0.10.2` with `environments: pyforge-core`, `cache: true`, `timeout-minutes: 30`).
- `pyforge-station-tests`' depends-on gains the core leg first (it is the cheapest, ~10 s, and fails fastest); the task description and CLAUDE.md's two descriptions of the lane set say "pyforge-core + the 8 stations".
- `pyforge-pip-install.yml`'s header no longer claims the station-tests workflow runs every test below; it says that lane runs the core suite via the pixi task and that pip-install's value is the installation path.
- `pixi project export conda-environment -e build > environment.yaml` is run after the `pixi.toml` edit and the result committed (the sync check is ungated by the `maintenance` label).
- Local proof before landing: `pixi run --frozen -e pyforge-guild pyforge-station-tests` green from the worktree (all nine legs), and the fixture proof — a scratch second `subprocess.run` implementation dropped under `src/shared/packages/pyforge-marshal/src/pyforge/marshal/` makes `pixi run --frozen -e pyforge-core pyforge-core-test` exit non-zero, then is removed (recorded in the Auto Run Result, never committed).

**Never:**
- Do not add a `pixi.toml` dependency, change any threshold, touch station code or tests, or restructure the workflow beyond the one new job + one new filter output; do not edit `pyforge-pip-install.yml`'s job steps (only its header comment).
- Do not make `core-test` a job the others `need` (it is a peer, not a gate on them).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| station-only PR | only `src/shared/packages/pyforge-herald/**` changed | `core=true`; `core-test` runs; herald-test runs; others skip | — |
| shared-surface PR | `pixi.toml` changed | `core=true`; all nine jobs run | — |
| docs-only PR | only `docs/**` changed | workflow does not trigger at all (paths filter unchanged) | — |
| violation introduced | a second `subprocess.run` under a station's `src/pyforge` | `pyforge-core-test` exits 1 → `core-test` red | — |
| local aggregate | `pixi run --frozen -e pyforge-guild pyforge-station-tests` | core leg first, then the eight; first red stops the run | — |

</intent-contract>

## Code Map

- `.github/workflows/pyforge-station-tests.yml:71-117` -- the `changes` job: outputs (one per station) + the `SHARED_CHANGED` shell that already diffs `pyforge-core`, `pyforge-testing-kit`, `pixi.toml`, `pixi.lock`, and this workflow file; the per-station loop writes `$s=true|false`. Add `core` to `outputs:` and compute it in the same shell (true if `SHARED_CHANGED` or any station diff non-empty).
- `.github/workflows/pyforge-station-tests.yml:155-167` (`doctor-test`) and `:279-294` (`warden-test`) -- the job shape to mirror for `core-test` (place it before `atlas-test`, after `changes`).
- `pixi.toml:1268-1287` -- `[feature.guild-tasks.tasks.pyforge-station-tests]` description + `depends-on` list of eight `{ task, environment }` entries; `:949` -- `pyforge-core = { features = ["pyforge-core"], no-default-feature = true }` (the lean env); `:2837-2839` -- `[feature.pyforge-core.tasks.pyforge-core-test]` = `pytest src/shared/packages/pyforge-core/tests -q`.
- `pixi.toml:1300-1310` -- `pr-preflight` depends-on already includes `pyforge-station-tests` (inherits the new leg; no edit needed).
- `.github/workflows/pyforge-pip-install.yml:1-14` -- header comment with the false claim (lines 5-6); `:102-108` the enumerated subset (leave the steps as they are).
- `CLAUDE.md` -- "Critical Rule — PR CI gates" item 3 (`pyforge-station-tests` … "ALL 8 station suites") and § Common Commands › Tests "**All 8 PyForge stations** (mirrors …)": both gain "+ `pyforge-core`" wording.
- `environment.yaml` -- regenerated artifact of `pixi.toml` (`pixi project export conda-environment -e build`).
- `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py` -- the guard the fixture proof exercises (scratch violation under marshal's tree; `_OUT_OF_SCOPE_STATIONS` excludes doctor/warden/steward/herald/mason/scribe, so use marshal or atlas for the fixture).

## Tasks & Acceptance

**Execution:**
- `.github/workflows/pyforge-station-tests.yml` -- add `core` output + computation to `changes`; add the `core-test` job -- CAP-8.
- `pixi.toml` -- `pyforge-station-tests` depends-on gains the core leg first; description updated -- CAP-8 (local twin).
- `environment.yaml` -- regenerate -- repo PR gate.
- `.github/workflows/pyforge-pip-install.yml` -- header comment corrected -- VG-other-2 from 52.1.
- `CLAUDE.md` -- two lane-set sentences -- docs that list the lanes.

**Acceptance Criteria:**
- Given the worktree, when `pixi run --frozen -e pyforge-guild pyforge-station-tests` runs, then the core leg runs first and all nine legs pass.
- Given a scratch second `subprocess.run` under `pyforge-marshal/src/pyforge/marshal/`, when `pixi run --frozen -e pyforge-core pyforge-core-test` runs, then it exits non-zero (then the scratch file is removed and the suite is green again).
- Given the workflow file, when parsed as YAML, then `jobs.core-test.if` reads `needs.changes.outputs.core == 'true'` and its single run step is the pixi task.

## Spec Change Log

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 20 findings — high 0, medium 1, low 13, false 2, maybe-false 0 (+6 descriptive divergences from the intent-alignment layer, logged)
- findings:
  - `[low]` `[patch]` (BH-1) spec-pyforge-core records nothing and is not re-stamped for `pixi.toml`; the detector's OK is masked by co-governors' moved memlogs — verified; action: the landing step's memlog entry names `pixi.toml` and the new test file and stamps scoped (done in this landing).
  - `[low]` `[patch]` (BH-2) CAP-8's negative proof (the scratch violation reds the lane) is in no artifact — verified; action: recorded under Auto Run Result with both exit codes and the failing test id.
  - `[false]` `[reject]` (BH-3) tracked story artifacts not advanced — the hand-driven landing step advances them (this landing).
  - `[low]` `[patch]` (BH-4) the workflow's header still says "8 stations, uniformly" — verified; action: header names the ninth, non-station `core-test` job and its gate.
  - `[low]` `[patch]` (BH-5 / ECH-3 / VG-other / IA-D5) CAP-8 and the story say `src/shared/packages/**` while the built gate covers `pyforge-*` only (the `django-*` packages are neither triggers nor `core` inputs) — verified: the sole-ownership scan itself covers `pyforge-*` dirs only, so the difference has no runtime effect; action: stated in the `core-test` comment, and CAP-8's wording narrowed to what the scan covers via memlog at landing.
  - `[low]` `[patch]` (BH-6 / IA-D4) CLAUDE.md rule 3 conflated the local depends-on order with CI (in CI `core-test` is a concurrent peer) — verified; action: the two facts split.
  - `[low]` `[patch]` (BH-7) `docs/how-to/github-actions-recipe-ci.md`'s Role cell omits the conformance job — verified; action: extended (its governing spec-pyforge-doctor memlog named + stamped).
  - `[low]` `[patch]` (BH-8) the pip-install header said the enumerated subset "deliberately does not carry" meta-tests while three remain — verified; action: header made precise (the three stay as outside-pixi importability proofs; the sole-ownership guards are not in it; the list must not grow); job steps untouched.
  - `[low]` `[reject]` (ECH-1) a planning-spec rename could break `test_cli_parity_matrix` while `core-test` skips a docs-only PR — real but pre-existing (that test's coupling to planning artifacts predates this story) and the docs-only non-trigger is the intent's own I/O row; fixing it means widening `on.paths` beyond the story.
  - `[low]` `[patch]` (ECH-2) a ninth `pyforge-*` directory would be scanned by the guards but not set `core=true` (hardcoded roster) — verified; action: the structural test derives the roster from the filesystem and asserts every `pyforge-*` dir is a path trigger and (for stations) in the loop roster.
  - `[medium]` `[patch]` (VG-1) nothing pins the CI wiring: deleting the job, the in-loop `CORE_CHANGED=true`, or the pixi leg would red nothing — verified by the reviewer's demonstration; action: `pyforge-core/tests/meta/test_conformance_lane_wired.py` (stdlib-only: regex over the workflow text, `tomllib` over `pixi.toml`, filesystem roster) with six mutation proofs.
  - `[false]` `[reject]` (IA-D2) `environment.yaml` "not committed" — the export is byte-identical; there is nothing to commit; the sync check passes.
  - `[low]` `[reject]` (IA-D1 / D3 / D6) station-only path not exercised by this PR's own CI (the structural test and the fixture proof cover it); docs edits broader than enumerated (same direction as the goal); governance side effects (the spec-surface ritual) — none a defect.

## Auto Run Result

Status: done
Blocking condition: none

**Summary of implemented change:** pyforge-core's whole `tests/` tree — the four sole-ownership meta-tests included — is now a PR gate. `.github/workflows/pyforge-station-tests.yml` gains a `core` output on the `changes` filter (true when the shared surface OR any station changed) and a `core-test` job (peer of the eight station jobs) running exactly `pixi run --frozen -e pyforge-core pyforge-core-test`; `pyforge-station-tests`' depends-on gains the core leg first, so `pr-preflight` inherits it; a structural meta-test pins the wiring; the pip-install header, CLAUDE.md and the GitHub-Actions how-to describe the lane set truthfully.

**Files changed:**
- `.github/workflows/pyforge-station-tests.yml` — `core` output + `CORE_CHANGED` in the changes filter; `core-test` job; header and `django-*` exclusion comments.
- `pixi.toml` — `pyforge-station-tests` depends-on: core leg first; descriptions of the lane set.
- `src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py` (new) — 10 tests: job/gate/run-step shape, `changes` wiring, pixi leg, filesystem-derived roster vs triggers; six mutation proofs.
- `.github/workflows/pyforge-pip-install.yml` — header comment corrected (job steps untouched).
- `CLAUDE.md`, `docs/how-to/github-actions-recipe-ci.md` — lane-set descriptions.
- `environment.yaml` — regenerated, byte-identical (no dependency moved).

**Fixture proof (the story's Then, recorded, never committed):** with a scratch `src/shared/packages/pyforge-marshal/src/pyforge/marshal/_scratch_violation.py` calling `subprocess.run(["true"], check=False)`, `pixi run --frozen -e pyforge-core pyforge-core-test` → `FAILED tests/meta/test_process_sole_ownership.py::test_no_second_subprocess_implementation[pyforge-marshal/src/pyforge/marshal/_scratch_violation.py]` ("invokes a subprocess directly at line(s) [11] -- a second subprocess implementation outside pyforge-core (CAP-7 …)"), 1 failed / 1866 passed, **exit 1**; scratch file removed → 1863 passed, **exit 0**.

**Review findings breakdown:** patched — VG-1 (medium; structural test), BH-1/BH-2 (landing record), BH-4, BH-5 group, BH-6, BH-7, BH-8, ECH-2; rejected — BH-3 (landing concern), ECH-1 (pre-existing coupling; the docs-only non-trigger is the intent's own row), IA-D2 (nothing to commit), IA-D1/D3/D6 (not defects).

**Follow-up review recommendation:** false — one medium patched, no high. Patched counts: high 0 / medium 1 / low 7.

**Verification performed (exit codes read directly):** `pyforge-core-test` 1873 passed (1863 + the 10 new); the nine-leg `pixi run --frozen -e pyforge-guild pyforge-station-tests` from the worktree: core (first) 1863, atlas 1871, doctor 1749, herald 1488, marshal 8225, mason 1589 + 12, scribe 358 green, steward 1 failed on the operator-machine `bmad-eval-quality` probe (its own comment exempts it under `CI`; `CI=1 pyforge-steward-test` 1277 passed), warden 2122; workflow YAML shape asserted; `changes`-step shell replayed over five real commit ranges matching every I/O-matrix row; `environment.yaml` export byte-identical; `spec-surface-check` ok after the steward + doctor reconciles.

**Residual risks:** the local aggregate's steward leg is red in a fresh worktree without the `local-recipes` env (an operator-machine probe, CI-exempt); CAP-8's wording said `src/shared/packages/**` and is narrowed at landing to what the scan covers (`pyforge-*`).

## Binding

Parent Spec capability: `spec-pyforge-core CAP-8`.
Surface: `.github/workflows/pyforge-station-tests.yml` (a `core-test` job beside the eight station jobs, same shared-surface triggers, running `pixi run --frozen -e pyforge-core pyforge-core-test`), `pixi.toml` (`pr-preflight` depends on `pyforge-core-test`; `environment.yaml` regenerated), docs that list the lanes.
Ledger key: `52-2-the-conformance-suite-is-a-pr-gate`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-52-2-the-conformance-suite-is-a-pr-gate.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 52.2 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
