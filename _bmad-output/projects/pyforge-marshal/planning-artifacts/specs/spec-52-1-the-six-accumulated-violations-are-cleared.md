---
title: '52.1: The six accumulated violations are cleared'
type: 'fix'
created: '2026-09-19'
status: 'done'
baseline_revision: 'cefe85df1d6a6fdd7546c804b88f9ad42d5fab36'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pixi run --frozen -e pyforge-core pyforge-core-test` is red on `main` (6 failed / 1855 passed, 2026-09-19): three exception roots are not parented to the core `PyforgeError` (marshal `adapters/oidc_pkce.py::PkceLoginError`, `cli/watch.py::LoopCliError` + `ProbeError`, warden `tea_advisory.py::TeaRosterMissingError`) and three modules carry a second subprocess implementation (marshal `cli/login.py::_mint_local_token`, `cli/refresh.py::_sync_status_step`, testing-kit `branch_diff_guard.py`). They accumulated between 09-07 and 09-15 because no CI lane runs the suite (Story 52.2 closes that); the gate must be born green.

**Approach:** Re-parent the four classes to `PyforgeError` as first base (the `class X(PyforgeError, RuntimeError)` shape marshal's own `ports/forge.py::ForgeCommandError` uses), widening no `except`; route marshal's two call sites through `pyforge.core.process.PosixProcess().run` — `login.py` drops its custom `env` by moving the `PYTHONPATH` need into the child's own `sys.path` (the two `setdefault` env vars are already set inside the script) — and record testing-kit's `branch_diff_guard.py` as a sanctioned, tested opt-out in the meta-test's own `_EXEMPT_RELATIVE_PATHS` mechanism, because that package is a declared stdlib leaf (`dependencies = []`, guarded by `test_dependency_completeness`) and cannot import `pyforge.core` without ceasing to be one.

## Boundaries & Constraints

**Always:**
- `pyforge-core-test` → 0 failed; `pyforge-marshal-test`, `pyforge-warden-test`, `pyforge-testing-kit-test` and `pyforge-deps-test` stay green.
- Every re-parented class keeps every existing base (`RuntimeError` / `Exception`) so `except RuntimeError` / `except Exception` sites behave identically; each gains an `issubclass(X, PyforgeError)` + original-base pin test (the `test_seed_error_is_a_pyforge_error_and_an_exception` pattern). Verified during planning: no `except PyforgeError` clause in marshal (`cli/dispatch.py:452` — skill-deploy file ops) or warden (`config.py`, `sbom.py`) lies on a path that raises any of the four, so nothing widens.
- `_mint_local_token` and `_sync_status_step` keep their observable contracts: non-zero exit → `RuntimeError(message)` / `MRS-REFRESH-008` finding exactly as today; a launch failure (`ProcessError`) maps to the same outcome the raw `OSError`/`TimeoutExpired` did.
- The testing-kit opt-out carries an inline comment in `_EXEMPT_RELATIVE_PATHS` naming the capability gap (stdlib leaf by declaration) — the same shape as the five existing file-level exemptions.
- Tests fake `PosixProcess.run` via `monkeypatch.setattr(PosixProcess, "run", ...)` (the `test_harness_bmadloop_engine_liveness.py` convention), never `subprocess`.

**Never:**
- Do not touch `cli/watch.py::_gather_station` or anything below the two class definitions — Story 51.6 owns that function.
- Do not add `env=` to `ProcessPort`/`PosixProcess` (its env-inheritance is documented as by-design in the meta-test; that is CAP-6 surface, not this story's).
- Do not add a dependency to `pyforge-testing-kit`, do not enumerate test files anywhere, do not widen any station-level exclusion, and do not touch `spec_difficulty.py`/`dispatch_harness_done.py` or any file outside the six named plus their tests and the one meta-test exemption table.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| mint succeeds | `PosixProcess.run` returns `returncode 0`, stdout `tok\n` | `_mint_local_token` returns `"tok"` | No error expected |
| mint exits non-zero | `returncode 1`, stderr `boom` | `RuntimeError("boom")` | as today |
| mint cannot launch | `PosixProcess.run` raises `ProcessError` | `RuntimeError` whose message names the launch failure | no raw `OSError` escapes |
| sync-status launch fails | `PosixProcess.run` raises `ProcessError` | `RefreshStep(..., "failed", ...)` + `MRS-REFRESH-008` finding | as today (was `OSError`/`TimeoutExpired`) |
| sync-status non-zero | `returncode 1`, stderr `boom` | `failed` + `MRS-REFRESH-008` | as today |
| re-parented class raised | `raise ProbeError("git", "x")` | caught by `except ProbeError`, `except RuntimeError`, `except PyforgeError` | no behaviour change for existing sites |
| sole-ownership scan | the six files as changed | `test_exception_root_sole_ownership` / `test_no_second_subprocess_implementation` pass; `branch_diff_guard.py` skipped by the exemption table | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/errors.py:23` -- `PyforgeError(Exception)`, the root to re-parent to.
- `src/shared/packages/pyforge-core/src/pyforge/core/process.py:65-136` -- `ProcessPort.run(argv, *, cwd, timeout_s=None) -> ProcessResult(returncode, stdout, stderr)`; raises `ProcessError` only on launch/timeout; never for non-zero exit; no `env=` (by design). `PosixProcess` is the adapter.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/forge.py:105` -- `class ForgeCommandError(PyforgeError, Exception)`: the re-parent shape.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py:24` -- `class PkceLoginError(Exception)`; caught at `cli/login.py:123` only.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py:45,:54` -- `LoopCliError(RuntimeError)`, `ProbeError(RuntimeError)`; caught at `:708,:718,:738,:795` by exact class. `PosixProcess`/`ProcessError` already imported at `:24`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/login.py:63-90` -- `_mint_local_token`: `subprocess.run([sys.executable, "-c", script, persona], cwd=repo_root, env=env, ...)`; `env` only adds `PYTHONPATH=<repo_root/_PLATFORM_SRC>` + two `setdefault`s the script already performs itself. Tests stub `_mint_local_token` (`tests/unit/test_login.py:26,:53`), so no test stubs `subprocess` here.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/refresh.py:190-216` -- `_sync_status_step`: `subprocess.run(argv, cwd=git_repo_root, capture_output=True, text=True, timeout=_SYNC_STATUS_TIMEOUT_S)`; `except (OSError, subprocess.TimeoutExpired)` → `MRS-REFRESH-008`. Tests at `tests/unit/test_refresh.py:297-360` stub `refresh_mod.subprocess.run` (four tests) — must move to `PosixProcess.run`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py:91` -- `class TeaRosterMissingError(RuntimeError)`; caught by exact class at `:365` and `cli.py:1442`. Warden already imports `PyforgeError` in `actuator.py`, `config.py`, `waiver.py` (dependency edge exists). Its `subprocess.run` at `:153` is NOT flagged — warden is station-excluded from the subprocess guard (`engines.py` is its sanctioned seam).
- `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py` -- eight `subprocess.run`/`check_output` git calls; package `pyproject.toml:12-16` declares `dependencies = []` ("stdlib leaf. Never a station runtime dependency"), enforced by `tests/packaging/test_dependency_completeness.py`.
- `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py:150-158` -- `_EXEMPT_RELATIVE_PATHS` (five file-level exemptions, each commented with its capability gap) — the sanctioned opt-out mechanism; `:303` pins `_OUT_OF_SCOPE_STATIONS` (unchanged).
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_engine_liveness.py:46` -- `monkeypatch.setattr(PosixProcess, "run", _fake_run)`: the fake convention.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_errors.py:51-53` -- the `issubclass` pin pattern for re-parented roots.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py` -- `class PkceLoginError(PyforgeError, Exception)` + import -- CAP-5.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py` -- `LoopCliError(PyforgeError, RuntimeError)`, `ProbeError(PyforgeError, RuntimeError)` + import; nothing else in the file -- CAP-5, 51.6 boundary.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py` -- `TeaRosterMissingError(PyforgeError, RuntimeError)` + import -- CAP-5.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/login.py` -- drop `import subprocess`/`env`; script prepends `sys.path.insert(0, <platform src>)`; `PosixProcess().run(...)`; `except ProcessError` → `RuntimeError` -- CAP-6.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/refresh.py` -- drop `import subprocess`; `PosixProcess().run(argv, cwd=git_repo_root, timeout_s=_SYNC_STATUS_TIMEOUT_S)`; `except ProcessError` -- CAP-6.
- `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py` -- add `branch_diff_guard.py` to `_EXEMPT_RELATIVE_PATHS` with the stdlib-leaf comment; extend the docstring's exclusion narrative by one sentence -- CAP-6 sanctioned opt-out.
- `src/shared/packages/pyforge-marshal/tests/unit/test_refresh.py` -- the four stubs move from `refresh_mod.subprocess.run` to `PosixProcess.run` (`ProcessResult` fakes; launch failure raises `ProcessError`) -- keep coverage.
- `src/shared/packages/pyforge-marshal/tests/unit/test_login.py` -- add `_mint_local_token` tests over a fake `PosixProcess.run` for the three matrix rows.
- `src/shared/packages/pyforge-marshal/tests/unit/test_oidc_pkce.py`, `test_watch.py`; `src/shared/packages/pyforge-warden/tests/` (beside the tea_advisory tests) -- `issubclass` pins (PyforgeError + original base) for the four classes -- CAP-5 widening guard.

**Acceptance Criteria:**
- Given the six files as changed, when `pixi run --frozen -e pyforge-core pyforge-core-test` runs, then 0 failed (six previously-failing parametrized cases now pass) and the exemption pin test still passes.
- Given each re-parented class, when `issubclass` is checked against `PyforgeError` and its original base, then both are true, and every pre-existing `except <ExactClass>` site is untouched.
- Given `PosixProcess.run` faked to raise `ProcessError`, when `_mint_local_token` / `_sync_status_step` run, then the caller-visible outcome equals today's launch-failure outcome (`RuntimeError` / `MRS-REFRESH-008`).
- Given the station suites, when `pyforge-marshal-test`, `pyforge-warden-test`, `pyforge-testing-kit-test`, `pyforge-deps-test` run, then all green.

## Spec Change Log

### 2026-09-19 — first review pass (no code re-derivation)
- Triggering findings: BH-1 / BH-4 / IA-a (the testing-kit exemption).
- Amended: the Approach's clause "record testing-kit's `branch_diff_guard.py` as a sanctioned, tested opt-out" is superseded — the kit's nine git calls route through the guard via a function-local import, which honours the leaf declaration by the file's own precedent. The intent-contract text itself is left unedited (read-only in this step); the tracked story spec and CAP-9 are the contract and already say route.
- Known-bad state avoided: a meta-test exemption that pins continued non-conformance while the contract says the file conforms, pre-deciding spec-pyforge-core's open Q2 by omission.
- KEEP: the four re-parents (original base retained, `PyforgeError` first), the `login.py` script-side `sys.path.insert(0, …)` design, class-level `PosixProcess.run` fakes in tests, and the real-child test.

### 2026-09-19 — follow-up review pass (no code re-derivation)
- Triggering finding: BH2-2 (the function-local import's stated reason is false — `test_dependency_completeness.py` skips the `pyforge` namespace — and the real constraint, Q-26's stdlib leaf, is violated by any `pyforge.core` import: the built kit gains an undeclared runtime dependency).
- Amended: the first pass's supersession is itself reverted — the Approach's opt-out clause stands, now with the TRUE rationale (Q-26 leaf declaration; spec-pyforge-core Non-goals exclude the kit until Q2; the completeness gate cannot catch a stray import) and a premise pin that retires the exemption when the leaf declaration changes. The contract is corrected at the planning tier (spec-pyforge-core CAP-9 success via memlog + render; epics.md Story 52.1 Surface; the tracked story spec's Surface) instead of shipping code that contradicts the Spec's Non-goals.
- Known-bad state avoided: a test-support kit whose built package requires `pyforge-core` while declaring `dependencies = []`, and a guard comment citing a detector that does not fire.
- KEEP: everything in the first entry's KEEP list, plus the decoy-PYTHONPATH real-child test and the honest seam-delta comments (`stdin=DEVNULL`, utf-8/replace).

## Review Triage Log

### 2026-09-19 — Review pass (follow-up, patched-medium trigger)
- verdicts: 12 findings — high 0, medium 3, low 6, false 2, maybe-false 1
- findings:
  - `[low]` `[reject]` (ECH2-1) a parent `PYTHONPATH` entry could shadow `django` for the mint child; proposed `-E` — verified possible but `-E` drops every `PYTHON*` variable (more than the old env replaced); the accepted, now-documented widening is scoped to `config` and pinned by the decoy-PYTHONPATH test.
  - `[low]` `[reject]` (ECH2-2) `_git` in a kit env without `pyforge-core` raises `ModuleNotFoundError` instead of skipping — moot: the kit migration is reverted (below); the kit imports nothing from `pyforge.core`.
  - `[low]` `[reject]` (ECH2-3) git's stderr no longer reaches the terminal on a failed `check_output` — moot: reverted with the kit migration.
  - `[medium]` `[patch]` (ECH2-4) the claims file's opt-out is absent and the kit gained an undeclared runtime `pyforge-core` dependency hidden from `test_dependency_completeness` — verified (same evidence as BH2-2). Action: kit files restored to `main`; exemption reinstated with the true rationale and a premise pin.
  - `[low]` `[reject]` (ECH2-5) login's launch-failure path moved from a traceback crash to EXIT_USAGE — carried: ECH-2 first pass (deliberate, documented).
  - `[maybe-false]` `[reject]` (BH2-1) the diff leaves `spec-surface` red (11 drift rows) — true of the working tree, but memlog naming + scoped stamps are the landing step's last edits by design (the stamp reads the tree as landed); not a diff defect. If it were, it would be `low`.
  - `[medium]` `[patch]` (BH2-2) the function-local import's stated reason is false and Q-26's leaf is violated either way (built kit gains an undeclared runtime dep) — verified: `test_dependency_completeness.py:379` `continue`s on the `pyforge` namespace; kit `pixi.toml` `[package.run-dependencies]` = python only; parent Spec Non-goals line 187. Action: revert the migration; reinstate the exemption with the true rationale; premise pin `test_branch_diff_guard_exemption_rests_on_the_kits_leaf_declaration`; CAP-9 corrected via memlog.
  - `[low]` `[reject]` (BH2-3) the `CalledProcessError` re-raise preserved a contract nobody consumes — moot after the revert.
  - `[low]` `[reject]` (BH2-4) no real-tree negative proof for the kit as a second type-only `subprocess` retention — moot after the revert (the kit is exempt, not a retention case).
  - `[low]` `[patch]` (BH2-5) the login comment's "django resolves exactly as before" is false (a parent PYTHONPATH precedes site-packages) and the accepted widening was untested — verified. Action: claim scoped to `config`; decoy-PYTHONPATH real-child test added.
  - `[low]` `[patch]` (BH2-6) all three migration comments claimed behavioural identity the seam does not deliver (`stdin=DEVNULL`; utf-8/replace decoding) — verified against `PosixProcess.run`. Action: comments name both deltas as intentional (kit comment gone with the revert).
  - `[false]` `[reject]` (BH2-7) story bookkeeping not moved with the code — the hand-driven landing step advances the tracked spec, ledger and CAP-9 realization (done in this landing).
  - `[low]` `[patch]` (BH2-8) the timeout test's docstring claimed coverage only pyforge-core's tests establish — verified. Action: docstring narrowed to the pass-through it pins. (`errors.py`'s stale "37" count updated to 41 in the same round.)

### 2026-09-19 — Review pass (first)
- verdicts: 20 findings — high 1, medium 4, low 11, false 4, maybe-false 0
- findings:
  - `[medium]` `[patch]` (BH-1) the `branch_diff_guard.py` exemption contradicts the story's own Surface and CAP-9's success text; nothing in the planning tier records the deviation — verified: tracked story spec, epics.md Story 52.1 and spec-pyforge-core CAP-9 all say route; the exemption pinned non-conformance. Action: exemption removed; the kit's nine git calls now route through `PosixProcess.run` via a module-private `_git()` with a function-local import (the file's own `_require_ref`/`pytest` precedent), preserving `CalledProcessError` on non-zero. The Tier-3 Approach's exemption clause is superseded (Spec Change Log); the tracked contract stands as written.
  - `[low]` `[patch]` (BH-2) meta-test docstring "five" vs "sixth" exemption count; pre-existing "(fourth entry)" for `query_plane_boot.py` is wrong — with the exemption removed "five" is correct again; "fourth" → "fifth" fixed (a one-word pre-existing error in the paragraph being edited).
  - `[low]` `[patch]` (BH-3) "eight git calls" undercounts nine — moot: the comment was removed with the exemption.
  - `[medium]` `[patch]` (BH-4) the leaf premise was overstated (the PYTHONPATH claim was wrong; the kit's pixi feature already ships `pyforge-core`) and the function-local-import alternative was never addressed — verified against `pixi.toml` and `test_dependency_completeness.py` (module-level imports only, `pyforge` namespace skipped). Action: adopted the alternative; same root cause as BH-1.
  - `[low]` `[patch]` (BH-5) the exemption pinned its symptom, not its premise — moot: exemption removed.
  - `[low]` `[patch]` (BH-6) `login.py` comment misdescribed the old behaviour: `env["PYTHONPATH"]=…` REPLACED the parent's PYTHONPATH, so the child now additionally inherits it — verified. Action: comment rewritten to state the widening and why it is acceptable (`sys.path.insert(0, …)` keeps `config` deterministic; siblings resolve from the env). Same root cause as ECH-1 / IA-c.
  - `[low]` `[reject]` (BH-7) `login.py`/`refresh.py` hard-instantiate `PosixProcess()` instead of the `process: ProcessPort | None` kwarg convention — real style divergence, but the fix adds a public parameter, the spec's Always chose class-level fakes (`test_harness_bmadloop_engine_liveness.py` precedent), and the everyday harm is negligible.
  - `[false]` `[reject]` (BH-8) story status / ledger not advanced, `maintenance` label — not a defect of the diff: the hand-driven landing step advances the tracked spec and ledger and labels the PR.
  - `[low]` `[patch]` (BH-9) PKCE pin weaker than its siblings; no timeout-shaped `ProcessError` row for refresh — verified. Action: PKCE pin loops over `(PkceLoginError, Exception, PyforgeError)`; `test_sync_status_step_reports_failure_when_child_times_out` added.
  - `[low]` `[patch]` (ECH-1) parent PYTHONPATH now visible to the mint child — same root cause as BH-6; the scrub-inherited-entries guard variant rejected (adds behaviour nobody asked for); documentation patch applied.
  - `[low]` `[reject]` (ECH-2) launch failure now maps to `RuntimeError`/EXIT_USAGE where a raw `OSError` traceback escaped before, so the Always bullet's "equals today's outcome" is inexact for login — verified real and deliberate (the I/O matrix row states it; strictly an improvement); the only fix is spec wording inside the intent-contract → rejected per rule; recorded under Auto Run Result as a documented behaviour change.
  - `[false]` `[reject]` (ECH-3) `ForgeCommandError` exemplar keeps `Exception`, not `RuntimeError` — the code kept each class's ORIGINAL base (Exception for PKCE, RuntimeError for the other three); no bad outcome in code; the spec's phrasing was loose.
  - `[medium]` `[patch]` (VG-1) the rewritten `-c` child script is never executed by any test (a malformed script passed the substring checks; demonstrated) — verified. Action: `test_mint_local_token_executes_the_child_script_for_real` runs the real child against a stub `src/platform` tree (and a stub `django.py` proving `insert(0)` precedence).
  - `[high]` `[defer]` (VG-2) the sole-ownership meta guards run in no gated CI path (`pyforge-station-tests.yml` has no core job; `pr-preflight` has no core leg; `pyforge-pip-install.yml` runs an enumerated subset) — verified real and pre-existing; it is exactly Story 52.2 (spec-pyforge-core CAP-8, Deps: 52.1). Deferred to that story, not to the ledger.
  - `[low]` `[patch]` (VG-other-1) "eight git calls" → nine — duplicate of BH-3; moot.
  - `[low]` `[defer]` (VG-other-2) `pyforge-pip-install.yml:6-7` claims `pyforge-station-tests.yml` runs every core test in pixi — pre-existing false comment; Story 52.2's docs task.
  - `[medium]` `[patch]` (IA-a) intent expects the kit's calls routed; the diff exempted them and pinned the non-conformance — same root cause as BH-1/BH-4; resolved by the migration.
  - `[low]` `[reject]` (IA-b) the CAP-5 widening pins are structural (`issubclass` + raise/catch), not behavioural through real `except` sites — this is the Story 14.3 convention the parent spec defines; the grep over every `except PyforgeError` site (`marshal/cli/dispatch.py:452`, `marshal/seed/verbs/kit.py:471`, `atlas/query_plane_boot.py:364`) establishes no path to the four classes; no named harm.
  - `[low]` `[patch]` (IA-c) login env inheritance change undocumented — same root cause as BH-6.
  - `[false]` `[reject]` (IA-d) `refresh.py`'s `except ProcessError` is wider than the old `(OSError, TimeoutExpired)` (also NUL byte / empty argv) — unreachable: argv is built internally from constants and a slug; no bad outcome.

## Auto Run Result

Status: done
Blocking condition: none

**Summary of implemented change:** the six `pyforge-core` conformance failures on `main` are cleared. Four exception roots gained `PyforgeError` as first base with their original base retained (`PkceLoginError(PyforgeError, Exception)`, `LoopCliError`/`ProbeError`/`TeaRosterMissingError(PyforgeError, RuntimeError)`); marshal's `cli/login.py::_mint_local_token` and `cli/refresh.py::_sync_status_step` route through `pyforge.core.process.PosixProcess().run` (login's former custom `env` replaced by a `sys.path.insert(0, <platform src>)` inside the child script; refresh's `except (OSError, TimeoutExpired)` became `except ProcessError`); the testing-kit's `branch_diff_guard.py` is cleared as CAP-6's recorded, tested opt-out — a file-level entry in the guard's `_EXEMPT_RELATIVE_PATHS` with the Q-26 / Non-goals rationale and a premise pin on the kit's `dependencies == []`. `pixi run --frozen -e pyforge-core pyforge-core-test`: 6 failed / 1855 passed → 0 failed / 1863 passed.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py` — `PkceLoginError` re-parented.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py` — `LoopCliError`, `ProbeError` re-parented (nothing below the class definitions touched; 51.6's `_gather_station` untouched).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py` — `TeaRosterMissingError` re-parented.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/login.py` — `PosixProcess.run`; script-side `sys.path.insert`; launch failure → `RuntimeError` (EXIT_USAGE via `run_login`); honest comment on the PYTHONPATH widening and seam deltas.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/refresh.py` — `PosixProcess.run`; `except ProcessError`; seam deltas named.
- `src/shared/packages/pyforge-core/tests/meta/test_process_sole_ownership.py` — kit exemption with the true rationale + three pins (excluded; would fire with 9 sites; premise: kit `dependencies == []`); "fourth"→"fifth" docstring fix.
- `src/shared/packages/pyforge-core/src/pyforge/core/errors.py` — family-root count 37 → 41.
- Tests: `test_login.py` (+7 incl. two real-child runs), `test_refresh.py` (four stubs moved to the seam; +1 timeout-shaped launch failure), `test_oidc_pkce.py`, `test_watch.py`, warden `test_tea_advisory.py` (re-parent pins looping over every base).

