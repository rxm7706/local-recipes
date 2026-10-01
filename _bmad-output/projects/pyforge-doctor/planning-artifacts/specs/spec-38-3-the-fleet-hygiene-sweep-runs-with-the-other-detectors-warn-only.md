---
title: "38.3: The fleet hygiene sweep runs with the other detectors, warn-only"
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: '0a93bd41a886326ba18faf6f05bba4caa946649d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py
  - scripts/detectors.py
  - pixi.toml
warnings: [oversized]
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 9.2 built `sources/hygiene.py`, the fleet hygiene sweep (CAP-42), and registered `Source.BMAD_OUTPUT_HYGIENE`
(`bmad-output-hygiene`), but it is absent from `sources/__main__.py`'s `DISPATCH`, from `scripts/detectors.py` and from
`pixi.toml`, so `gather()` runs only in its own tests and its four deferrals (DW-FU-9-2, DW-FU-9-2-2, DW-FU-9-2-3,
DW-FU-9-3) describe code nothing runs (DW-OPS-2026-10-01-1). Run once by hand on 2026-10-01 it reports 5 orphan-file
warnings. Operator ruling 2026-10-01: wire it in, warn-only.

**Approach:**

- Add `Source.BMAD_OUTPUT_HYGIENE.value: hygiene.gather` to `DISPATCH`, a `guild-tasks` pixi task running
  `python -m pyforge.doctor.sources bmad-output-hygiene`, and a row in `scripts/detectors.py`.
- Its findings stay WARN (CAP-43: reported, never auto-applied); a WARN never changes an exit code.
- Re-check the four hygiene deferrals against the running source and close or update each with evidence.

Ledger key: `38-3-the-fleet-hygiene-sweep-runs-with-the-other-detectors-warn-only`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-42, CAP-43 (`spec-deferred-work-visibility` CAP-8, CAP-9), in progress; operator ruling 2026-10-01. No new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the module When `python -m pyforge.doctor.sources bmad-output-hygiene` runs Then `hygiene.gather` runs and prints its findings
- Given the detector aggregate When it runs Then it includes the hygiene source
- Given the hygiene source reports WARN findings When the aggregate's exit code is read Then it is unchanged by them
- Given the four hygiene deferrals When the story lands Then each is closed or updated with evidence from the running source
- Given the `DISPATCH` row is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `sources/hygiene.py`, `sources/__main__.py` (`DISPATCH`), `scripts/detectors.py` and an existing guild-tasks detector task in `pixi.toml`.
2. Wire the source in the three places; keep it warn-only.
3. Tests: dispatch reaches `gather`, the aggregate lists it, a WARN leaves the exit code; re-check the four deferrals.

## Boundaries & Constraints

**Always:**
- The sweep stays advisory (CAP-43).
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not make a hygiene finding FAIL.
- Do not reimplement any `hygiene_definitions` predicate.
- Do not hand-edit any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| dispatch | `bmad-output-hygiene` | runs `gather` | — |
| aggregate | detectors run | hygiene included | — |
| warn only | orphan-file WARNs | exit code unchanged | — |

</intent-contract>

## Binding

