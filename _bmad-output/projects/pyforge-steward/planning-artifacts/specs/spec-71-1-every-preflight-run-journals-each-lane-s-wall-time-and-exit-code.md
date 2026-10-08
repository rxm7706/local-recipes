---
title: "71.1: Every preflight run journals each lane's wall time and exit code"
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: ba6ec72d3296a640d2b86794e7d0dc305c869763
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pr-preflight` is a pixi `depends-on` aggregate (`pixi.toml`, `[feature.guild-tasks.tasks.pr-preflight]`) whose legs `lint-types`, `pyforge-station-tests` and `pyforge-station-coverage-gates` nest further aggregates — 28 leaf lanes that pixi runs one at a time, reporting only the final exit. The Dream's per-lane table (2026-09-27: 622.8 s serial on a 16-core laptop, marshal-only branch) had to be measured by hand, one `pixi run` per lane. With no journal, the one-minute budget CAP-159 sets cannot be measured, and a lane that grows is invisible until someone times it again. This story is the prerequisite for 71.2–71.7; it changes no lane, no order and no verdict.

**Approach:** a new module `pyforge.steward.preflight` (`src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py`) becomes `pr-preflight`'s `cmd`: `python -m pyforge.steward.preflight` — a `python -m` entry beside `frames.py` (`frame-preflight` runs `python -m pyforge.steward.frames`), not a new `steward` duty, so `DUTIES` and the duty-count tests do not move and the module's own `main()` owns its exit code (AD-8). The lane list stays declared once, in `pixi.toml`: today's `pr-preflight` aggregate moves, unchanged, to a task `pr-preflight-lanes` (still runnable as the serial reference). The runner reads `pixi.toml` with `tomllib` and flattens `pr-preflight-lanes`' `depends-on` recursively into leaf lanes, each `(task, environment)`, in declaration order: an entry with an `environment` runs there; a bare entry runs in the environment `pr-preflight` itself was invoked from (`PIXI_ENVIRONMENT_NAME`), exactly as pixi's own `depends-on` does; a task carrying both `depends-on` and `cmd` contributes its own lane after its dependencies. Each lane runs as `pixi run --frozen -e <env> <task>`; the first red lane stops the run, as pixi's `depends-on` does today. Every run appends one JSON line to `.steward/preflight-runs.jsonl` (gitignored): run id, start time (UTC), HEAD sha, branch, the machine's logical core count, total wall seconds, verdict, and per lane `{task, environment, seconds, exit_code, status}` with status `ok` / `red` / `not-run`. Exit codes: 0 every lane exited 0; 1 a lane exited non-zero (named on stderr); 2 the lane list could not be read (no `pixi.toml`, no `pr-preflight-lanes`, a cycle, a task that does not exist) — no lane runs, never a silent 0.

Ledger key: `71-1-every-preflight-run-journals-each-lane-s-wall-time-and-exit-code`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-159 (FR-32; extends CAP-154 — the `pre-push` hook runs this command).

## Acceptance Criteria

- Given a fixture `pixi.toml` whose lane aggregate nests two aggregates, mixes bare and `environment` entries, and holds one task with both `depends-on` and `cmd` When the runner lists lanes Then it returns every leaf once, in declaration order, each with its environment (a bare entry in the invoking one) and the combined task after its dependencies
- Given the real repository `pixi.toml` When the runner lists lanes Then it returns every leaf of `pr-preflight-lanes` exactly once — the 28 of the day of mint (the five lint-types lanes, `detectors-ci`, `test-ci` in `local-recipes`, `pyforge-doctor-scripts-test` in `pyforge-ci`, `docs-map-render-test`, `docs-gen-test`, `pyforge-core-test` and the eight station suites, the eight coverage gates, `site-check` in `site`), derived, never a hard-coded list
- Given a lane runner faked to exit 1 on the third leaf When the preflight runs Then it exits 1 naming that lane, runs no later lane, and appends exactly one journal line whose lanes carry seconds, exit code and status `ok` / `red` / `not-run`
- Given every fake lane exits 0 When the preflight runs Then it exits 0 and the journal line's verdict is `ok` with the total wall time and core count recorded
- Given a `pixi.toml` with no `pr-preflight-lanes`, or a `depends-on` naming a task that does not exist When the preflight runs Then it exits 2 and runs no lane
- Given the `pre-push` hook When it runs the preflight Then its command is still `pixi run --frozen -e pyforge-guild pr-preflight` (`tests/scripts/test_lint_types_gate.py` unchanged and green)
- Given pyforge-core's `tests/meta/test_conformance_lane_wired.py` When it reads the preflight lane list Then it reads `pr-preflight-lanes` and still finds `pyforge-station-tests` there

## Boundaries & Constraints

**Always:**
- The lane list is read from `pixi.toml`, never copied into steward (derive, don't declare); steward code reads `pixi.toml` and never writes it (AD-5).
- A lane's verdict is its process exit code — never its output, never through a pipe.
- The journal records every run, green or red; write it with an append and create `.steward/` if absent.
- `pixi.toml` changes (the rename, the new `cmd`): regenerate `environment.yaml` (`pixi project export conda-environment -e build > environment.yaml`) and `docs/how-to/pixi-tasks.md` (`pixi run -e pyforge-guild docs-pixi-tasks`) in the same change; `pixi.toml` is shared surface, so run `pixi run -e pyforge-guild pyforge-station-tests` before pushing.
- Cross-station seam: `src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py` is `spec-pyforge-core`'s (marshal project) — append its memlog, then reconcile and scoped-stamp every Spec `spec-surface-check` names (`pixi.toml` has several governors); a co-governor memlog entry moves that Spec's date, so run `python scripts/chain_currency_sweep_check.py --project <slug> --json` for each and carry its cascade note if it fires.

**Never:**
- Do not add, drop, reorder or skip a lane — selection is Story 71.2, concurrency Story 71.3.
- Do not change the `pre-push` hook's command line, its skips or its skip journal (`.steward/preflight-skips.log`, CAP-156); `PYFORGE_PREFLIGHT_SKIP=1` stays the hook's.
- Do not register a `steward` duty for this.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| all green | 28 lanes exit 0 | exit 0, one journal line, verdict `ok` | — |
| one red | lane N exits non-zero | exit 1, lanes after N `not-run` | red lane named on stderr |
| bare entry | `"detectors-ci"` in the aggregate | runs in the invoking env | `PIXI_ENVIRONMENT_NAME` unset → `pyforge-guild` |
| aggregate missing | no `pr-preflight-lanes` | exit 2, no lane run | message names what is missing |
| unknown task | `depends-on` names a task no feature defines | exit 2 | names the task |
| journal dir absent | no `.steward/` | created, line appended | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-159 (FR-32).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 — Proposed: the preflight answers in under a minute*.
Ledger key: `71-1-every-preflight-run-journals-each-lane-s-wall-time-and-exit-code`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (the lane-wired meta-test reads `pr-preflight-lanes`).
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_lint_types_gate.py -q` — expected: pass (the hook's command line unchanged).
- `pixi run -e pyforge-guild pr-preflight` — expected: the same verdict as `pixi run -e pyforge-guild pr-preflight-lanes`, and one new line in `.steward/preflight-runs.jsonl` with every derived leaf lane.

## Auto Run Result

Status: done

Summary: Added `pyforge.steward.preflight` as the `pr-preflight` cmd, moved the prior aggregate to `pr-preflight-lanes`, journal append to `.steward/preflight-runs.jsonl`, and updated cross-station meta-tests to read the renamed aggregate.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` — lane flatten + serial runner + journal
- `src/shared/packages/pyforge-steward/tests/unit/test_preflight.py` — matrix and AC coverage
- `pixi.toml` — `pr-preflight-lanes` + `pr-preflight` cmd
- `.gitignore` — ignore journal file
- `environment.yaml`, `docs/how-to/pixi-tasks.md` — pixi regeneration
- Co-governor meta-tests (core, doctor, herald) — `pr-preflight-lanes`
- Spec memlogs (steward, core, doctor, herald)

Review: no patch-tier findings after self-review of the diff.

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — pass
- `pixi run --frozen -e pyforge-core pyforge-core-test` — pass
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_lint_types_gate.py -q` — pass
- `python scripts/spec_surface_reconcile.py` — exit 0

Residual risk: full `pr-preflight` against live pixi legs remains operator-expensive; journal shape is append-only JSONL with no rotation (future story scope).
