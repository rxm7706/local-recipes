---
title: '82.2: Marshal land keeps a live run''s branch and home while its engine is alive, even when its supervisor is dead'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: 'cc9d6a78188a27c7734d2872c1721e5d212ad57b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `core/status.py::is_run_live` (`:1255-1296`) is the one predicate `cli/land.py` checks (`:936`) before it
honours `landing_branch_retirement` and deletes a station branch. Its last line is
`return not facts.finished and facts.supervisor_alive is True`: it reads only the supervisor sidecar's pid. Story 5.8
added `FleetHomeFacts.engine_alive` (`ProcessPort.is_alive(launch_pid)`, gathered at `:849-852`) and `derive_home_state`
already lets it soften a dead sidecar (`:784`), but `is_run_live` never reads it. So a dead sidecar behind a live harness
(the 2026-08-11 incident Story 5.8 fixed for `status`) reads "not live" here, and `marshal land` retires a branch a running
harness is still using (DW-5-8-1, DW-FU-4-11). Separately, `_resync_home_branch` (`cli/land.py:1570`, called at `:533`,
`:616` and `:1060`) fetches and fast-forwards the loop home's checked-out branch from outside the run with no lock and no
liveness check: a live run's untouched tracked files can be rewritten on disk mid-turn (DW-FU-4-12). Re-verified at HEAD
a7cdb91fe4.

**Approach:**

- `is_run_live` also returns live when the run is unfinished and `engine_alive is True`, whatever `supervisor_alive`
  reads. Its existing conservative arms (`journal_unreadable`, `run_state_retired`) are unchanged.
- `run_land` gathers the home's facts once and hands `_resync_home_branch` the liveness verdict; while the run is live the
  resync neither fetches nor fast-forwards and reports one `MRS-LAND-009` WARN naming the live run (the code's existing
  "resync did not happen" signal, so no new code).
- All three resync call sites take the same verdict.

Ledger key: `82-2-marshal-land-keeps-a-live-run-s-branch-and-home-while-its-engine-is-alive-even-when-its-supervisor-is-dead`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-9 (the last mile lands itself; branch retirement and resync), with Story 4.11 (FR-172),
  Story 5.8 (FR-181; AD-5) and Story 4.12 (FR-173). A defect of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given facts with `has_run`, not `finished`, `supervisor_alive is False` and `engine_alive is True` When `is_run_live` runs Then it returns `True`
- Given the same home When `marshal land` runs with `landing_branch_retirement` true Then branch deletion is downgraded with `MRS-LAND-008` and the branch survives
- Given a live run in the home When `marshal land` reaches any of its three resync exits Then no fetch or fast-forward runs against the home and one `MRS-LAND-009` WARN names the live run
- Given a finished run, or one whose supervisor and engine are both confirmed dead When `marshal land` runs Then retirement and resync behave exactly as today
- Given the `engine_alive` term removed from `is_run_live` When the new test runs Then it fails (mutation)
- Given the liveness check removed from the resync When the new live-run resync test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** `is_run_live` stays pure and reads `FleetHomeFacts` directly, never `derive_home_state`'s state string. A fact
that cannot be proven stays refused, never defaulted to "safe to delete". Close DW-5-8-1, DW-FU-4-11 and DW-FU-4-12 in
`deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this story).

**Never:** Do not change what `marshal status` displays for a home. Do not add a lock that can block a live run's own git
operations. Do not write back the on-disk `landing_branch_retirement` or `landing_resync` policy values.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` -- `is_run_live` (`:1255`): last line reads `supervisor_alive` only; `FleetHomeFacts.engine_alive` (`:849-852`, `:888`) is already gathered, never `None` once the journal is readable.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` -- `run_land`: retirement gate (`:921-952`) gathers `_gather_home_facts` only when `delete_branch and not retire_live_branch`; three `_resync_home_branch` calls (`:533`, `:616`, `:1060`); the function (`:1570`) returns `None` early when resync is off or the strategy is not `merge`, then warns `MRS-LAND-009` through its local `_warn`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- `:875` calls `_resync_home_branch` positionally on the primary checkout, not a loop home: the new parameter must default to "not live" so this caller is untouched.
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` -- `TestIsRunLive` (`:843`): the pure matrix; `FleetHomeFacts.engine_alive` defaults `None`, so the existing rows keep their verdicts.
- `src/shared/packages/pyforge-marshal/tests/unit/test_land.py` -- liveness fakes (`_FakeHarness`, `_FakeProcess`, `_land_outcome_line`, `_land_supervisor_attach_line`, `_live_snapshot`, `:1086-1210`) and the resync tests (`:756-1050`) are the reuse points. Two tests pass explosive fakes to prove the retirement gate never gathers (`:1429`, `:1475`); resync now also gathers, so each sets `landing_resync = false` to keep proving the retirement gate alone.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-5-8-1 (`:1552`), DW-FU-4-11 (`:4855`), DW-FU-4-12 (`:4869`): close each (`status: closed`, a `resolved:` line naming this story).

## Tasks & Acceptance

