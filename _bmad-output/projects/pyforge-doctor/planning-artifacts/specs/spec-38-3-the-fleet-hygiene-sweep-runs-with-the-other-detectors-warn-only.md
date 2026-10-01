---
title: "38.3: The fleet hygiene sweep runs with the other detectors, warn-only"
type: 'fix'
created: '2026-10-01'
status: 'done'
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

### 2026-10-01 — Review pass
- verdicts: 22 findings — high 0, medium 0, low 18, false 4, maybe-false 0
- findings (one row per finding, in the order the layers reported: intent-alignment, verification-gap, blind-hunter, edge-case-hunter):
  - `[low]` `[reject]` Intent-alignment: the aggregate tests call `_run_doctor_sources` directly and never `detectors.main()` or the whole production tuple — a source feeds `main()` only through its row's `(status, rc)` (`scripts/detectors.py:477-481`), the WARN-versus-FAIL control test pins that projection, and a real aggregate run read the `bmad-output-hygiene` row `pass`; a `main()`-level test would run all 42 detectors for minutes, which is more than a direct correction.
  - `[low]` `[patch]` Intent-alignment: `docs/reference/detectors.md`, generated from `_DOCTOR_SOURCE_TASKS`, is stale — verified: `docs_detectors.py --check` exited 1. Fixed: regenerated by `scripts/docs_detectors.py` (27 doctor-owned sources, new row), `--check` now exits 0, and a memlog entry names the page.
  - `[low]` `[reject]` Intent-alignment: warn-only is not crash-proof — real (reproduced twice: unreadable `_bmad-output/projects` raises `PermissionError` out of `hygiene.gather`) but it is the pre-existing DW-FU-9-2, needs a mode-000 directory (not met in everyday use), and its fix is a new guard plus a finding kind plus the cross-file design call the entry itself records; the ledger already tracks it open with this story's evidence, so a `deferred:` row would mint a duplicate.
  - `[false]` `[reject]` Intent-alignment: the live 5 WARNs appear only in ledger prose and the tests use throwaway repos — hermetic fixtures are intended; the live output was measured: `pixi run -e pyforge-guild bmad-output-hygiene-check` exits 0 and prints the 5 orphan-file WARNs, and the aggregate row reads `pass`.
  - `[false]` `[reject]` Intent-alignment: bare `python` imports `pyforge.doctor` from the primary checkout — bare `python` outside a pixi env is not a supported invocation here; the diff's tests prepend the worktree's doctor `src`, and the mutation run proved the worktree package resolves (row commented out → 4 doctor and 2 script tests failed).
  - `[false]` `[reject]` Intent-alignment: the pixi task is checked only as a string and never executed — it was executed: exit 0, 5 WARNs (as for every sibling detector task, none of which has an executing test).
  - `[low]` `[patch]` Verification-gap: `docs/reference/detectors.md` committed stale against the new registry row, with no test failing — same defect and fix as the second row above (regenerated, `--check` exit 0); a per-page live test was not added because `docs-currency`'s warn-only generated-stale finding is Story 30.3's designed signal.
  - `[low]` `[patch]` Verification-gap: the 38.3 memlog entry omits `docs/reference/detectors.md` — same root cause; a second surface-reconcile entry now names the page and the `docs/map.yaml` stamp.
  - `[low]` `[patch]` Blind Hunter: `detectors.md` not regenerated and the memlog incomplete — same root cause and fix as the two rows above.
  - `[low]` `[patch]` Blind Hunter: `test_every_doctor_source_task_name_is_a_dispatch_entry` cites DW-FU-6-9-3 but checks only the name half — fixed: docstring reworded to say exactly that, assertion unchanged; generalizing to all 27 pairs is a new check beyond this story.
  - `[low]` `[reject]` Blind Hunter: git-fixture helpers copy-pasted a third and fourth time — per-file helpers are this package's documented convention (`hygiene.py` and `test_sources_hygiene.py` say so, mirroring `test_sources_ledger.py`); a shared conftest refactor touches other test files, more than a direct correction.
  - `[low]` `[patch]` Blind Hunter: "warn-only by construction" overstates a source with a known uncaught crash — fixed: the `DISPATCH` row comment, the `_DOCTOR_SOURCE_TASKS` row comment and the `main()` comment now say findings are WARN or OK while a raise escaping `gather` (DW-FU-9-2) reads `unknown`; the guard itself is not added (see the crash row above) and the pixi task description is left alone because it describes findings.
  - `[low]` `[reject]` Blind Hunter: the sweep's cost is unmeasured — measured here: the `bmad-output-hygiene` aggregate row took 17.6 s and 21.1 s on two runs, recorded under Auto Run Result; a runtime written into a code comment goes stale (the lesson `sources/__main__.py`'s own docstring records for member counts), and no requirement is violated.
  - `[low]` `[reject]` Blind Hunter: the 5 live orphan WARNs have no disposition — the intent names the 5 WARNs as the known baseline and the operator ruled "wire it in, warn-only"; judging each file belongs to herald, marshal and steward, and minting five deferrals runs against the burn-down's stop-the-inflow ruling.
  - `[false]` `[reject]` Blind Hunter: `--json` output is not validated against the frozen schema — `report-schema.json` is the `DoctorReport` envelope (`schema_version`, `verb`, `generated_at`), while the sources dispatcher emits a bare array of `Finding.to_json_dict()` for every source, a shape the pre-existing `test_json_flag_emits_finding_to_json_dict_shape` pins.
  - `[low]` `[reject]` Blind Hunter: the deferrals were re-probed in prose only, the DW-FU-9-2 entry body contradicts its new line, and no xfail test was committed — the ledger's convention is append-only `verified:` lines under an unchanged body (the new line states which half stands), and an xfail test per open defect is new ceremony beyond the story.
  - `[low]` `[reject]` Edge Case Hunter: an unreadable `_bmad-output/projects` gives a raw traceback and exit 1 — same pre-existing DW-FU-9-2 as the third row above, tracked open in the ledger.
  - `[low]` `[reject]` Edge Case Hunter: zero stations judged still reads `ok` — Story 9.2's own I/O matrix design (the `stations` count rides the OK finding), reachable only by running the CLI from a wrong working directory because the aggregate passes the absolute repo root, and the fix adds a branch.
  - `[low]` `[reject]` Edge Case Hunter: no wall-clock budget across the per-candidate `git grep` calls — each call is already bounded by `run_git`'s 30 s timeout and the live total is about 20 s; a budget is a new mechanism.
  - `[low]` `[patch]` Edge Case Hunter: the name-only test overclaims DW-FU-6-9-3 — duplicate of the test-docstring row above, fixed there.
  - `[low]` `[patch]` Edge Case Hunter: the `main()` comment "every DISPATCH entry is wrapped by `degrade_on_exception`" and "same shape as LIVE_PROOF_SURFACE" are now false — fixed with the comment rewrite in the "warn-only by construction" row above.
  - `[low]` `[patch]` Edge Case Hunter: the new `verified:` lines cite `hygiene.py` line numbers that are off by 2 — verified: `iterdir` sat at 105 against the cited 103; the 7-line docstring replaced a 5-line paragraph. Fixed: the paragraph is 5 lines, `hygiene.py` is 389 lines again and every anchor matches the baseline revision, so the new and the 2026-09-30 citations are valid; the ledger was not edited for this.

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

