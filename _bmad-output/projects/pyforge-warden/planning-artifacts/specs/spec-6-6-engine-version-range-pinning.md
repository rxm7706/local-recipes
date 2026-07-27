---
title: 'Story 6.6: Engine version-range pinning (the distribution gate)'
type: 'feature'
created: '2026-07-24'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'abbc90839f1da3797a47ced38d1c656a3e2f2952'
final_revision: '5f548c1183'
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `pixi.toml` pins `deptry`/`osv-scanner` run-deps to `"*"`, so any future feedstock build could silently ship an engine whose JSON output shape was never verified — undetected schema drift the C0 "never false-green" guarantee depends on catching. FR21 already promises engine version-compatibility detection, but nothing implements it, and internal JFrog v1 + public v1.x publish are both blocked (D6) until this closes.

**Approach:** Pin `deptry`/`osv-scanner` in `pixi.toml` to the exact minor range each already has in-repo output-schema evidence for (0.25.1 / 2.4.0), and add a runtime `--version` pre-flight in `engines.py` (the module's sole subprocess site) that fails loud via the EXISTING `ENGINE_UNAVAILABLE` kind — FR21's "unavailable/incompatible" is one typed kind, not two — before either engine's real scan trusts its output.

## Boundaries & Constraints

**Always:**
- The range is evidence-backed, not assumed: only the exact minor already verified in-repo is trusted (deptry 0.25.1 — hygiene.py's DEP005 docstring evidence; osv-scanner 2.4.0 — vuln.py's "Empirically-verified 2.4.0 shape" docstring), open only to patch releases of that SAME minor (NFR-C1: a range, not an exact pin, since engines come from feedstocks).
- `pixi.toml`'s declared range string and the Python-side `SpecifierSet` constants in `engines.py` must never drift apart — enforced by a new meta-test parsing `pixi.toml` directly.
- The version check runs BEFORE the real engine subprocess in both `DeptryEngine.run` and `OsvEngine.run`, reusing `_engine_env`'s own typed-error taxonomy (`FileNotFoundError`→unavailable, `TimeoutExpired`→timeout, `OSError`→execution-failed) plus a new terminal case — unparseable or out-of-range version text — that ALSO maps to `ENGINE_UNAVAILABLE` (no new `ErrorKind` member; 6.1 froze `error_kind`'s schema enum).
- A version-check failure preserves every finding already computed at that point in each `run()` — deptry's purity-guard `excluded_findings`; osv's `excluded_findings`/`name_level_findings`/`stale_findings`/`kev_findings`/`epss_findings` — mirroring the adjacent `mkstemp_error`/`FileNotFoundError` branches' never-silently-dropped handling.
- `OsvEngine`'s version check sits immediately before the ONE branch that actually shells out to `osv-scanner` (after the no-candidates / DB-unavailable / name-level-only early returns) — those paths never invoke the real subprocess today and must keep not invoking the version check either.
- `sprint-status.yaml`'s `release_gates` row for the v1-publish gate flips from `blocked` once this story verifies done — its mechanical home (D6).
- Standing cross-cutting gates hold: C0 fixtures unaffected by the range/version-check addition; twice-run determinism (NFR-R3b) — the check is deterministic for a fixed engine binary.

**Block If:** none identified — self-contained within `pixi.toml`, `engines.py`, and `sprint-status.yaml`.