**Execution:**
- `core/status.py` -- `is_run_live` returns live when the run is unfinished and `supervisor_alive is True` or `engine_alive is True`; docstring names the engine term -- closes DW-5-8-1 / DW-FU-4-11.
- `cli/land.py` -- `run_land` gathers the home's facts once through one lazy, memoised `home_run_live()` shared by the retirement gate and the resync; `_resync_home_branch` gains keyword-only `run_live: bool = False` and, after its existing early return, warns one `MRS-LAND-009` naming the live run and returns `False` before any `resolve_ref`/`fetch`/`fast_forward`; all three call sites pass the same verdict -- closes DW-FU-4-12.
- `tests/unit/test_status.py` -- `TestIsRunLive`: dead supervisor plus live engine is live; finished with live engine is not; both dead is not.
- `tests/unit/test_land.py` -- live-engine/dead-supervisor retirement refusal (`MRS-LAND-008`, branch kept); live run skips resync at the no-op, already-landed and full-merge exits (no `fetch`/`fast_forward`, one `MRS-LAND-009` naming the run, `home_current` false); dead and finished runs resync as today; the two explosive-fake tests set `landing_resync = false`.
- `deferred-work-ledger.md` -- close DW-5-8-1, DW-FU-4-11, DW-FU-4-12.

**Acceptance Criteria:**
- Given the spec's six Given/When/Then rows above, when the station suite runs, then each passes and each mutation row (drop the `engine_alive` term; drop the resync liveness check) fails its new test.

## Spec Change Log

## Binding