**Review findings breakdown:** first pass 20 findings — patched: BH-1/BH-4/IA-a (kit migration — later reverted), BH-2, BH-3/BH-5 (moot), BH-6/ECH-1/IA-c (login comment), BH-9, VG-1 (real-child test); deferred: VG-2 (no gated lane runs the core meta-tests — Story 52.2), VG-other-2 (`pyforge-pip-install.yml` header claim — Story 52.2); rejected: BH-7 (port-injection kwarg adds public surface; spec chose class-level fakes), BH-8 (landing concern), ECH-2 (deliberate, documented behaviour change; spec-text fix), ECH-3 (false — original bases kept), IA-b (14.3 convention; grep-established), IA-d (unreachable). Follow-up pass 12 findings — patched: ECH2-4/BH2-2 (revert kit migration, reinstate exemption with true rationale + premise pin, CAP-9 corrected), BH2-5, BH2-6, BH2-8; rejected: ECH2-1 (`-E` over-drops), ECH2-2/ECH2-3/BH2-3/BH2-4 (moot after revert), ECH2-5 (carried), BH2-1 (landing-step stamp; maybe-false, if-true low), BH2-7 (landing concern).

**Follow-up review recommendation:** false — this was the single follow-up pass and it patched no `high`; the patched mediums converged on a reversal to a previously reviewed shape (the kit file is byte-identical to `main`). Patched counts: first pass high 0 / medium 3 / low 5; follow-up high 0 / medium 2 / low 3.

