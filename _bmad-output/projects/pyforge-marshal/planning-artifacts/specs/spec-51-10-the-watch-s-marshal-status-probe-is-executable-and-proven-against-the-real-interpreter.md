---
title: '51.10: The watch''s marshal-status probe is executable and proven against the real interpreter'
type: 'fix'
created: '2026-09-20'
status: 'done'
baseline_revision: '00e52b3d37a064c94e28ab06ada03cc1fa60d4fb'
final_revision: '09b45a2a130fe98b2b9a71d065098b7f1ea1cdda'
review_loop_iteration: 1
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** at 2026-09-20 00:38Z `marshal watch --fleet` reported all eight stations idle while three dispatch sessions (doctor 26.1, steward 61.3, marshal 51.7) were live. Story 51.6 wired dispatch-run detection into `cli/watch.py::_gather_station`, but the `marshal_home` probe it reads shells out to `python -m pyforge.marshal status --project <slug> --format json`; `pyforge/marshal/__main__.py` does not exist (the console script is `pyforge.marshal.cli.main:main`), so every call raises `ProcessError`, the probe degrades to `None`, and the detection never fires. `test_default_ports_marshal_home_reads_homes_zero` asserted that exact argv against a fake — the suite pinned the bug.

**Approach:** the probe names the executable module through one module-level constant (`pyforge.marshal.cli.main`); the fake-probe tests assert the argv against that constant, never a literal; a regression test executes `[sys.executable, "-m", <constant>, "--help"]` through the `pyforge.core` process primitive and asserts exit 0, so a module rename can never silently kill the probe again.

## Boundaries & Constraints

**Always:**
- The probe stays advisory: `ProcessError` or non-JSON output → `None`; the existing degradation tests are unchanged
- One constant, one call site; the regression test reads the constant the probe uses — a divergence between the two is impossible by construction
- `pyforge-marshal-test` green; no second subprocess implementation (spec-pyforge-core CAP-7)

**Never:**
- Do not mint `pyforge/marshal/__main__.py` to make the old name work — the fix is the name, not a shim
- Do not replace the probe with an in-process import of `cli/status.py` — out of scope; the probe boundary (a subprocess reading the CLI's own JSON) is what the fake-port tests are built on
- Do not touch `_gather_station` (Story 51.6's logic is correct; its input was `None`)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| live fleet 2026-09-20 00:38Z | three stations with a live dispatch run | `marshal watch --fleet` names each by `dispatch_run_id` | n/a |
| module rename | the constant names a module the interpreter cannot execute | regression test fails with the interpreter's own "No module named …" | n/a |
| probe failure | `marshal status` exits non-zero or prints non-JSON | `marshal_home` → `None`, station reads from its bmad-loop rows only | advisory, never raised |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-257`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py` (`_default_ports.marshal_home`, the new `_MARSHAL_STATUS_MODULE` constant), `src/shared/packages/pyforge-marshal/tests/unit/test_watch.py` (argv assertions read the constant; new `test_marshal_status_module_is_executable_by_this_interpreter`).
Ledger key: `51-10-the-watch-s-marshal-status-probe-is-executable-and-proven-against-the-real-interpreter`.
Minted 2026-09-20 from `epics.md`; hand-driven in the mint's own PR (operator ruling 2026-09-20 00:40Z).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- `pixi run --frozen -e pyforge-guild marshal watch --fleet` on a fleet with a live dispatch run names that run's `dispatch_run_id`; the same command before the fix reads the station idle.

## Review Triage Log

### 2026-09-20 — hand-driven pass (operator ruling 00:40Z)
  - `[high]` `[patch]` `_default_ports.marshal_home` named `pyforge.marshal` (no `__main__`) — every call raised `ProcessError`; verified by running the argv against the real interpreter (`No module named pyforge.marshal.__main__`). Fixed: one constant `_MARSHAL_STATUS_MODULE = "pyforge.marshal.cli.main"`.
  - `[high]` `[patch]` `test_default_ports_marshal_home_reads_homes_zero` and `test_run_watch_uses_the_injected_process_for_default_ports` asserted the wrong literal against a fake that accepts any key — the suite pinned the bug. Fixed: both read the constant; `_RecordingProcess` responses are keyed by the constant.
  - `[medium]` `[patch]` no test executed the module name for real. Added `test_marshal_status_module_is_executable_by_this_interpreter` (runs `--help` through `PosixProcess`, asserts exit 0 and that the constant is not the bare package).
  - `[low]` `[reject]` replace the subprocess probe with an in-process `cli/status.py` call — out of scope (the fake-port tests are built on the subprocess boundary); recorded as a Never in this spec.
  - `[medium]` `[intent_gap → resolved as Story 51.12]` with the probe fixed, the marshal and steward clones still returned `homes: []` — a second mechanism (`run_status`'s loop-worktree-only fleet sweep), minted and fixed as 51.12 in the same PR rather than widened here.

## Auto Run Result

**Status:** done
**Summary:** `cli/watch.py` gains `_MARSHAL_STATUS_MODULE`; the probe uses it; `test_watch.py` reads it and executes it against the real interpreter. Live proof from the main checkout (doctor run `pyforge-doctor-20260919T233255320Z-8f2b958e` present): before the fix `marshal watch --fleet` printed eight `None` rows; with the fix each station row carries its latest dispatch run id and completion state. The other two live runs (marshal 51.7, steward 61.3) need Story 51.12 too — each checkout's binary reports that checkout's Tier-3 (`repo_root()` is package-relative by design), and those clones have no loop homes.
**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` 8278 passed, 1 skipped; `pixi run --frozen -e pyforge-ci pyforge-deps-test` 130 passed, 3 skipped; the new regression test fails on the old name (`No module named pyforge.marshal.__main__`) and passes on the new one.
**Files changed:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_watch.py`.
**Residual risks:** none from this change; the `finished`/`stopped` state shown for a run that halted with an uncommitted blocked spec is Story 51.11's (CAP-258).
**Follow-up review recommendation:** false
