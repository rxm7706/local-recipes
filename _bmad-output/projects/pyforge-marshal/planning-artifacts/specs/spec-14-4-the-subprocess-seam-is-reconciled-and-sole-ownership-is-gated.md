---
title: 'Story 14.4: The subprocess seam is reconciled and sole ownership is gated'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/planning-artifacts/specs/spec-pyforge-core/SPEC.md']
warnings: ['oversized']
baseline_revision: '5141daad88345935bd955e53c9a211c09c8a7f28'
final_revision: '3b79714bc32eeaef7d686db311240fd66582e170'
---

<intent-contract>

## Intent

**Problem:** Four stations invoke subprocesses with no shared primitive: Marshal has 9 files
consuming its own `ProcessPort`/`PosixProcess` port-adapter pair plus 7 more modules calling
`subprocess` directly around it (the fleet's widest ungated surface); Doctor has a simpler
`cli_bridge.run_cli_json`/`run_git` pair with its own already-enforced sole-site meta-test;
Warden's `engines.py` carries a single, already-annotated "sole seam"; Steward propagates raw
`subprocess.CalledProcessError` deliberately across 3 files, pinned by 11 tests. Nothing prevents
a ninth copy from appearing anywhere.

**Approach:** Move Marshal's `ProcessPort`/`ProcessResult`/`PosixProcess`/`ProcessError` design
(chosen over Doctor's, for its `is_alive`/`spawn_detached` capability and non-raising-on-nonzero-exit
contract, which generalizes better across the fleet's actual usage) verbatim into
`pyforge.core.process`; retire Marshal's own copies and route its gated and previously-ungated call
sites through it (4 of `harness_bmadloop.py`'s call sites stay as a documented sanctioned exception,
needing capabilities -- interactive stdio passthrough, append-mode log -- the guard does not offer);
confirm Doctor/Warden/Steward each already conform and record each exclusion in a new fleet-wide
sole-ownership meta-test.

## Boundaries & Constraints

**Always:**
- `pyforge-core` gains `pyforge/core/process.py`: `ProcessResult` (frozen dataclass:
  returncode/stdout/stderr), `ProcessPort` (Protocol: run/is_alive/spawn_detached), `PosixProcess`
  (concrete adapter), `ProcessError(PyforgeError, Exception)` -- verbatim move of Marshal's
  `ports/process.py` + `adapters/process_posix.py`, preserving the exact exception-translation
  discipline (`FileNotFoundError`/`TimeoutExpired`/`ValueError`-NUL/`OSError` -> `ProcessError`,
  each `raise ... from exc`, so `isinstance(exc.__cause__, subprocess.TimeoutExpired)`-style
  downstream checks keep working). No non-stdlib import (leaf constraint, CAP-1).
- Marshal retires `ports/process.py` + `adapters/process_posix.py` entirely; its 9 already-gated
  production consumers (`core/status.py`, `core/gate.py`, `cli/{gate,land,check,spin,status,deploy}.py`,
  `supervisor/__main__.py`) re-point imports to `pyforge.core.process`, no other change --
  `core/status.py`/`core/gate.py` keep importing ONLY `ProcessResult`, never `PosixProcess`
  (preserves AD-4's `core/**` purity; the existing import-linter contract is unchanged).
- Marshal's 5 real ungated callers (`adapters/vcs_git.py`, `adapters/forge_gh.py`,
  `adapters/notify_file_desktop.py`, `adapters/observer_mux.py` [4 call sites],
  `adapters/harness_bmadloop.py`'s `_run`/`spin`/`stop` only) swap their own `subprocess.run`/`Popen`
  call for `PosixProcess().run(...)`/`.spawn_detached(...)`. None of these five use `check=True`
  today, so none currently raise `CalledProcessError` -- confirmed drop-in; each adapter's own
  existing exception translation (`VcsCommandError`, `ForgeCommandError`, `HarnessError`, etc.)
  now wraps `ProcessError`/a non-zero `ProcessResult.returncode` instead of raw `subprocess`
  exceptions, unchanged externally. `supervisor/__main__.py`/`cli/init.py`'s bare `import subprocess`
  (used only inside `except (..., subprocess.SubprocessError)`, never calling it) stays untouched.
- New `pyforge-core/tests/meta/test_process_sole_ownership.py`, following the `tests/meta/conftest.py`
  (`sibling_station_dirs`/`station_source_files`/`parse_module`) convention from 14.2/14.3,
  generalizes Doctor's own hardened `_subprocess_violations` AST detector
  (`test_cli_bridge_sole_subprocess.py`: `import subprocess`, `subprocess.*` access,
  `os.system`/`os.popen`/spawn/exec family incl. aliasing) to scan every sibling station, EXCLUDING
  `pyforge-doctor`/`pyforge-warden`/`pyforge-steward` (station-level, one documented rationale each)
  and `pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` (file-level, mirroring
  Doctor's own `_EXEMPT_RELATIVE_PATHS` pattern) -- proven non-vacuous via synthetic fixtures
  (positive + negative), matching 14.2/14.3's established convention.
- `harness_bmadloop.py`'s `attach()`/`run_foreground()` (inherited-stdio interactive passthrough --
  `PosixProcess.run()` always captures) and `resume()`'s detached `Popen` (append-mode log --
  `spawn_detached()` hardcodes truncate) keep their own direct `subprocess` calls, each gaining a
  short comment naming the capability gap and citing this story -- the same sanctioned-exception
  latitude CAP-6 grants Steward.
- `pyforge-core/tests/unit/test_process.py` (new) covers the moved primitive in isolation, adapted
  from Marshal's `tests/unit/test_process_posix.py`; every Marshal test file importing
  `ProcessPort`/`ProcessResult`/`PosixProcess`/`ProcessError` (`test_gate.py`, `test_land.py`,
  `test_status.py`, `test_check.py`, `test_spin.py`, `test_deploy.py`, `test_egress.py`, `test_cli.py`,
  `test_supervisor.py`, `test_ad11_write_boundary.py`, `test_ad34_egress_registry_completeness.py`)
  updates its import path only -- no assertion changes, class names/shapes unchanged.
- No new `pyforge-core` run-dependency wiring: Marshal (14.2) already depends on it; Doctor/Warden/
  Steward aren't migrated here. `pixi.toml`/`environment.yaml` stay untouched unless review finds
  otherwise.

**Block If:** none identified -- the design choice, the per-station treatment, and every
`harness_bmadloop.py` call site's fit (or non-fit) were confirmed by direct investigation, not
assumed.

**Never:**
- No change to Doctor's `cli_bridge.py`, `run_git`, or `test_cli_bridge_sole_subprocess.py` --
  CAP-6's success text names only Marshal for mandatory migration; Doctor's design already
  independently meets the bar (single typed exception, argv-list-only, timeout-bound, own working
  sole-site guard) and is excluded from the new guard, exactly like Warden.
- No change to Warden's `engines.py` or Steward's `deploy.py`/`provision.py`/`keys.py` -- both
  explicitly confirmed-conforming / sanctioned-opt-out per the epic's own Technical Decision, not
  "fixed."
- No expansion of `ProcessPort`'s contract (no interactive-passthrough mode, no append-mode
  `spawn_detached` parameter) -- the non-drop-in `harness_bmadloop.py` call sites stay a documented
  exception rather than growing the shared primitive for one caller (CAP-6's own "no primitive earns
  a place on one caller" constraint).
- No change to any station's actual subprocess argv, timeout values, or observable CLI behavior --
  only the call MACHINERY relocates. `run_smoke()` in `harness_bmadloop.py` also stays untouched
  (bounded-timeout + file-redirect fits neither `.run()` nor `.spawn_detached()` cleanly; forcing it
  risks a behavior regression this story does not need to take on).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| vcs_git checkout timeout | `_run(...)` via `PosixProcess().run(...)` exceeds timeout | `ProcessError` raised, `__cause__` is `subprocess.TimeoutExpired` | `vcs_git.py`'s existing `isinstance(exc.__cause__, subprocess.TimeoutExpired)` branch still fires, same partial-state message |
| observer_mux tmux capture-pane, non-zero exit | tmux exits 1 (no such pane) | `ProcessResult(returncode=1, ...)` returned, no exception | `observer_mux.py`'s own returncode check maps to `None`/`False` as before |
| harness spin, detached launch | `spin()` calls `PosixProcess().spawn_detached(...)` | pid returned, log truncated fresh (matches current behavior) | `ProcessError` on launch failure, unchanged message shape |
| harness resume, append-mode log | `resume()`'s own direct `Popen` (unmigrated) | log opened `"ab"`, prior wedged-run content preserved | unchanged from current behavior |
| harness attach, interactive | `attach()`'s own direct `subprocess.run` (unmigrated) | inherits parent stdio, operator can type into the session | unchanged from current behavior |
| Sole-ownership guard, synthetic violation | a fixture file with a raw `subprocess.run(...)` outside pyforge-core and outside excluded stations/files | flagged as a violation | guard is alive, not vacuous |
| Sole-ownership guard, excluded file | `harness_bmadloop.py`'s real `attach`/`resume` calls | NOT flagged (file-level exemption) | guard does not false-positive on this story's own sanctioned exception |
| Sole-ownership guard, excluded stations | Doctor's `cli_bridge.py`, Warden's `engines.py`, Steward's `deploy.py` | NOT flagged (station-level exemption) | guard does not false-positive on already-conforming/sanctioned designs |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/process.py` -- NEW: `ProcessResult`/`ProcessPort`/`PosixProcess`/`ProcessError`, moved verbatim from Marshal.
- `src/shared/packages/pyforge-core/tests/unit/test_process.py` -- NEW: unit tests adapted from Marshal's `test_process_posix.py`.
- `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py` -- NEW: CAP-7 guard, generalizing Doctor's `_subprocess_violations` detector; excludes doctor/warden/steward (station-level) + marshal's `harness_bmadloop.py` (file-level).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/process.py` -- DELETE (content moved).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/process_posix.py` -- DELETE (content moved).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/{core/status.py,core/gate.py,cli/gate.py,cli/land.py,cli/check.py,cli/spin.py,cli/status.py,cli/deploy.py,supervisor/__main__.py}` -- re-point imports to `pyforge.core.process`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py` -- `_run()` calls `PosixProcess().run(...)`; downstream `__cause__` check preserved.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py` -- `_run()` calls `PosixProcess().run(...)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/notify_file_desktop.py` -- its one call site calls `PosixProcess().run(...)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/observer_mux.py` -- its 4 call sites call `PosixProcess().run(...)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` -- `_run()`/`spin()`/`stop()` call `PosixProcess().run(...)`/`.spawn_detached(...)`; `attach()`/`run_foreground()`/`resume()`/`run_smoke()` stay unmigrated, each gains a short comment naming its capability gap.
- `src/shared/packages/pyforge-marshal/tests/unit/{test_process_posix.py,test_gate.py,test_land.py,test_status.py,test_check.py,test_spin.py,test_deploy.py,test_egress.py,test_cli.py,test_supervisor.py}` -- import-path updates only (`test_process_posix.py` retires, superseded by pyforge-core's own).
- `src/shared/packages/pyforge-marshal/tests/meta/{test_ad11_write_boundary.py,test_ad34_egress_registry_completeness.py,test_ad36_projection_mechanism_table.py,test_supervisor_run_path_agreement.py}` -- import-path/comment updates only, no assertion changes.

## Tasks & Acceptance

**Execution:**
- [x] `pyforge-core/src/pyforge/core/process.py` + `tests/unit/test_process.py` -- move `ProcessResult`/`ProcessPort`/`PosixProcess`/`ProcessError` verbatim, in isolation -- establishes the primitive before any station points at it
- [x] `pyforge-core/tests/meta/test_process_sole_ownership.py` -- CAP-7 guard, station+file exclusions, synthetic non-vacuous proof
- [x] Marshal: delete `ports/process.py` + `adapters/process_posix.py`; repoint the 9 already-gated production consumers + all listed test files; `pyforge-marshal-test` green
- [x] Marshal: migrate `vcs_git.py`/`forge_gh.py`/`notify_file_desktop.py`/`observer_mux.py` (5 files, all drop-in) to `PosixProcess().run(...)`; each station's own existing exception translation preserved; relevant unit tests green
- [x] Marshal: migrate `harness_bmadloop.py`'s `_run`/`spin`/`stop` to `pyforge.core.process`; document `attach`/`run_foreground`/`resume`/`run_smoke` as sanctioned exceptions with inline comments; `pyforge-marshal-test` green
- [x] `grep -rn "subprocess" src/shared/packages/pyforge-marshal/src` -- manually confirm remaining hits are only the 4 documented `harness_bmadloop.py` exceptions
- [x] `environment.yaml` -- re-run export and diff; commit only if it reports a change

**Acceptance Criteria:**
- Given the fleet's subprocess call sites, when `pyforge.core.process` lands, then Marshal's
  `ports/process.py`/`adapters/process_posix.py` no longer exist and every former consumer imports
  from `pyforge.core.process` instead, with identical class names/shapes.
- Given Marshal's 5 previously-ungated real callers (vcs_git/forge_gh/notify_file_desktop/
  observer_mux/harness_bmadloop's `_run`+`spin`+`stop`), when they run, then each invokes
  `PosixProcess`, and a grep for `subprocess.run(...capture_output=True...)`/`Popen(...
  start_new_session=True...)` outside pyforge-core and the documented exceptions returns nothing.
- Given the new sole-ownership meta-test, when it scans the fleet, then it fires on a synthetic
  violation and does not fire on Doctor/Warden/Steward's real code or `harness_bmadloop.py`'s 4
  sanctioned call sites.
- Given `vcs_git.py`'s worktree-add timeout-handling branch, when a checkout times out after
  migration, then the same partial-state operator message is produced (the `__cause__` chain is
  preserved through `ProcessError`).
- Given each of Marshal's and pyforge-core's existing test suites, when run after the refactor, then
  all pass with assertion content unchanged (only import paths moved).

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (low 5)
- defer: 2: (medium 2)
- reject: 4: (medium 1, low 3)
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both independently): `PosixProcess.run([])`'s
    empty-argv guard raises `ProcessError` with no `from` clause, so `exc.__cause__` is `None` --
    `vcs_git.py::_run`'s and `forge_gh.py::_run`'s `except ProcessError` translation fell through to
    the generic branch and produced `"cannot launch git: None"`/`"cannot launch gh: None"` (currently
    unreachable, since every real `args` list starts with a literal `"git"`/`"gh"`, but a real gap in
    the new translation logic). Fixed both to fall back to `cause or exc` for the message and the
    `from` chain, so `exc` (which carries the real "cannot launch an empty argv" text) is never lost.
  - `[low]` `[patch]` Edge Case Hunter: the new `test_process_sole_ownership.py`'s file-level
    exemption for `harness_bmadloop.py` is coarser than its 4 named sanctioned call sites -- a fifth,
    unsanctioned `subprocess.*` call added anywhere else in that file would go undetected. Real, but
    already matches Doctor's own `_EXEMPT_RELATIVE_PATHS` precedent (also file-level, not
    line-level) -- added one paragraph to the guard's module docstring explicitly stating this as a
    stated, bounded limitation (matching `test_leaf_constraint.py`'s "Bounded, not aspirational"
    convention) rather than leaving it undisclosed.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (both independently): stale cross-references to
    the now-deleted `ports/process.py`/`adapters/process_posix.py`/`tests/unit/test_process_posix.py`
    remained in `adapters/__init__.py`'s module docstring, `cli/gate.py`/`cli/deploy.py`'s inline
    comments, and 4 test-file docstrings (`test_supervisor_run_path_agreement.py`, `test_gate.py`,
    `test_forge_gh.py`, `test_cli.py` x2). Updated all to point at `pyforge.core.process` /
    `pyforge-core/tests/unit/test_process.py`, verifying each cited test name actually exists there.
  - `[low]` `[patch]` Blind Hunter: test function name
    `test_guard_would_fire_on_dockers_cli_bridge_if_it_were_not_excluded` read as a reference to
    Docker containers rather than the intended possessive of "Doctor" (the station). Renamed to
    `test_guard_would_fire_on_doctors_cli_bridge_if_it_were_not_excluded`.
  - `[low]` `[patch]` Self-caught during this pass's own re-verification (not flagged by either
    reviewer): running `ruff check` on the full diff surfaced 3 `I001` import-order violations in
    `test_cli.py` (this story's own new `from pyforge.core.process import ProcessResult` lines) and
    `SIM102`/`SIM114` in the new `test_process_sole_ownership.py` -- confirmed against the baseline
    revision that these are not pre-existing debt (the many OTHER ruff findings in `deploy.py`/
    `vcs_git.py`/`test_cli.py` the broad scan surfaced ARE pre-existing and were left untouched,
    Surgical Changes). Fixed all five; `ruff check --select I001,SIM102,SIM114` now clean on every
    touched file.
- rejected (4, with reasoning):
  - `[medium]` Blind Hunter's cross-package string-prefix error dispatch concern --
    `harness_bmadloop.py::spin`'s `str(exc).startswith("cannot open log")` classifies a
    `pyforge.core.process.ProcessError` by message text across a package boundary, which would
    silently misclassify if pyforge-core's wording ever changes. Real, but the textbook fix (a
    `ProcessError.kind` attribute) would expand the shared primitive's contract for exactly one
    caller -- explicitly foreclosed by this story's own Never section ("no primitive earns a place
    on one caller"). A regression test already pins the literal message, so drift would fail loudly,
    not silently. Accepted as a bounded tradeoff of the spec's own deliberate "verbatim move, no
    contract expansion" design, not a defect this story's implementation introduced through error.
  - `[low]` Blind Hunter's AST-detector evasion concerns (deep attribute chains, `getattr` dynamic
    dispatch) and Edge Case Hunter's `from subprocess import *` / `from os import *` star-import gap
    -- the same class of "narrow, stated AST-shape" limitation every sole-ownership guard in this
    package already carries (`test_atomic_write_sole_ownership.py`'s name-shaped heuristic,
    `test_verdict_lattice_sole_ownership.py`'s `_RANK`-literal-only match, `test_exception_root_sole_
    ownership.py`'s alias-evasion gap -- all previously reviewed and accepted under the same
    "Bounded, not aspirational" convention in Stories 14.2/14.3). Not a new gap this story
    introduced; re-litigating an already-established, repeatedly-accepted codebase convention.
  - `[low]` Blind Hunter's "exclusion list asserted, not derived" concern (`test_out_of_scope_
    stations_matches_the_documented_six` only checks the hardcoded set equals itself) -- identical in
    shape to Story 14.3's own `_OUT_OF_SCOPE_STATIONS` self-assertion test for the exception-root
    guard, already an accepted pattern in this codebase; a future migration removing a station from
    the set is expected to edit this test in the same change, exactly as DW-FU-14-3 already documents
    for CAP-5's analogous exclusion.
  - `[low]` Blind Hunter's `import subprocess  # noqa: F401` monkeypatch-anchor coupling in
    `notify_file_desktop.py`/`observer_mux.py` (relies on `pyforge.core.process` also doing a plain
    `import subprocess`, so both modules reference the same `sys.modules` object) -- real but
    speculative (bites only if a FUTURE, unrelated `pyforge.core.process` refactor changes its own
    import style), and the actual fix at true scale is a 30+ call-site rewrite across two test files,
    disproportionate to a narrow, already-self-documented (the code carries its own explanatory
    comment) future risk. Not fixed here; the existing comment already discloses the coupling to the
    next reader.

### 2026-08-13 — Review pass (verification-repair follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (low 3)
- defer: 0
- reject: 4: (medium 2, low 2)
- addressed_findings:
  - `[low]` `[patch]` Edge Case Hunter: `harness_bmadloop.py::spin`'s `except ProcessError as exc:
    ... raise HarnessError(...) from cause` branches lacked the `cause or exc` fallback the prior
    review pass already added to `vcs_git.py::_run` and `forge_gh.py::_run` for the identical
    empty-argv-guard gap (`cause` is `None` when `PosixProcess`'s own empty-argv guard raises with
    no `from` clause) -- the prior pass fixed the two adapters it happened to check but missed
    `spin`'s own use of the same pattern. Fixed both of `spin`'s `raise` branches to match; reconciled
    into `spec-pyforge-marshal`/`spec-adaptive-model-tiering`/`spec-horizontal-run-concurrency`'s own
    memlogs (all three govern `harness_bmadloop.py`) and their baselines re-stamped.
  - `[low]` `[patch]` Blind Hunter: this pass's own new `spec-pyforge-core` memlog entry (written to
    close the deterministic-verification gap that triggered this repair) claimed
    `` `ruff check src/shared/packages/pyforge-core`: zero findings `` without having run it at that
    scope -- the actual command reported one `I001` import-order violation in the new
    `tests/unit/test_process.py`. Fixed with `ruff check --fix`; re-verified clean, claim now
    accurate.
  - `[low]` `[patch]` Blind Hunter: the same new memlog entry asserted "Marshal's own 26
    re-pointed/migrated call sites," a figure that does not match any derivable count in the diff
    (spec-pyforge-marshal's own entry itemizes 27 governed paths total, of which a different subset
    is test files). Removed the unverified number; the entry now points to `spec-pyforge-marshal`'s
    own memlog for the itemized detail instead of restating an uncomputed count.
- rejected (4, with reasoning):
  - `[medium]` Blind Hunter's `spin()` string-prefix error-dispatch concern -- identical in substance
    to the prior review pass's own rejected finding on the same line (`str(exc).startswith("cannot
    open log")` classifying by message text across the `pyforge.core.process` package boundary).
    Already accepted as a bounded tradeoff of the spec's own "no primitive earns a place on one
    caller" constraint; re-litigating an already-triaged finding, not a new one.
  - `[medium]` Blind Hunter's "only 2 of 6 station exclusions have a synthetic would-fire-if-
    not-excluded proof" concern (Doctor and Herald have one, Warden/Steward/Mason/Scribe do not) --
    real asymmetry, but the guard's non-exhaustive nature is already disclosed in its own module
    docstring per the prior pass's `[patch]` fix, matching this codebase's established "Bounded, not
    aspirational" convention for every sole-ownership meta-test in this package. Extending proof
    coverage to 4 more stations is a coverage expansion, not a trivial patch, and no station's real
    exclusion was shown to be wrongly granted.
  - `[low]` Edge Case Hunter's AST-guard evasion findings (`from subprocess import *`/`from os
    import *` star-imports, plain-assignment aliasing, `getattr`/dynamic-dispatch invocation) --
    identical in class to the prior review pass's own rejected finding on the same guard (deep
    attribute chains, `getattr` dynamic dispatch, star-imports); re-litigating an already-established,
    repeatedly-accepted "narrow, stated AST-shape" limitation shared by every sole-ownership guard in
    this package.
  - `[low]` Blind Hunter's observation that the `DW-FU-14-4`/`DW-FU-14-4-2` ids cited in this story's
    memlogs exist only in the gitignored Tier-3 `implementation-artifacts/deferred-work.md`, not the
    tracked `planning-artifacts/deferred-work-ledger.md` -- this is the standing, intentional shape of
    every DW-FU citation across this codebase's memlogs (Tier-3 is where deferred-work entries are
    minted; promotion to the tracked ledger is a separate, later act, not a defect of this citation).

## Design Notes

**Why Marshal's design over Doctor's.** `ProcessPort` offers `is_alive`/`spawn_detached` (needed by
Marshal's own supervisor, absent from Doctor's two-function API) and its `.run()` never raises on a
non-zero exit -- the same non-raising, typed-classification philosophy Warden's `engines.py`
independently already uses (returns a classified `ErrorRecord`, never raises on a failing scan),
whereas Doctor's `cli_bridge.run_cli_json` raises on ANY non-zero exit, a narrower convenience
fitting only its own JSON-fetch use case. Choosing the design already living in the station with the
widest migration surface also makes that migration a pure relocation, not a re-implementation --
lower risk, matching Story 14.2's atomic-write precedent.

**Why Doctor/Warden/Steward are untouched.** CAP-6's own success text names only Marshal for
mandatory migration ("Marshal's own 7 importing modules... route through it"), grants Steward an
explicit either/or latitude ("folded in or recorded as a sanctioned, tested opt-out"), and states
Warden is "confirmed conforming... not fixed." Doctor is the losing design candidate but isn't named
for migration; its own already-working, already-tested sole-site guard continues doing its job
untouched. All three get a documented, named exclusion in the new pyforge-core guard rather than
silent invisibility -- consistent with CAP-5's `_OUT_OF_SCOPE_STATIONS` precedent (Story 14.3).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Confirm `harness_bmadloop.py`'s 4 unmigrated call sites each carry an inline comment citing this story's capability-gap rationale.

## Auto Run Result

Status: done

**Summary.** This session was a repair-only resume: the previous landing (commit `901f211f5a`)
already implemented every task and passed its own review pass, but `python
scripts/spec_surface_reconcile.py` (bmad-loop's own S-13.7 verify-step gate) failed post-landing
because `spec-pyforge-core`'s own memlog was never updated to name the 3 new files this story
added under its surface (`process.py`, `test_process.py`, `test_process_sole_ownership.py`) --
`spec-pyforge-marshal`'s own memlog entry for this story said that reconciliation was "handled
independently in its own memlog," but the entry was never actually written. No code or intent
change was needed to fix this; the repair reconciled the governance ledger by name and re-stamped
the affected baseline.

A fresh step-04 review pass (Blind Hunter + Edge Case Hunter) was then run over the full diff
since `baseline_revision`, per the workflow, and surfaced one genuine, previously-missed code bug
plus two factual inaccuracies in the new memlog prose the repair itself introduced; all three were
fixed in this same pass (see the new Review Triage Log entry above).

**Files changed this session:**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` --
  added the missing Story 14.4 reconciliation entry (CAP-6/CAP-7, 3 new files), plus a follow-up
  entry for the ruff-fix hash change.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`,
  `spec-adaptive-model-tiering/.memlog.md`, `spec-horizontal-run-concurrency/.memlog.md` -- each
  gained a follow-up entry reconciling the `harness_bmadloop.py` hash change from the `spin()` fix
  below (all three govern that file).
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to exactly the 4 specs above.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` --
  `spin()`'s two `except ProcessError` branches gained the `cause or exc` fallback
  `vcs_git.py::_run`/`forge_gh.py::_run` already carry for the identical empty-argv-guard gap
  (`__cause__` is `None` when `PosixProcess`'s own guard raises with no `from` clause); the prior
  review pass fixed the two adapters it checked but missed `spin`'s own use of the same pattern.
- `src/shared/packages/pyforge-core/tests/unit/test_process.py` -- `ruff check --fix` applied
  (import-order only, no assertion change).

**Review findings breakdown (this pass):** 3 patched (all low severity: the `spin()` fix, and two
factual corrections to this pass's own new memlog prose), 0 deferred, 4 rejected (2 medium, 2 low
-- all either duplicates of findings the story's original review pass already triaged and rejected
with recorded reasoning, or the guard's already-disclosed "Bounded, not aspirational" limitation).

**Follow-up review recommendation:** false. The fixes are narrow (one mechanical adapter-pattern
fix mirroring existing code in the same file, two prose corrections in a governance ledger) and
low-consequence; no new behavior, API, or security surface was touched.

**Verification performed (all green, re-run after every fix in this session):**
- `python scripts/spec_surface_reconcile.py` -- 0 findings (was 3 gating findings at session start)
- `pixi run --frozen -e pyforge-core pyforge-core-test` -- 1051 passed
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3552 passed, 9 deselected
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- 845 passed, 1 skipped
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- 1937 passed, 11 deselected
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 602 passed
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-core/src/pyforge/core/process.py`
  -- zero findings; whole-package `ruff check src/shared/packages/pyforge-core` also now zero
  findings (was 1 before this session's fix)
- `grep -rn "subprocess" src/shared/packages/pyforge-marshal/src` -- only the 4 documented
  `harness_bmadloop.py` sanctioned sites plus pre-existing except-clause references remain
- `pixi project export conda-environment -e build` vs tracked `environment.yaml` -- no diff,
  nothing to commit there
- `ruff check` on the modified `harness_bmadloop.py` -- 6 pre-existing findings, confirmed
  byte-identical (pre-existing, at shifted line numbers) against the pre-edit revision; none
  introduced by this session's fix

**Residual risks:** none new. The pre-existing, already-disclosed guard limitations (AST-shape
evasion, asymmetric per-station proof depth) and the `DW-FU-14-4`/`DW-FU-14-4-2` Tier-3-only
citations are unchanged carry-overs from the original landing, not introduced or worsened by this
repair.