**Never:**
- No new `ErrorKind` member and no `report-schema.json` change — the schema stays frozen post-6.1.
- No change to `deptry`/`osv-scanner`'s argv, output parsing, or the finding shapes they produce — this story only adds a pre-flight gate in front of the existing calls.
- No change to `NullEngine`/`LicenseEngine`/`CurrencyEngine` or to `verdict.py`'s lattice/exit projection.
- No widening the range beyond the evidenced minor "to be safe" — an untested newer minor must fail loud, not silently pass; that is NFR-C1's entire point.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| In-range engine | `deptry --version` reports `0.25.1` | version check passes silently; scan proceeds exactly as before this story | No error |
| Missing engine | engine binary not on PATH | `ENGINE_UNAVAILABLE`, "not found" message; real subprocess never invoked; pre-computed findings preserved | Typed error, no crash |
| Out-of-range engine | engine reports a version outside the pinned range | `ENGINE_UNAVAILABLE`, "outside tested range" message; real subprocess never invoked | Typed error |
| Unparseable version text | `--version` output doesn't match the expected pattern | `ENGINE_UNAVAILABLE`, "could not parse version" message | Typed error, fail closed |
| osv-scanner: no candidates | inventory has zero vuln-matchable/name-level components | version check never runs — osv-scanner was never invoked here before this story either | No error |
| osv-scanner: name-level-only scan | components with no concrete version, DB valid | version check never runs — the real subprocess still isn't invoked on this path | No error |
| osv-scanner: real scan | candidates present, DB valid, in-range engine | version check runs once, immediately before the real `osv-scanner` subprocess call | No error |
| `pixi.toml` / `engines.py` drift | one edited without the other | the new sync meta-test fails | Test failure, not a runtime defect |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/pixi.toml` -- `deptry = "*"` / `osv-scanner = "*"` (run-dependencies) → `">=0.25.1,<0.26"` / `">=2.4.0,<2.5"`; update the adjacent comment block (currently says "range-pinning is Story 6.6's job" — record this story as `pixi.toml`'s owner, closing review-T-a).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` -- add `from packaging.specifiers import SpecifierSet` + `from packaging.version import InvalidVersion, Version`; module constants `DEPTRY_VERSION_RANGE = SpecifierSet(">=0.25.1,<0.26")` / `OSV_SCANNER_VERSION_RANGE = SpecifierSet(">=2.4.0,<2.5")` (mirroring `pixi.toml` verbatim) + their `--version` regex patterns; a new `_check_engine_version(*, owner, argv, version_pattern, expected, cwd) -> ErrorRecord | None` helper (stdout-capturing subprocess call — `--version` has no output-file equivalent for `_engine_env`'s tempfile contract — reusing its FileNotFoundError/TimeoutExpired/OSError taxonomy). Call it at the top of `DeptryEngine.run` (after `excluded_findings` is computed, before the deptry subprocess); call it in `OsvEngine.run` immediately before the real `osv-scanner` `_engine_env` invocation (after the `if not synthesized.lines:` early-return branch), merging the same findings tuple that branch already assembles on failure.
- `src/shared/packages/pyforge-warden/tests/meta/test_engine_version_range_sync.py` (new) -- parses `pixi.toml` with `tomllib` and asserts its `deptry`/`osv-scanner` run-dependency strings equal `str(DEPTRY_VERSION_RANGE)`/`str(OSV_SCANNER_VERSION_RANGE)` byte-for-byte; fails loud on drift in either direction.
- `src/shared/packages/pyforge-warden/tests/unit/test_engine_env_deptry.py` -- add `_check_engine_version` coverage (in-range / out-of-range / missing / unparseable, injected fakes only) + a `DeptryEngine.run` test proving the real deptry subprocess is never invoked when the version gate fails, and that `excluded_findings` still survive.
- `src/shared/packages/pyforge-warden/tests/conformance/test_osv_engine.py` -- same coverage for `OsvEngine.run`'s version gate, plus a regression proving the check is SKIPPED on the no-candidates / name-level-only / DB-unavailable paths (osv-scanner subprocess still never invoked there, unchanged from pre-story behavior).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- flip the `release_gates` row (`v1-publish-jfrog-internal-and-v1x-public-pypi-conda-forge`) from `blocked` once this story is verified done.

## Tasks & Acceptance

**Execution:**
- [x] `pixi.toml` -- pin `deptry`/`osv-scanner` to their evidence-backed ranges; update the run-dependencies comment -- closes review-T-a's unowned mitigation
- [x] `engines.py` -- `DEPTRY_VERSION_RANGE`/`OSV_SCANNER_VERSION_RANGE` constants + version regex patterns -- the Python-side mirror of the pixi.toml pin
- [x] `engines.py` -- `_check_engine_version(...)` helper -- FR21's version-compatibility detection, reusing `_engine_env`'s typed-error taxonomy
- [x] `engines.py` -- wire the check into `DeptryEngine.run` (top, after `excluded_findings`) -- deptry always invokes the real subprocess, so the gate is unconditional
- [x] `engines.py` -- wire the check into `OsvEngine.run` (immediately before the real `osv-scanner` call only) -- must not run on the paths that never shell out today
- [x] `tests/meta/test_engine_version_range_sync.py` -- new drift-detection meta-test -- keeps `pixi.toml` and `engines.py` from silently diverging
- [x] `tests/unit/test_engine_env_deptry.py` -- version-gate coverage for `_check_engine_version` + `DeptryEngine.run` -- proves fail-closed behavior and finding preservation
- [x] `tests/conformance/test_osv_engine.py` -- version-gate coverage for `OsvEngine.run`, incl. the skip-on-early-return regression -- proves the gate doesn't fire where the subprocess never ran
- [x] `sprint-status.yaml` -- flip the `release_gates` row from `blocked` on verified completion -- the D6 gate's mechanical home

**Acceptance Criteria:**
- Given `pixi.toml` today (`deptry = "*"`, `osv-scanner = "*"`), when this story lands, then both carry a tested version range (not an exact pin) matching the evidence already recorded in-repo (deptry 0.25.1, osv-scanner 2.4.0).
- Given an engine that is missing, unparseable, or outside its pinned range, when a scan runs, then the affected engine's axis fails loud via a typed `ENGINE_UNAVAILABLE` `ErrorRecord`, the real engine subprocess is never invoked, and any findings already computed before the check (purity-guard exclusions, name-level/stale/KEV/EPSS findings) are preserved, never dropped.
- Given an in-range engine, when a scan runs, then behavior and output are unchanged from pre-story (`--deterministic` twice-run byte-identical, NFR-R3b; C0 fixtures pass as before).
- Given `osv-scanner`'s no-candidates / name-level-only / DB-unavailable paths, when a scan runs, then the version check does not run and the real subprocess is still never invoked — unchanged from today.
- Given the story verifies done, then `sprint-status.yaml`'s release-gate row is updated and `pixi.toml`'s run-dependencies comment records this story as `pixi.toml`'s owner.
- Given `pixi.toml` and `engines.py`'s range constants, when the new meta-test runs, then they match exactly; editing one without the other fails the test.

## Spec Change Log

(No bad_spec loopback occurred during this story's review pass — empty.)

## Review Triage Log

### 2026-07-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (medium 1, low 1)
- defer: 0
- reject: 0: (high 0, medium 0, low 6)
- addressed_findings:
  - `[medium]` `[patch]` `_check_engine_version` never checked the `--version` subprocess's exit code — a broken/misconfigured engine install that exits non-zero but still prints a matching (e.g. stale/cached) version banner on stdout would pass the gate on content alone. Fixed: a non-zero `completed.returncode` now returns `ENGINE_UNAVAILABLE` before the version text is even parsed; regression test added (`test_check_engine_version_nonzero_exit_is_engine_unavailable_even_with_matching_stdout`).
  - `[low]` `[patch]` The `FileNotFoundError` handler didn't disambiguate "binary not found" from "cwd vanished" the way the adjacent `_engine_env` seam already does three lines below (both raise the same exception) — message-accuracy only, never a false pass. Fixed by mirroring `_engine_env`'s `os.path.isdir(cwd)` TOCTOU guard; regression test added (`test_check_engine_version_vanished_cwd_is_distinguished_from_missing_binary`).

Rejected as noise (6, all low real-world plausibility, none a false-green risk): a TOCTOU race between the `--version` preflight and the real engine subprocess (two separate `subprocess.run` calls of the same binary name) — an adversarial local-binary-replacement scenario outside this tool's stated threat model; `pixi.lock` not regenerated — verified the currently-locked versions (0.25.1/2.4.0) already satisfy the new tightened range, so no functional break; the version regexes anchoring to today's exact `--version` banner text — explicitly fails safe (over-blocking) by design, never a false positive; a hypothetical multi-line-match misparse — not demonstrated against the real, live-verified `--version` output of either engine; `ENGINE_TIMEOUT` being shared between the 10s preflight and the real scan's own timeout — the `.message` text already distinguishes them and no consumer mechanically branches on kind alone; and a process-completeness concern about the `sprint-status.yaml`/spec-DoD gate recording, which was independently verified already correct (the `release_gates` row is flipped; the separate master-spec DoD checkbox intentionally stays unchecked since it tracks actual publish having happened, not this story landing).

All 2 patch fixes applied; full suite re-verified green (1869 passed, net +2 regression tests) after patching.

## Design Notes

The check is a second, narrowly-scoped exception to `engines.py`'s "one subprocess seam" rule (`_engine_env`) — justified because `_engine_env`'s contract always writes to an `-o`/`--output`-style tempfile flag that `--version` has no equivalent of; capturing stdout directly is simpler and doesn't touch disk at all.

```python
DEPTRY_VERSION_RANGE = SpecifierSet(">=0.25.1,<0.26")
_DEPTRY_VERSION_PATTERN = re.compile(r"^deptry\s+(\S+)", re.MULTILINE)

def _check_engine_version(*, owner, argv, version_pattern, expected, cwd) -> ErrorRecord | None:
    try:
        completed = subprocess.run(
            argv, cwd=str(cwd), env={**os.environ, "NO_COLOR": "1"},
            stdin=subprocess.DEVNULL, capture_output=True,
            timeout=ENGINE_VERSION_CHECK_TIMEOUT_SECONDS, check=False,
        )
    except FileNotFoundError:
        return ErrorRecord(kind=ErrorKind.ENGINE_UNAVAILABLE, owner=owner,
                            message=f"engine binary for {owner!r} not found on PATH")
    # TimeoutExpired -> ENGINE_TIMEOUT, OSError -> ENGINE_EXECUTION_FAILED (mirrors _engine_env)
    match = version_pattern.search(completed.stdout.decode("utf-8", errors="replace"))
    if match is None or Version(match.group(1)) not in expected:
        return ErrorRecord(kind=ErrorKind.ENGINE_UNAVAILABLE, owner=owner,
                            message=f"{owner!r} version is missing, unparseable, or outside {expected}")
    return None
```

`deptry --version` prints `deptry 0.25.1`; `osv-scanner --version` prints a multi-line block starting `osv-scanner version: 2.4.0` — each engine needs its own regex, verified live against the currently-locked `pixi.lock` versions during this story's implementation.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including the new version-gate coverage and the pixi.toml/engines.py sync meta-test.

## Auto Run Result

**Summary:** `deptry`/`osv-scanner` moved from unbounded `"*"` run-deps to evidence-backed tested ranges (`>=0.25.1,<0.26` / `>=2.4.0,<2.5`) in `pixi.toml`, and a new `--version` pre-flight (`_check_engine_version`) now gates both `DeptryEngine.run` and `OsvEngine.run` before either trusts its engine's output — fulfilling FR21's version-compatibility detection via the existing `ENGINE_UNAVAILABLE` typed error (no schema change; 6.1 stays frozen). The D6 release gate (internal JFrog v1 + public v1.x publish) is now unblocked in `sprint-status.yaml`.

**Files changed:**
- `src/shared/packages/pyforge-warden/pixi.toml` — `deptry`/`osv-scanner` range-pinned; comment records this story as `pixi.toml`'s owner (closes review-T-a).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` — `DEPTRY_VERSION_RANGE`/`OSV_SCANNER_VERSION_RANGE` constants + regex patterns; new `_check_engine_version` helper; wired into `DeptryEngine.run` (unconditional, top of `run()`) and `OsvEngine.run` (immediately before the one real `osv-scanner` call); review pass hardened it with a non-zero-exit check and a vanished-cwd disambiguation.
- `src/shared/packages/pyforge-warden/tests/meta/test_engine_version_range_sync.py` (new) — drift guard between `pixi.toml` and `engines.py`'s range constants.
- `src/shared/packages/pyforge-warden/tests/unit/test_engine_env_deptry.py` — `_check_engine_version` + `DeptryEngine.run` version-gate coverage, incl. the two review-pass regressions.
- `src/shared/packages/pyforge-warden/tests/conformance/test_osv_engine.py` — `OsvEngine.run` version-gate coverage incl. the skip-on-early-return regressions.
- `src/shared/packages/pyforge-warden/tests/unit/test_osv_engine_exit_codes.py` — existing exit-code fakes updated to answer the new `--version` pre-flight call.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `release_gates` row flipped `blocked` → `unblocked`.

**Review findings breakdown:** 2 patched (1 medium: unchecked `--version` exit code could let a broken engine install pass the gate on stale stdout content alone; 1 low: `FileNotFoundError` didn't disambiguate a vanished scan-target cwd from a missing binary), 0 deferred, 6 rejected as noise (TOCTOU between the two subprocess calls, `pixi.lock` not regenerated — verified already-compliant, banner-text-anchored regexes — fails safe by design, a hypothetical multi-line regex misparse — not demonstrated against real tool output, shared `ENGINE_TIMEOUT` kind — already message-distinguishable, and a release-gate recording concern — independently verified already correct).

**Follow-up review recommendation:** false — both patches are small, localized hardening of one new helper function with no behavior/API/schema impact beyond fail-closed precision; the adversarial and edge-case passes independently confirmed no false-green path exists anywhere in the new code.

**Verification:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` → 1869 passed (was 1867 pre-review, 1867+2 post-patch), 0 failed. `ruff check` on all touched files → clean.

**Residual risks:** none rising above the rejected-as-noise findings above; the engine-version-range choice is deliberately conservative (locked to the exact evidence-backed minor) and will need a routine follow-up story whenever conda-forge ships a new deptry/osv-scanner minor with fresh output-schema evidence.