Parent: Stories 4.11, 4.12 and 5.8, `spec-pyforge-marshal` CAP-9; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-2-marshal-land-keeps-a-live-run-s-branch-and-home-while-its-engine-is-alive-even-when-its-supervisor-is-dead`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-5-8-1, DW-FU-4-11, DW-FU-4-12.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 25 findings — high 0, medium 6, low 8, false 11, maybe-false 0
- findings:
  - `[medium]` `[patch]` (Blind Hunter) a retired run or unreadable journal now skips the home resync, and the `MRS-LAND-009` WARN says "still live" for them — verified: `is_run_live` returns `True` for `run_state_retired`/`journal_unreadable`, so the resync inherits those arms; the contract hands the resync that predicate's own verdict, so the skip is kept, but the wording was false for them. Patched: the WARN now reads "live, or its state could not be proven finished", the `run_live` docstring names the conservative arms, and `test_unprovable_run_state_skips_the_home_resync_with_an_honest_warn` pins both arms at all three exits.
  - `[low]` `[reject]` (Blind Hunter) the pre-merge verdict is reused for the post-merge resync — the contract says `run_land` gathers the home's facts once, and re-gathering contradicts it; the retirement window is already documented as intentionally open in `run_land`.
  - `[false]` `[reject]` (Blind Hunter) the liveness gather on the resync path has no error handling — `PosixProcess.is_alive` never raises (`pyforge-core/src/pyforge/core/process.py:85`), `fs.read_text` is guarded by `FsError`, `run_status_snapshot` has its widened guard, `_latest_run_dir`/`_discover_harness_run_id_by_filesystem` guard `OSError`; the same gather already ran unguarded at the retirement gate.
  - `[low]` `[reject]` (Blind Hunter) `resync_home()` repeats the `resync_enabled and merge_strategy == "merge"` condition — a maintenance nit; the fix changes the seam's signature for no behavioural gain.
  - `[low]` `[reject]` (Blind Hunter) no operator override for the resync skip, and a recycled engine pid reads live — `--retire-live-branch` is retirement-only by design and pinned by test; a recycled supervisor pid already read live the same way; an override would add flag semantics the intent does not ask for.
  - `[low]` `[patch]` (Blind Hunter) `MRS-LAND-009` now has a second meaning and its registry comments say it names only failures — verified in `core/findings.py` and `core/verdict.py`. Patched: both comments now record the deliberate skip (comment-only; no new code, no envelope field, as the contract says).
  - `[false]` `[reject]` (Blind Hunter) the ledger rows are closed before the story lands — the ledger edit ships in the same diff as the code, which is how the contract's "when the story lands" is met; a loopback reverts with the branch.
  - `[false]` `[reject]` (Blind Hunter) uneven surface-reconcile entries and no visible stamp — `scripts/spec_surface_reconcile.py` and `spec-surface-check` both exit 0; the task forbids `--write-baseline`; `spec-pyforge-core` governs `land.py`/`status.py` but not the test files.
  - `[false]` `[reject]` (Blind Hunter) the new `status.py` tests have gaps and near-duplicates — the between-stories case is cheap and harmless; the retired/unreadable pairing is covered at the `run_land` surface by the patched test; no named harm.
  - `[false]` `[reject]` (Blind Hunter) the memo is a mutable `list[bool]` closure — a style preference with no named harm.
  - `[medium]` `[patch]` (Edge Case Hunter) the conservative arms suppress the resync indefinitely — same root cause and same patch as the first row; the skip is a deliberate consequence of reusing `is_run_live`, recorded under Residual risks.
  - `[low]` `[reject]` (Edge Case Hunter) the memoised pre-merge verdict reaches the post-merge resync — same as the second row.
  - `[low]` `[reject]` (Edge Case Hunter) a false-live engine has no resync override — same as the fifth row.
  - `[false]` `[reject]` (Edge Case Hunter) the gather is unguarded on the post-merge path — same refutation as the third row; the reviewer rated it low-confidence.
  - `[medium]` `[patch]` (Edge Case Hunter, claim) the WARN says "still live" where no live run was proven — same as the first row.
  - `[low]` `[reject]` (Edge Case Hunter, claim) the full-merge exit reuses the gate's verdict — same as the second row.
  - `[medium]` `[patch]` (Edge Case Hunter, claim) the conservative arms are "unchanged" yet newly suppress the resync — same as the first row.
  - `[medium]` `[patch]` (Verification Gap) no `run_land` test for a retired run or an unreadable journal — added (first row).
  - `[medium]` `[patch]` (Verification Gap, other) the WARN wording misleads for retired homes — fixed (first row).
  - `[low]` `[reject]` (Verification Gap, other) the memoised verdict can be stale at the full-merge exit — same as the second row.
  - `[false]` `[reject]` (Intent Alignment) the conservative arms now also skip the resync — same as the first row, which carries the verdict.
  - `[false]` `[reject]` (Intent Alignment) the verdict's timing depends on policy (gate versus first resync call) — by design: one lazy gather, never two.
  - `[false]` `[reject]` (Intent Alignment) a project with retirement off but resync on now pays the gather — by design and pinned: `test_resync_off_or_non_merge_strategy_never_gathers_liveness` proves no gather when the resync would not act.
  - `[false]` `[reject]` (Intent Alignment) the feed reconcile (`_run_resync_if_enabled`) is not gated on liveness — it runs at the repo root and never writes under a loop home (`test_reconcile_feed_resync_runs_at_root_and_never_writes_under_a_loop_home`).
  - `[false]` `[reject]` (Intent Alignment) the contract cites `engine_alive` as gathered at `core/status.py:849-852`, but the probe is in `cli/status.py` — a citation inaccuracy in the contract; the docstring there is the field's home and no code is wrong.

## Auto Run Result

Status: done

**Summary.** `marshal land` keeps a live run's branch and home while its engine is alive, even when its supervisor sidecar is dead. `is_run_live` now also returns live for an unfinished run whose `engine_alive is True`. `run_land` gathers the home's facts once, lazily, and hands that verdict to the retirement gate and to all three `_resync_home_branch` exits. While the run is live, or could not be proven finished, the resync does no `resolve_ref`, `fetch` or `fast_forward` and reports one `MRS-LAND-009` WARN. DW-5-8-1, DW-FU-4-11 and DW-FU-4-12 are closed in the ledger.

**Files changed.**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` — `is_run_live` counts a confirmed-alive engine.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` — shared lazy verdict (`home_run_live`, `resync_home`); `_resync_home_branch(run_live=...)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` — `MRS-LAND-009` comments record the deliberate skip.
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` — five `TestIsRunLive` cases.
- `src/shared/packages/pyforge-marshal/tests/unit/test_land.py` — retirement refusal, skip at every exit, dead/finished as before, retired and unreadable arms, override, no-gather, seam test; two explosive-fake tests set `landing_resync = false`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` — the three rows closed.
- Five `.memlog.md` files (`spec-pyforge-marshal`, `spec-pyforge-core`, `spec-marshal-drain-self-resolution`, `spec-landing-evidence-grammar`, `spec-quick-dev-reconciliation`) — surface reconcile entries.

**Review.** 25 findings across four layers: patches applied 2 (one `medium` group covering 6 rows, one `low`), deferred 0, rejected 11 `false` and 7 `low`, each with its reason in the log above.

**Follow-up review recommended:** `false` — one medium and one low were patched; no high.

**Verification.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 9817 passed, 1 skipped; `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped; `lint-types`, `spec_surface_reconcile.py`, `spec-surface-check` and `deferred-work-check` all exit 0. Both mutation rows were re-run by hand: removing the `engine_alive` term fails `TestIsRunLive::test_dead_supervisor_with_live_engine_is_live`; disabling the resync's `run_live` check fails 8 tests in `test_land.py`.

**Residual risks.**
- A retired run (its state cleaned up) or an unreadable journal skips the home resync on every `land`, because the resync reuses `is_run_live`'s verdict including its conservative arms. That is the contract's reading ("hands the liveness verdict"), and it never rewrites a tree a run may still use, but it is a change from today for retired homes, and the acceptance row "finished run, behaves as today" does not name them. If the operator wants retired homes to keep resyncing, the resync needs a narrower, confirmed-live predicate (a new pure function beside `is_run_live`); that is a design choice for the operator, not made here.
- The verdict is gathered before `merge_pr` when retirement is on and reused for the post-merge resync, a window the file already documents as open for retirement.
- `--retire-live-branch` overrides retirement only; there is no override for the resync skip.