## Auto Run Result

Status: done

**Summary.** The fleet hygiene sweep (`Source.BMAD_OUTPUT_HYGIENE`, Story 9.2) now runs. `hygiene.gather` is a row of `DISPATCH`, so `python -m pyforge.doctor.sources bmad-output-hygiene` prints its findings; `("bmad-output-hygiene", "bmad-output-hygiene-check")` is a row of `scripts/detectors.py`'s `_DOCTOR_SOURCE_TASKS`; and `bmad-output-hygiene-check` is a `guild-tasks` pixi task. Every finding stays WARN or the single OK, so no exit code moves. The four hygiene deferrals were re-probed against the running source and each stays open with a dated `verified:` line; `DW-OPS-2026-10-01-1` is closed.

**Files changed.**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` — imports `hygiene`; the `DISPATCH` row and its comment; the `main()` comment no longer says every entry is wrapped.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py` — docstring only: the stale "no dispatch wiring" paragraph, same line count so every cited line number holds.
- `scripts/detectors.py` — the `_DOCTOR_SOURCE_TASKS` row and its comment.
- `pixi.toml` — the `bmad-output-hygiene-check` task beside `live-proof-surface-check`.
- `docs/how-to/pixi-tasks.md`, `docs/reference/detectors.md`, `docs/map.yaml` — regenerated by `scripts/docs_pixi_tasks.py` and `scripts/docs_detectors.py`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py` — the roster row and two in-process `main()` runs (text and `--json`) over a throwaway git repo.
- `tests/scripts/test_detectors_doctor_sources.py` — the row and pixi-task pin, the name-to-`DISPATCH` check, a WARN-versus-FAIL projection test and a real unstubbed `gather` run through `_run_doctor_sources`.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` — four `verified:` lines (DW-FU-9-2, 9-2-2, 9-2-3, 9-3) and the `DW-OPS-2026-10-01-1` closure.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — surface-reconcile entries appended with `memlog.py` (the wiring, a count correction, the review-pass regeneration). No baseline was stamped.

