---
title: 'Partial install is a named failure'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/SPEC.md']
warnings: ['oversized']
baseline_revision: '538ffa0d208f323233db55d5a234952c7621e2e3'
final_revision: 'f1beb226ea33327669dbcdf72f3725560bb6c02b'
---

<intent-contract>

## Intent

**Problem:** `provision_module()` (Story 6.1) runs two subprocess steps (`merge-config.py` then `merge-help-csv.py`) and only ever reports what the failing exception itself says. If the first script succeeds and the second fails, `_bmad/config.yaml` already has a `<name>` section, but the `DutyResult(ok=False, ...)` never says so — the operator only sees the second script's stderr. And if both scripts exit 0, `_run_module` trusts that at face value and returns `ok=True` without ever confirming `<name>` actually landed in `_bmad/config.yaml` — FR-21's second clause ("succeeds while leaving the module unimportable") is entirely unguarded today.

**Approach:** In `_run_module`, wrap the `provision_module()` call so a failure names whether `_bmad/config.yaml` already gained a `<name>` section before the failure (reusing Story 6.2's `module_install_states`, never re-deriving that check); and, after `provision_module()` reports success, call `module_install_states` once more to confirm `<name>` is actually installed before returning `ok=True` — if it isn't, report a named failure instead of trusting the subprocess's self-report.

## Boundaries & Constraints

**Always:**
- Every new failure/verification check reuses `module_install_states(cwd=root)` (Story 6.2) as the single "is `<name>` actually installed" oracle — never a second, divergent way of answering the same question.
- A failure that occurs after `provision_module()` may have already run `merge-config.py` (`subprocess.CalledProcessError` or `RuntimeError` from `provision_module`) has its `DutyResult` summary explicitly state whether `_bmad/config.yaml` already gained a `<name>` section before the failure — never left for the operator to infer.
- After both setup-skill scripts report success, `_run_module` verifies `<name>` is present in `module_install_states(cwd=root)` before returning `ok=True`; if absent, returns `ok=False` naming that the scripts exited 0 but `<name>` was not counted as provisioned.
- `--json` is honored on both new failure paths via the existing `ProvisionDuty._render_error`, matching every other flag's error contract.
- The wrapped installer's own stderr still reaches the operator verbatim (unchanged from Story 6.1) — the new "already landed" note is appended, never replaces it.

**Block If:** None identified — the oracle (`module_install_states`), the two failure points needing the new naming (mid-chain subprocess/runtime failure, post-success verification), and the message wording are all resolved below with evidence from the real `provision_module()`/`merge-config.py` source.

**Never:**
- Does not change `provision_module()`'s own signature, return shape, or exception types — Story 6.1's already-reviewed internals are untouched; the new logic lives entirely in `_run_module`.
- Does not add a third `module_install_states` state or change its derivation — Story 6.2 already resolved "two states, not three" and this story reuses that primitive as-is.
- Does not catch `FileNotFoundError` (unregistered name / missing backend dir) in the new local handler — both occur before any subprocess call, so nothing can have landed; Story 6.1's existing message and tests for that path are unchanged.
- Does not attempt real-backend verification beyond `_bmad/config.yaml` membership (e.g., does not open `.claude/skills/` or run the module's own CLI) — `module_install_states` is the one filesystem oracle this codebase has for "installed," matching Story 6.2's own two-state design.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First script succeeds, second fails | `merge-config.py` exits 0 (writes `bmb:` into `_bmad/config.yaml`), `merge-help-csv.py` exits 1 | `DutyResult(ok=False, ...)` with the failing script's stderr **and** a note that `_bmad/config.yaml` already has a `bmb` section | `subprocess.CalledProcessError`, caught locally in `_run_module` |
| First script itself fails | `merge-config.py` exits 1, nothing written | `DutyResult(ok=False, ...)` with the stderr **and** a note that nothing was written to `_bmad/config.yaml` | `subprocess.CalledProcessError`, caught locally |
| Both scripts exit 0, output-dir creation fails afterward | `_materialize_module_output_dirs` raises `RuntimeError` (occupied path) | `DutyResult(ok=False, ...)` with the `RuntimeError` text **and** a note that `_bmad/config.yaml`/`module-help.csv` already updated | `RuntimeError`, caught locally |
| Both scripts exit 0 but `<name>` never lands in `_bmad/config.yaml` | Hypothetical backend inconsistency (simulated in tests) | `DutyResult(ok=False, ...)` naming that the scripts exited 0 but `<name>` was not counted as provisioned | No exception — verification gate, not an error path |
| Full success (unchanged happy path) | Both scripts exit 0 and `<name>` verified present afterward | `DutyResult(ok=True, ...)` exactly as Story 6.1 | No error expected |
| Any new failure path with `--json` | flag combo | Parseable `{"error": ...}` via existing `_render_error` | Same JSON shape as every other error path |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- add `_format_called_process_error()` (dedupe the stderr-formatting logic currently inline in `ProvisionDuty.run()`'s except block); wrap `_run_module`'s `provision_module()` call in a local try/except naming already-landed state; add the post-success `module_install_states` verification gate before returning `ok=True`
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py` -- update `_fake_module_scripts_run` to perform the same minimal `_bmad/config.yaml`/`module-help.csv` writes the real scripts perform (so the new verification is meaningfully exercised, not vacuously true against an empty filesystem); add tests for the two new naming paths and the post-success verification gate
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/{spec-bmad-module-provisioning,spec-pyforge-steward}/.memlog.md` -- append one `(change)` entry to each, naming every touched file (S-13.2, matching Stories 6.1/6.2's own precedent)

## Tasks & Acceptance

**Execution:**
- [x] `provision.py` -- add `_format_called_process_error(exc: subprocess.CalledProcessError) -> str`, extracting the `` `{cmd}` exited {code}: {stderr} `` formatting currently inline in `ProvisionDuty.run()`'s except block; call it from both that block and the new local handler below (no behavior change to existing formatting)
- [x] `provision.py` -- in `_run_module`, wrap `steps = provision_module(name, cwd=root)` in `try/except (subprocess.CalledProcessError, RuntimeError) as exc`: build the base message via `_format_called_process_error(exc)` or `str(exc)`, then append a note based on `module_install_states(cwd=root).get(name) == "installed"` — `"; already wrote a {name!r} section to _bmad/config.yaml before this failure -- provisioning is INCOMPLETE"` when true, `"; nothing was written to _bmad/config.yaml before this failure"` when false; return `DutyResult(ok=False, summary=ProvisionDuty._render_error(ns, message))`
- [x] `provision.py` -- after the try/except succeeds (no exception), before formatting the success summary: if `module_install_states(cwd=root).get(name) != "installed"`, return `DutyResult(ok=False, summary=ProvisionDuty._render_error(ns, f"{name!r}'s setup-skill scripts both exited 0, but {name!r} is not present in _bmad/config.yaml afterward -- not counted as provisioned"))`
- [x] `provision.py` -- replace `ProvisionDuty.run()`'s inline `CalledProcessError` formatting with a call to `_format_called_process_error(exc)`
- [x] `test_provision_module.py` -- update `_fake_module_scripts_run` to parse `--config-path`/`--target` out of `cmd` and write a minimal realistic file at each (a `bmb:` section for config.yaml, a header+one-row CSV for module-help.csv) before returning its JSON stdout, so `module_install_states` sees a real, consistent filesystem state in every existing happy-path test
- [x] `test_provision_module.py` -- add tests covering every new I/O Matrix row: mid-chain failure after the first script lands (asserts the "already wrote a section" note), first-script-itself failure (asserts the "nothing was written" note), output-dir `RuntimeError` after both scripts land (asserts the same "already wrote" note), a simulated backend that exits 0 on both scripts without ever writing `<name>` into `_bmad/config.yaml` (asserts `ok=False` and `EXIT_FAILED` via `main()`), and `--json` honored on both new failure paths
- [x] Append one `(change)` memlog entry to each of `spec-bmad-module-provisioning` and `spec-pyforge-steward`, naming every file this story touches (S-13.2)

**Acceptance Criteria:**
- Given `merge-config.py` succeeds and `merge-help-csv.py` fails, when `steward provision --module <name>` runs, then the result is `ok=False` and the summary names both the failing script's stderr and that `_bmad/config.yaml` already gained a `<name>` section
- Given `merge-config.py` itself fails before any file is written, when `steward provision --module <name>` runs, then the summary states nothing was written to `_bmad/config.yaml`
- Given both setup-skill scripts exit 0 but `<name>` is not present in `_bmad/config.yaml` afterward, when `steward provision --module <name>` runs, then the result is `ok=False`, explicitly naming that the scripts exited 0 but the module was not counted as provisioned
- Given a fully successful run (both scripts exit 0 and `<name>` verified present), when `steward provision --module <name>` runs, then `DutyResult(ok=True, ...)` is returned exactly as Story 6.1 established -- no regression on the true happy path
- Given any of the new failure paths above with `--json`, when `steward provision --module <name> --json` runs, then the result is parseable JSON honoring the existing `_render_error` error shape

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 1, medium 1, low 2)
- defer: 0
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` Both Blind Hunter and Edge Case Hunter independently found and reproduced the same bug: the failure-naming logic in `_run_module`'s except handler compared only the POST-failure `module_install_states` read against nothing, so a failure against a module ALREADY installed by a prior run (e.g. a transient `uv` invocation error that touches no file) was misreported as `"already wrote a '<name>' section ... provisioning is INCOMPLETE"` even though this run changed nothing. Fixed by capturing a `state_before` snapshot before calling `provision_module()` and comparing it against `state_after`: the "INCOMPLETE" note now only fires when the state genuinely transitioned from not-installed to installed during this run; a failure against an already-installed module gets no landed-state note at all, since nothing about this run's outcome is newly incomplete. New regression test: `test_provision_module_failure_against_an_already_installed_module_does_not_claim_incomplete`.
  - `[medium]` `[patch]` Both reviewers also found that the recovery read (`module_install_states(cwd=root)`, called inside the except handler to determine the landed-state note) could itself raise `yaml.YAMLError` if `_bmad/config.yaml` happened to be malformed at that moment — silently REPLACING the original, more diagnostic subprocess stderr/RuntimeError text with an unrelated YAML-parse error, masking the real failure. Fixed by adding `_module_install_state_or_none()`, a narrow wrapper that catches `(yaml.YAMLError, OSError)` and degrades to `None` ("could not confirm") rather than letting a secondary exception replace the primary one; used for both the before/after snapshots and the post-success verification gate's own read (which had the identical unguarded-read shape, plus a masking risk on the success path this story's own new code owns). New regression tests: `test_provision_module_malformed_config_during_failure_recovery_read_preserves_original_stderr`, `test_provision_module_post_success_gate_survives_an_unreadable_config_yaml`.
  - `[low]` `[patch]` A bare `OSError`/`PermissionError` from the same recovery read (not a subclass of any type in `ProvisionDuty.run()`'s outer except tuple) would propagate past a `DutyResult` entirely, surfacing as an internal crash (`EXIT_INTERNAL` via `cli.main()`'s own catch-all, or a raw exception through the `ProvisionDuty().run()` API directly) rather than the clean, correctly-classified `ok=False` failure this story exists to produce. Same fix as the medium finding above (`_module_install_state_or_none`'s `except (yaml.YAMLError, OSError)`) closes this too.
  - `[low]` `[patch]` `provision_module()`'s own docstring still claimed its `subprocess.CalledProcessError` is "caught only at `ProvisionDuty`'s existing boundary," no longer accurate for the `--module` path now that `_run_module` intercepts it one layer earlier. Updated the docstring to name the split (`FileNotFoundError` still reaches `ProvisionDuty`'s boundary; `CalledProcessError`/`RuntimeError` are now caught inside `_run_module`).

Rejected (verified, not fixed): the already-computed `steps` dict (each script's own parsed JSON envelope) is discarded on the post-success verification gate's failure path, even under `--json` — a DX nicety for a branch the real `bmb` backend cannot reach today (per this spec's own Design Notes), not a correctness gap; the existing message already states the accurate, actionable fact (`ok=False`, "not counted as provisioned"). `module_install_states` being re-read from disk on every call with no memoization — matches Story 6.2's own already-reviewed derive-don't-declare design (no state file, always re-read); this story adds call sites to an existing, accepted pattern, not a new risk class.

## Design Notes

**Why reuse `module_install_states` instead of a bespoke check:** it is already the codebase's one oracle for "is `<name>` installed" (Story 6.2, `--list-modules`'s own backing primitive) — a pure, read-only `_bmad/config.yaml` top-level-key check. Introducing a second, parallel notion of "landed" would let the two drift; reusing it means `--module`'s own success verification and `--list-modules`'s reporting can never disagree about what "installed" means.

**Why the post-success verification is reachable only via a simulated backend in tests, not the real `bmb` backend:** Story 6.1's review already verified `merge-config.py`'s real source always pairs `"status": "success"` with actually writing `config[module_code] = module_section` — so with the real backend this branch cannot fire today. It exists as a defensive contract for FR-21's literal wording ("succeeds while leaving the module unimportable") and for future backends this registry may grow to include, not because today's `bmb` backend is known to be unreliable.

**Why `FileNotFoundError` stays out of the new local catch:** it is raised in `provision_module` only before any subprocess call (unregistered name or missing backend directory) — nothing could have landed, so Story 6.1's existing message is already complete and its tests must keep passing unchanged.

## Verification

**Commands:**
- `cd src/shared/packages/pyforge-steward && python3 -m pytest tests/conformance/test_provision_module.py -q` -- all tests (existing + new) pass
- `cd src/shared/packages/pyforge-steward && python3 -m pytest tests -q` -- full existing suite stays green
- `python3 scripts/spec_surface_check.py` -- exit 0, no drift (after the memlog updates)

**Manual checks (real backend, no mocks):**
- From repo root, with `local-recipes` on PATH: `pixi run -e pyforge-steward steward provision --module bmb`, confirm the happy path still reports `ok=True` against the real `bmb` backend (unaffected by the new verification gate, since the real backend always lands the section on exit 0).

## Auto Run Result

- **Summary:** `_run_module` (`provision --module <name>`) no longer trusts `provision_module()`'s
  two wrapped subprocess steps at face value. A new `_format_called_process_error()` helper
  dedupes the `` `{cmd}` exited {code}: {stderr} `` formatting `ProvisionDuty.run()`'s except
  block already applied inline (that block now calls the helper -- no behavior change).
  `_run_module` wraps its `provision_module()` call in a local
  `try/except (subprocess.CalledProcessError, RuntimeError)` that compares a `module_install_states`
  snapshot taken BEFORE the call against one taken after it fails: `"; already wrote a '<name>'
  section to _bmad/config.yaml during this run before the failure above -- provisioning is
  INCOMPLETE"` when `<name>` newly transitioned to installed during this run, `"; nothing was
  written to _bmad/config.yaml before this failure"` when it's still not installed, and no note
  at all when it was already installed before this run started (nothing about this run's own
  outcome is newly incomplete). Both snapshots go through `_module_install_state_or_none()`, a
  narrow wrapper degrading a `yaml.YAMLError`/`OSError` read failure to "unknown" rather than
  masking the original failure or crashing past this boundary. After a successful call, the same
  wrapper is consulted once more before reporting `ok=True`; if `<name>` isn't `installed`, the
  run reports `ok=False` naming `"not counted as provisioned"` instead of trusting the scripts'
  own exit-0 self-report (FR-21's "succeeds while leaving the module unimportable" clause,
  previously entirely unguarded). `FileNotFoundError` (unregistered name / missing backend dir)
  is untouched -- it still propagates to `ProvisionDuty.run()`'s outer boundary exactly as Story
  6.1 left it. `--json` is honored on both new failure paths via the existing `_render_error`.
- **Review pass:** Blind Hunter (`bmad-review-adversarial-general`) and Edge Case Hunter
  (`bmad-review-edge-case-hunter`) ran in parallel against the full diff and independently
  converged on the same three real bugs in the first implementation attempt -- a false
  "provisioning is INCOMPLETE" claim on a failure against an already-installed module (no
  before-snapshot to compare against), a masked-original-error risk when the recovery read
  itself hit a malformed `_bmad/config.yaml`, and an unguarded `OSError`/`PermissionError` path
  on the same read. All three were fixed in this pass (4 patch findings total, including a stale
  docstring; see `## Review Triage Log` above for full detail and the 2 rejected findings).
- **Files changed:**
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- new
    `_format_called_process_error()` and `_module_install_state_or_none()`; `_run_module` grows
    a before/after state comparison in its local try/except plus a post-success verification
    gate, both routed through the new defensive wrapper; `ProvisionDuty.run()`'s
    `CalledProcessError` except block refactored to call the shared formatting helper;
    `provision_module()`'s docstring corrected (review finding); module-level and `_run_module`
    docstrings extended to describe the new behavior.
  - `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py` --
    `_fake_module_scripts_run` now parses `--config-path`/`--target` out of `cmd` and writes a
    minimal realistic `bmb:` config.yaml section / header+one-row `module-help.csv` before
    returning its JSON stdout; new `_fake_module_scripts_run_without_writing_config` helper
    simulates the FR-21 backend-inconsistency scenario. 11 new tests added (23 -> 34) covering
    every I/O Matrix row plus the three review-pass regressions (already-installed-module false
    positive, malformed-config masking, unreadable-config crash-avoidance on the post-success
    gate). 1 pre-existing test augmented with one extra assertion.
  - `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/.memlog.md`
    and `.../spec-pyforge-steward/.memlog.md` -- one `(change)` entry each (S-13.2), both
    updated in this pass to describe the corrected before/after-snapshot behavior rather than
    the first draft's single-snapshot version.
  - `_bmad-output/implementation-artifacts/spec-6-3-partial-install-is-a-named-failure.md` (this
    file) -- Tasks & Acceptance checkboxes, `## Review Triage Log` entry, and this Auto Run
    Result.
- **Deviations from the letter of the spec (both narrowly scoped, no contract change):**
  1. Extended the module-level docstring and `_run_module`'s own docstring to describe the new
     local try/except and verification gate -- not explicitly listed in Tasks & Acceptance, but
     matches the file's own established convention (every prior story added a paragraph to the
     top docstring describing its own slice) and the repo's "match existing style" guideline.
  2. The before/after snapshot comparison and the `_module_install_state_or_none` defensive
     wrapper are additions beyond the spec's original Tasks list, added during the review pass
     to fix the two real bugs Blind Hunter and Edge Case Hunter found (see Review Triage Log);
     both stay strictly within the intent-contract's existing Always/Never boundaries (still
     `module_install_states` as the one oracle, still no third state, still `--json` honored).
  3. Rather than adding only brand-new tests, augmented one pre-existing test
     (`test_provision_module_script_failure_surfaces_stderr_verbatim_and_honors_json`) with one
     extra assertion, because it already exercised the exact "first-script-itself failure +
     `--json`" scenario the spec's task list calls out.
- **Review findings breakdown:** patch 4 (fixed: already-installed-module false-positive [high],
  masked-original-error on a malformed recovery read [medium], unguarded OSError on the same
  read [low], stale `provision_module` docstring [low]); defer 0; reject 2 (verified non-issues
  -- discarded diagnostic payload on an currently-unreachable branch, and
  `module_install_states`'s re-read-per-call pattern matching Story 6.2's own already-reviewed
  design).
- **Follow-up review recommendation:** `false` -- the fixes are localized to `_run_module`'s new
  code (one before/after comparison plus one defensive wrapper reused at three call sites), no
  new capability, no API/data-model change, and the full suite (264 tests, including every
  Story 6.1/6.2 regression) stayed green throughout. The high-severity finding was a real
  correctness bug, but its fix and the regression test proving it are both narrow and already
  independently verified by two adversarial passes plus this pass's own re-run.
- **Verification performed:**
  - `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py -q`
    -- 34 passed.
  - `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q` -- 264
    passed (253 pre-story + 11 new).
  - `python3 scripts/spec_surface_check.py` -- exit 0, "OK: every tracked file governed or
    allowlisted; no drift" (re-run after the review-pass memlog edits; clean).
- **Residual risks:**
  - The spec's own "Manual checks" (real `bmb` pixi backend / `uv` on PATH,
    `pixi run -e pyforge-steward steward provision --module bmb` against the true unmocked
    backend) were not run in this unattended session -- consistent with the spec marking them
    manual rather than a gating verification command, and with Stories 6.1/6.2's own dev-session
    posture. The Design Notes' own reasoning (`merge-config.py`'s real source always pairs
    `"status": "success"` with actually writing the section) is the basis for expecting the real
    backend to be unaffected by the new verification gate; this has not been independently
    re-verified against the live backend in this session.
  - The rejected "discarded diagnostic payload" finding names a real (if low-value) DX gap on a
    branch the real `bmb` backend cannot reach today; worth reconsidering if `_SUPPORTED_MODULES`
    grows a second, less-disciplined backend where the post-success gate's failure branch becomes
    live.
