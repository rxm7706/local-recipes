---
title: '45.1: Doctor names every CI surface that drifted, stuck or outlived its review date'
type: 'feature'
created: '2026-10-14'
status: 'done'
baseline_revision: '84bcb27e56a0f61a93ca7a04ecd317819b00e29c'
flag-exempt: detector-or-gate   # a check that judges; gating it off would bring back the silent-off surface it names (spec-feature-flag-governance Q2; bmad-spec ruling 2026-10-14, memlog)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docs/dreams/pyforge-doctor.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-3-the-operator-sees-the-pause-state-of-every-ci-surface-in-one-command.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py
  - scripts/fleet_picture.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** steward Story 99.3 landed `pyforge steward ci status --json`, one row per CI surface with a verdict, and
nothing the operator already reads shows it. The Pages deploy sat in `waiting` from 2026-10-06 to 2026-10-12 while
every check stayed green (`docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 1.4). Facts below are at
`8d04520770`.

- **The report.** `src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py` `run_status` builds
  `{fetched_at, repo, rate_limit: {core_limit, core_remaining}, rows: [...]}`, frozen by
  `data/ci-status-schema.json` (`$id: urn:local-recipes:pyforge-steward:ci-status-schema`, additive only). A row has
  `id`, `switch`, `declared_state`, `live_switch_value`, `paused_since`, `review_by`, `review_days_left`, `owner`,
  `last_green_run`, `verdict` (one of `live`, `paused`, `opt-in-off`, `paused-manually`, `retired`, `drift`, `stuck`,
  `overdue`) and an optional `detail`.
- **Verdict precedence** (`_build_rows`): `drift`, then `stuck`, then `overdue` (`review_days_left < 0`), then the
  state verdict. A drifted or stuck row past its review date therefore reads only `drift` or `stuck`, while
  `review_days_left` still carries the date.
- **What `drift` and `stuck` cover.** `drift`: a live switch value or workflow state the registry declares otherwise
  (`_is_drift`), a `PAUSE_*`/`ENABLE_*` variable with no row (`unregistered:<NAME>`), a `disabled_manually` workflow
  with no `paused-manually` row (`unregistered-workflow:<file>`); these carry `detail`. `stuck`: the row's
  `stuck_rules` (`consecutive_cancelled_runs`, `deploy_waiting_hours`; `_row_stuck`) and, once Story 99.6 lands, a
  paused `cost: high` row with no recent green canary; these carry no `detail`.
- **Exit codes** (`cli.py` `main`): exit 0 with the report on stdout; exit 1 (`partial`: one workflow's run list
  failed) with the report on **stderr**; exit 3 (`EXIT_CI_REFUSAL`) with a one-line refusal on stderr when `gh` is
  unauthenticated, the core rate limit is 60 or exhausted, or `pyforge.steward.ci_pause_control` is off (off in staging
  and production, on in dev). `pyforge.core.dispatch` exits 127 when no steward distribution is installed (the
  `pyforge-doctor` env carries none; `pyforge-guild` does).

**Approach:** one new Doctor source, `ci-pause-drift`, in the shape of `sources/sibling_dreams.py` (a live read,
warn-only, an explicit "could not read" finding instead of silence), registered and dispatched like every source,
and one `fleet-picture` ATTENTION probe in the shape of `sibling_dreams_drift_findings`.

- **Model.** `Source.CI_PAUSE_DRIFT = "ci-pause-drift"` in `models.py` (AD-3: the closed taxonomy extended); a
  `REGISTRY` entry with `scope="runtime"`, `subject_station="steward"`, `owning_station="doctor"`; a `DISPATCH` entry
  in `sources/__main__.py`.
- **The read.** One new helper in `cli_bridge.py` (AD-12: a new subprocess need is met there) that runs an argv list
  with a bounded timeout, `NO_COLOR=1` and `stdin=DEVNULL`, and returns the exit code, stdout and stderr, raising the
  one typed `CliBridgeError` only for a launch failure or a timeout. `run_cli_json` does not fit: it runs a script
  path and raises on every non-zero exit, and this read must tell exit 1 from exit 3. The source calls it with
  `[sys.executable, "-m", "pyforge.core.dispatch", "steward", "ci", "status", "--json"]` from the repo root.
- **Rules, per row.** `verdict == "drift"` → one `ci-pause-drift` WARN; `verdict == "stuck"` → one `ci-pause-stuck`
  WARN; an integer `review_days_left < 0` → one `ci-pause-overdue` WARN, whatever the verdict. Each message names the
  row `id`, its `switch` and its `owner`, and appends `detail` when present; `ci-pause-stuck` also names
  `last_green_run`; `ci-pause-overdue` names `review_by` and the days overdue. `evidence` carries the row as read.
- **Outcomes.** Exit 0 and a payload with a `rows` list → judged; no WARN → one OK finding counting the rows judged.
  Exit 1 and a stderr that parses to a payload with a `rows` list → judged, plus one `ci-pause-partial` WARN. Any
  other outcome (exit 3, exit 127, any other code, a timeout, a launch failure, unparseable JSON, a payload without a
  `rows` list or with a row missing `id` or `verdict`) → exactly one `ci-pause-unobserved` WARN naming the exit code
  and the first stderr line, and no OK.
- **fleet-picture.** `ci_pause_drift_findings()` runs `python -m pyforge.doctor.sources ci-pause-drift --json` with
  the same subprocess discipline as `sibling_dreams_drift_findings` and returns the WARN findings; `main()` appends
  one `watch` line per finding (`<check>: <first line of message, 110 chars>`) and `could not check CI pauses` when the
  probe raises, beside the other Doctor probes.

Ledger key: `45-1-doctor-names-every-ci-surface-that-drifted-stuck-or-outlived-its-review-date`.
Type / Effort / Deps: feature / S / none (steward 99.3 is `done` on `main`).

### Living CAP citations

- **`spec-pyforge-doctor` CAP-89** (FR-22): this story builds the whole capability.
- **`spec-pyforge-steward:CAP-166`** (Story 99.3; Story 99.6 adds the canary rule to `stuck`): the report it reads.
  Doctor imports no `pyforge.steward` module and calls no `gh`.
- **AD-2** (warn never changes the exit code), **AD-3** (closed `Source` enum, extended), **AD-5 / AD-12** (one
  subprocess site, `cli_bridge`), **NFR-1** (read-only), **NFR-4** (not in `doctor check`'s default set, so the
  speed budget does not move). AD-11 does not bind it: it judges the CI surfaces, not steward's own conformance, and a
  broken or absent steward reads as `ci-pause-unobserved`.
- **Flag:** `flag-exempt: detector-or-gate`. The source only judges; gating it off would reproduce the silent-off
  surface it exists to name. Ruled by `bmad-spec` on 2026-10-14 (memlog), against the plan's proposed
  `pyforge.doctor.ci_pause_drift`.
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, the 2026-10-12 and 2026-10-14 (ci pause drift)
  entries; the plan's § 4.4, § 5 and § 6; the operator's rulings Q1–Q8 of 2026-10-12.

## Acceptance Criteria

- **AC1 — One finding per rule.** Recorded `steward ci status --json` fixtures under
  `src/shared/packages/pyforge-doctor/tests/fixtures/ci_pause_drift/`, one per rule, each yield exactly one WARN of
  the matching check naming the row `id`: a `drift` row (`ci-pause-drift`); an `overdue` row (`ci-pause-overdue`);
  the 2026-10-06 waiting-deploy replay on `dashboard.deploy` (`ci-pause-stuck`); a five-cancelled streak
  (`ci-pause-stuck`); a stale canary on a paused `cost: high` row (`ci-pause-stuck`).
- **AC2 — Overdue is read from the date.** A `drift` row with `review_days_left: -3` yields two WARNs
  (`ci-pause-drift`, `ci-pause-overdue`); a row with `review_days_left: 0` yields no `ci-pause-overdue`.
- **AC3 — Quiet rows stay quiet.** `live`, `paused`, `opt-in-off`, `paused-manually` and `retired` rows with
  `review_days_left` null or at least 0 yield no WARN, and the report yields one OK finding naming the row count.
- **AC4 — Never a false clean.** A fake bridge returning exit 3 (each of the three refusals), exit 127, exit 2, a
  timeout, a launch failure, non-JSON stdout, a payload without `rows`, and a row without `verdict` each yields
  exactly one `ci-pause-unobserved` WARN naming the exit code or cause, and no OK finding.
- **AC5 — Partial read.** Exit 1 with a valid report on stderr yields its row findings plus one `ci-pause-partial`
  WARN.
- **AC6 — Warn never moves the exit code.** `python -m pyforge.doctor.sources ci-pause-drift --json` exits 0 on every
  fixture above, the unobserved ones included, and prints a JSON list of findings; every finding's status is `warn`
  except the OK row.
- **AC7 — The fixtures are the contract.** A test validates every fixture payload against
  `src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json` (read as a file by repo path,
  never imported) and fails naming the fixture that does not.
- **AC8 — Wired.** `Source.CI_PAUSE_DRIFT`, its `REGISTRY` row (`runtime`, subject `steward`, owner `doctor`) and its
  `DISPATCH` row exist, and the existing dispatch and registry tests cover them; `fleet-picture` prints one watch line
  per WARN from a stubbed probe, and `could not check CI pauses` when the probe raises.
- **AC9 — Boundaries hold.** The meta-tests stay green: `cli_bridge` is the only module that spawns a subprocess
  (`test_cli_bridge_sole_subprocess.py`), and no module under `pyforge.doctor` imports `pyforge.steward`. No test runs
  a live `steward`, `pyforge` or `gh`.
- **AC10 — Mutations.** Each fails a named test: a rule finding emitted as `fail`; `ci-pause-overdue` read from
  `verdict == "overdue"` instead of `review_days_left`; an unreadable report returned as the OK row; the partial
  shape treated as unobserved.

## Boundaries & Constraints

- Read-only (NFR-1): no `gh` call, no write, no read of `docs/governance/ci-surfaces.yaml`, no copy of steward's
  verdict rules. Pauses are written only through `steward ci pause|resume --yes` (`spec-pyforge-steward:CAP-166`).
- No steward file changes, including its schema: a missing `detail` on `stuck` rows is the Spec's open question,
  steward's to answer on its own chain.
- Not added to `doctor check`'s default set, `monitor --fleet`'s axes, `scripts/detectors.py` or `detectors-ci`; no
  pixi task (it runs through the sources dispatcher, as `sibling-dreams-drift` does), so `pixi.toml`,
  `environment.yaml` and the generated reference pages do not move.
- The subprocess call lives in `cli_bridge` only (AD-5, AD-12); the source module imports no `subprocess`.
- `doctor check`'s findings, exit code and speed-budget test are unchanged.
- Python from the doctor env only; `jsonschema` is already a doctor run-dep (check
  `docs/reference/library-llms-full.md` before importing anything else).

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| exit 0, every row `live` or `paused` within its date | one OK finding naming the row count |
| exit 0, `rows: []` | one OK finding, count 0 |
| exit 0, a `drift` row with `review_days_left: -3` | `ci-pause-drift` and `ci-pause-overdue` |
| exit 0, a `stuck` row with no `detail` | `ci-pause-stuck` naming id, switch, owner, `last_green_run` |
| exit 0, `unregistered:PAUSE_FOO` drift row (`owner: null`) | `ci-pause-drift` naming the id and `detail`; owner shown as `(none)` |
| `review_days_left: 0` | not overdue |
| exit 1, valid report on stderr | row findings plus `ci-pause-partial` |
| exit 3, `ci: refused — flag pyforge.steward.ci_pause_control is off` | one `ci-pause-unobserved` naming exit 3 and that line |
| exit 127 (no steward installed) | one `ci-pause-unobserved` naming exit 127 |
| bridge timeout | one `ci-pause-unobserved` naming the timeout |
| stdout `not json` with exit 0 | one `ci-pause-unobserved` |
| payload `{"rows": "x"}` or a row without `verdict` | one `ci-pause-unobserved` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-89 (FR-22), minted 2026-10-14.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-12 and 2026-10-14 (ci pause drift) entries.
- Epic: Epic 45 (new, reserved by the plan's § 5), Story 45.1. `epic-45` and `epic-45-retrospective` are minted with it.
- Ledger key: `45-1-doctor-names-every-ci-surface-that-drifted-stuck-or-outlived-its-review-date`.
- Ledger status at mint: `backlog`.
- Deps: none. Steward Story 99.3, which ships the report, is `done` on `main`. Story 99.6 (in flight at mint) adds the
  canary rule to steward's `stuck`; this story reads `stuck` whichever rule produced it, so 99.6 is not a gate.
- Surface: `marshal-policy.toml` `[epic_surfaces]."45"` (added with this mint). `scripts/fleet_picture.py` is
  allowlisted in `scripts/spec_surface_allowlist.txt` and named in `spec-pyforge-marshal`'s surface; reconcile every
  Spec `spec-surface-check` names.
- `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass, with AC1–AC10's tests (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py -q` — expected: pass (AC1–AC7, AC10).
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py -q` — expected: pass (AC8, AC9).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_fleet_picture_ci_pauses.py -q` — expected: pass (AC8's `fleet-picture` half).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` and `pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test` — expected: pass (the Detectors workflow's scripts lane).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0 (the source is not in it; nothing it judges moves).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` and `pixi run --frozen -e pyforge-guild flag-gate-check -- --spec <this spec>` — expected: exit 0 and `pass`.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- The four mutations of AC10 — expected: each fails its named test. Restore each.
- Operator, after landing, with `gh` authenticated and the steward flag on: `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources ci-pause-drift` — expected: exit 0, and a `ci-pause-overdue` WARN for any live pause past 2026-11-01; then `python scripts/fleet_picture.py` shows the same lines under ATTENTION.

## Auto Run Result

Status: done  
Verification: `pyforge-doctor-test` (3655 passed), `tests/scripts/test_fleet_picture_ci_pauses.py` (5 passed), `spec_surface_reconcile.py` (OK). Surface reconcile memlogs on `spec-pyforge-doctor`, co-governor `spec-pyforge-core`, and `spec-pyforge-marshal`.

## Spec Change Log

- 2026-10-14: minted with CAP-89 / FR-22 and Epic 45 from the Dream entries of 2026-10-12 and 2026-10-14 (ci pause
  drift), the plan's § 4.4, § 5 and § 6, and steward's landed `ci status` (Story 99.3). `type: feature`,
  `flag-exempt: detector-or-gate` by `bmad-spec` ruling (memlog 2026-10-14), not the plan's proposed
  `pyforge.doctor.ci_pause_drift`. The Dream's `monitor --fleet` `ci` axis is a recorded non-goal.