Parent capabilities: CAP-42, CAP-43 (realizes Story 9.2's promise; no new CAP). DW-OPS-2026-10-01-1.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `38-3-the-fleet-hygiene-sweep-runs-with-the-other-detectors-warn-only`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Code Map

All doctor paths below are under `src/shared/packages/pyforge-doctor/`.

- `src/pyforge/doctor/sources/__main__.py` -- `DISPATCH` (line 84) lacks the row; import block (line 50) lacks `hygiene`. `main()` already prints each finding and returns `exit_code_for(findings)`, so no logic change.
- `src/pyforge/doctor/sources/hygiene.py` -- `gather(target)` is the `Callable[[Path], tuple[Finding, ...]]` shape `DISPATCH` wants; every finding is `DoctorStatus.WARN` or the single `OK`. Module docstring (line 47) says "no dispatch wiring in this story": stale once wired.
- `src/pyforge/doctor/sources/__init__.py` -- `REGISTRY` row for `BMAD_OUTPUT_HYGIENE` already has `scope="repo"`; `scripts/detectors.py::_run_doctor_sources` reads it via `scope_for`. Read-only.
- `src/pyforge/doctor/verdict.py` -- `exit_code_for`: any FAIL -> 2, else 0; a WARN never moves it. Read-only reuse.
- `scripts/detectors.py` -- `_DOCTOR_SOURCE_TASKS` (line 204) pairs each dispatched name with its pixi task; `_run_doctor_sources` turns `exit_code_for != 0` into `FINDINGS`, else `pass`. Needs one row.
- `pixi.toml` -- `[feature.guild-tasks.tasks.*-check]` siblings, e.g. `live-proof-surface-check` (line 1401): `description` + `cmd = "python -m pyforge.doctor.sources <name>"`. Needs `bmad-output-hygiene-check`.
- `docs/how-to/pixi-tasks.md`, `docs/map.yaml` -- generated from `pixi.toml` by `scripts/docs_pixi_tasks.py`; a new task makes the page stale (`docs-currency` reds) until regenerated.
- `tests/unit/test_sources_dispatch.py` (doctor) -- `_EXPECTED_DISPATCH` pins the roster by name and identity. `tests/unit/test_sources_hygiene.py` -- fixture-repo helpers (`_init_repo`, `_git`, leaky-git-env scrub) to reuse.
- `tests/scripts/test_detectors_doctor_sources.py` (repo root) -- pins `_DOCTOR_SOURCE_TASKS` rows; DW-FU-6-9-3 notes the name -> task mapping is otherwise unvalidated.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` -- `DW-OPS-2026-10-01-1` (line 2284); `DW-FU-9-2` (1592), `DW-FU-9-2-2` (1604), `DW-FU-9-2-3` (1616), `DW-FU-9-3` (1640). Each already carries a `verified: 2026-10-01 — STANDS` line from the burn-down.
- Live baseline, 2026-10-01 in this worktree: `hygiene.gather(Path('.'))` returns 5 `orphan-file` WARNs (herald 1, marshal 2, steward 2) and `exit_code_for` = 0.

## Tasks & Acceptance

**Execution:**
- `src/pyforge/doctor/sources/__main__.py` -- import `hygiene`; add `Source.BMAD_OUTPUT_HYGIENE.value: hygiene.gather` with a Story 38.3 comment -- AC 1
- `src/pyforge/doctor/sources/hygiene.py` -- rewrite the stale "no dispatch wiring" docstring paragraph: dispatch, detectors and pixi wiring landed in 38.3; `doctor check`/`monitor` verbs stay unwired -- healed tissue, no code change
- `scripts/detectors.py` -- append `("bmad-output-hygiene", "bmad-output-hygiene-check")` to `_DOCTOR_SOURCE_TASKS` with a comment -- AC 2
- `pixi.toml` -- add `[feature.guild-tasks.tasks.bmad-output-hygiene-check]` beside `live-proof-surface-check`; then `docs_pixi_tasks.py` regenerates `docs/how-to/pixi-tasks.md` + `docs/map.yaml`, and `environment.yaml` is re-exported only if it differs -- AC 1, repo rule
- `tests/unit/test_sources_dispatch.py` -- add the row to `_EXPECTED_DISPATCH`; add an in-process `main(["bmad-output-hygiene"])` run over a `tmp_path` repo (cwd switched) asserting `gather`'s WARN lines print and the return is 0 -- AC 1, AC 3, AC 5
- `tests/scripts/test_detectors_doctor_sources.py` -- assert the `_DOCTOR_SOURCE_TASKS` row, that `pixi.toml` declares that task with the expected `cmd`, and that a WARN-only stub through `_run_doctor_sources("repo")` yields `status == "pass"`, `rc == 0` -- AC 2, AC 3, AC 5
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` -- probe each of the four deferrals against the running source and append one `verified:` line with that output; resolve `DW-OPS-2026-10-01-1` -- AC 4
- Mutation: delete the `DISPATCH` row, run the new tests, record that they fail, restore the row -- AC 5

**Acceptance Criteria:**
- Given `python -m pyforge.doctor.sources bmad-output-hygiene` run from the repo root, when it exits, then it printed its findings and the exit code is 0
- Given `python scripts/detectors.py --scope repo`, when it lists rows, then `bmad-output-hygiene` is one of them with status `pass`
- Given the full verification set below, when it runs, then every command exits 0

## Spec Change Log

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).

## Design Notes

- Warn-only needs no new code: `verdict.exit_code_for` already projects WARN to 0, and `_run_doctor_sources` maps that to `pass`. The work is registration plus tests that pin it.
- The CLI path has no `degrade_on_exception` net, and `hygiene.gather` has none either; `DW-FU-9-2` is exactly an unguarded `iterdir()`. Under `detectors.py` a raise reads `unknown` (exit 2), never green. Record that in the deferral evidence; do not widen this story into a `hygiene.py` hardening pass.
- The four deferrals are re-checked, not fixed: 9-2 and 9-2-2 mirror `board.py`'s shape (a two-file design call), 9-2-3 is the spec'd protocol, 9-3 would change a frozen evidence shape. Each stays `open` with new evidence from a live probe; only `DW-OPS-2026-10-01-1` closes.
- A probe fixture lives in the scratchpad or a `tmp_path`, never in the tracked tree.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 after the memlog entries name every governed path changed.
- `pixi run --frozen -e pyforge-guild python scripts/detectors.py --scope repo` — expected: a `bmad-output-hygiene` row reading `pass` (read the exit code from a file, never through a pipe). The aggregate's own exit code is not this story's verdict: it covers 42 detectors, and on 2026-10-01 it exits 1 because `ledger-direction` reds on pyforge-marshal 79.1 (landed-but-unpromoted), a marshal ledger state this diff cannot touch.