**Verification performed (final tree, exit codes read directly):** `pyforge-core-test` 1863 passed; `pyforge-testing-kit-test` 21 passed; `pyforge-deps-test` 130 passed / 3 skipped; `pyforge-marshal-test` 8098 passed / 1 skipped; `pyforge-warden-test` 2122 passed. Matrix rows each covered by a named passing test (listed under the first Verify).

**Documented behaviour changes (intentional):** a mint-child launch failure now exits EXIT_USAGE with the reason on stderr where a raw `OSError` traceback escaped before; the mint child inherits the parent's `PYTHONPATH` (the old env replaced it) with `config` resolution kept deterministic by `sys.path.insert(0, …)`; both migrated children run with `stdin=DEVNULL` and utf-8/replace decoding (the seam's fixed policy).

**Residual risks:** the sole-ownership meta-tests still run in no gated CI lane — Story 52.2 (CAP-8) wires them; `spec-pyforge-core` Q2 (kit as leaf vs module) remains open and now has a mechanical tripwire (the premise pin).

## Design Notes

`login.py` is the one site whose `env=` looked load-bearing. It is not: `COMPONENT_RUNTIME` and `DJANGO_SETTINGS_MODULE` are `setdefault`'d again inside the `-c` script, so only `PYTHONPATH` did work — and `sys.path.insert(0, ...)` inside the child does the same work without a custom env, which keeps `ProcessPort`'s inherit-`os.environ` contract intact. `PYTHONSAFEPATH` in the parent's environment does not affect an explicit `sys.path.insert`.

`branch_diff_guard.py` is the deliberate opt-out. Routing it through `pyforge.core` would make a declared stdlib leaf import a package it does not declare (fails `test_dependency_completeness`) or force a new dependency edge into a test-support kit — both larger than CAP-6's "recorded as a sanctioned, tested opt-out". The exemption is file-level, commented, and pinned like the other five.

## Binding

Parent Spec capability: `spec-pyforge-core CAP-9`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py`, `.../cli/watch.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py` (exception root — re-parent to the core root, no `except` clause widens); `.../marshal/cli/login.py`, `.../marshal/cli/refresh.py` (route through the core subprocess guard); `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py` (cleared as CAP-6's recorded, tested opt-out — a file-level entry in the guard's `_EXEMPT_RELATIVE_PATHS` pinned to the kit's Q-26 `dependencies == []`; outside spec-pyforge-core's scope per its Non-goals until Q2 — corrected at review 2026-09-19); tests.
Ledger key: `52-1-the-six-accumulated-violations-are-cleared`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-52-1-the-six-accumulated-violations-are-cleared.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 52.1 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