**Review breakdown.** 22 findings: 0 high, 0 medium, 18 low, 4 false. Patches applied: 4 grouped entries (9 rows), all low — the stale generated `detectors.md` and the memlog naming it, an overclaiming test docstring, three comments that overstated "warn-only", and a docstring that shifted every cited `hygiene.py` line by 2. Deferred: 0. Rejected: 13 (9 low, 4 false), each with its recorded reason in the Review Triage Log above; the crash path is the pre-existing DW-FU-9-2, already tracked open.

**Follow-up review recommendation.** `false`: 0 high and 0 medium entries were patched.

**Verification performed** (every verdict read from a captured exit code, never a pipe):
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — exit 0, 3140 passed, 1 skipped (before and after the patch round).
- `tests/scripts/test_detectors_doctor_sources.py` and `tests/scripts/test_docs_detectors.py` — exit 0, 25 passed.
- Mutation (AC 5), measured by hand: with the `DISPATCH` row commented out, 4 doctor tests and 2 script tests fail; the row is restored. The implementation subagent had reported 3 doctor tests; the ledger and a memlog correction carry the measured 4.
- `python scripts/detectors.py --scope repo` — the `bmad-output-hygiene` row reads `pass`. The aggregate exits 1 solely because `ledger-direction` reds on pyforge-marshal 79.1 (landed-but-unpromoted), which this diff cannot touch; the Verification section above was corrected from "exit 0" to say so.
- `pixi run -e pyforge-guild bmad-output-hygiene-check` — exit 0, the 5 orphan-file WARNs (herald 1, marshal 2, steward 2).
- `docs_detectors.py --check` and `docs_pixi_tasks.py --check` — exit 0; `lint-types` — exit 0; `python scripts/spec_surface_reconcile.py` — exit 0.
- Matrix Test Audit: dispatch — `test_bmad_output_hygiene_runs_gather_and_prints_its_findings_with_a_warn_leaving_exit_zero`, its `--json` twin and the roster tests; aggregate — `test_doctor_source_tasks_include_bmad_output_hygiene_and_a_matching_pixi_task` and `test_the_real_hygiene_gather_runs_through_the_aggregate_and_reads_pass`; warn only — `test_a_warn_only_hygiene_source_reads_pass_and_leaves_the_exit_code`. Each ran and passed in the runs above.

**Residual risks.**
- The sweep adds about 17-21 s to the repo-scope detectors run (one `git grep` per candidate).
- DW-FU-9-2 stands: an unreadable `_bmad-output/projects` crashes `hygiene.gather`, which `detectors.py` reads as `unknown`, never green.
- Five orphan-file WARNs are now standing output; judging each file belongs to herald, marshal and steward.
- The aggregate's current exit 1 (marshal 79.1 `ledger-direction`) needs marshal's `sprint-ledger-sync`, not this story.
- The regenerated `docs/` stamps read `-dirty` (as the previous ones did); `--check` does not depend on the stamp.
