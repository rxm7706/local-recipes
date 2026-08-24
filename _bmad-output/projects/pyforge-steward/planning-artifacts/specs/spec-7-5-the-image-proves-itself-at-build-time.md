---
title: 'Story 7.5: The image proves itself at build time'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '73391d567255fa1b9ff7fbbddc8700fbf902097e'
final_revision: 'e0614e74f7b7c6f4e1149ee145644730c1465b9f'
---

<intent-contract>

## Intent

**Problem:** No build-time gate proves the eight station CLIs actually work inside the exact composed `pyforge-container` env the image ships — Story 7.1's "each answers `--version`" was only ever checked by hand during review passes, and a real, already-observed risk exists: `pyforge-container` resolves a different package set than any per-station test env (e.g. `dagster` 1.13.17 vs. the 1.13.16 tested under `pyforge-atlas`), so an import break there is invisible until a later `docker run` (deferred-work: "Adding a container-env gate is Story 7.5's build-time smoke-gate scope").

**Approach:** Add a `cli-smoke` subcommand to `scripts/container-gates` (duty-agnostic, like `secrets-scan`/`volumes-roundtrip`: it takes `--cli "<cmd> --help"` pairs, not a hardcoded station list) and wire one `RUN` step into the Containerfile's final stage invoking it for all eight real station CLIs with `--help` — reliable across CLIs (unlike `--version`, which `marshal`'s own pixi smoke task documents as "always exits 0 ... never a gate"), with a documented per-CLI timeout as the start-up budget.

## Boundaries & Constraints

**Always:**
- `cli-smoke` stays duty-agnostic (AD-2 delegation-purity): each `--cli` value is a full invocation string (`shlex.split`, no shell), so the script has no station-name list baked into its logic — only the Containerfile `RUN` line names the real eight.
- Every subprocess call gets an explicit timeout (the documented start-up budget) and clean stderr on `FileNotFoundError`/nonzero-exit/timeout — never a raw traceback, mirroring `_scan_target`/`_roundtrip_mount`'s doctrine in this same script.
- Never short-circuits across multiple `--cli` values; aggregates and reports every failure.
- The gate is a plain Containerfile `RUN` step (like Story 7.3's), so a finding fails `docker build`/`podman build` itself, not a later `docker run`.
- The eight `--cli` invocations use `--help`, not `--version` (marshal's own `pyforge-marshal-smoke` task already documents why `--version` alone is not a reliable gate for that station).

**Block If:** a live `docker build` shows `--help` does not reliably exit non-zero for a real broken/unimportable station in this repo's actual images — HALT and report rather than reworking the invocation choice unattended.

**Never:**
- No change to any station's own CLI code — this story gates the existing `--help` behavior, it does not add one.
- No CI wiring (matches Stories 7.3/7.4's precedent).
- No per-station budget tuning — one documented constant applies to all eight; splitting is unwarranted absent evidence any station is structurally slower.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, one CLI | `--cli "true"` (or any exit-0 command) | Reports OK; exit 0 | No error |
| Happy path, all eight real stations | `--cli "marshal --help" --cli "steward --help" ...` (all 8) | All report OK; exit 0 only if ALL pass | Per-CLI diagnostics on any failure |
| Missing binary | `--cli "does-not-exist --help"` | `FileNotFoundError` caught | Clean stderr naming the binary; exit 1; never a raw traceback |
| Unimportable / broken CLI | `--cli` pointing at a script that exits non-zero | Reported as a failure naming the exit code + stderr tail | Exit 1; other `--cli` entries still attempted |
| Over start-up budget | `--cli` pointing at a script that sleeps past the timeout | `TimeoutExpired` caught, process killed | Clean stderr naming the budget; exit 1 |
| One of several fails, others pass | Three `--cli`, one broken | All three still attempted (no short-circuit) | Aggregate exit 1; each CLI's own pass/fail line printed |
| Malformed `--cli` value | Unbalanced quoting, or empty string | `shlex.split` `ValueError` / empty argv caught upfront | Clean stderr naming the bad value; exit 1 |

</intent-contract>

## Code Map

- `scripts/container-gates` -- EDIT: add `cli-smoke` subcommand (`--cli "<cmd> ..."`, repeatable) — per-invocation subprocess with a documented timeout budget, aggregate never-short-circuit verdict, mirrors `secrets-scan`/`volumes-roundtrip`'s error-handling doctrine
- `Containerfile` -- EDIT: add a `RUN` step in the final stage, after the Story 7.3 secrets-scan gate and before the Story 7.4 `VOLUME` line, invoking `container-gates cli-smoke` with all eight real station CLIs' `--help`
- `tests/scripts/test_container_cli_smoke.py` -- NEW: full I/O matrix against synthetic fixture scripts (no real station binary or docker needed — pure stdlib, picked up by the existing `pyforge-doctor-scripts-test` sweep of `tests/scripts/`)

## Tasks & Acceptance

**Execution:**
- [x] `scripts/container-gates` -- `cli-smoke` subcommand: `--cli CMD` (repeatable, `shlex.split` each value, argv[0] is the display name); a module-level `_CLI_SMOKE_TIMEOUT_SECONDS` constant (documented budget, with the real measured evidence: all eight real stations' `--help` completed in well under 1s including `docker run` overhead); `FileNotFoundError`/non-zero-exit/`TimeoutExpired`/`ValueError` all become clean stderr diagnostics, never a raw traceback; never short-circuits
- [x] `Containerfile` -- add the `cli-smoke` `RUN` step naming all eight real console scripts (`marshal`, `steward`, `pyforge-atlas`, `warden`, `doctor`, `mason`, `herald`, `scribe`) with `--help`
- [x] `tests/scripts/test_container_cli_smoke.py` -- one test per I/O-matrix row using synthetic fixture scripts under `tmp_path`

**Acceptance Criteria:**
- Given the built guild image with the `cli-smoke` gate wired in, when `docker build -f Containerfile` runs against the unmodified repo, then the build succeeds and the gate reports all eight stations OK.
- Given a scratch copy of the Containerfile with one extra `--cli "does-not-exist --help"` appended to the same `RUN` line, when `docker build` runs against it, then the build FAILS at that `RUN` step with a clear message naming the missing binary — proving the gate really fails the build, not a later run.
- Given `cli-smoke` invoked directly against a script that sleeps past `_CLI_SMOKE_TIMEOUT_SECONDS`, then it fails cleanly (clear stderr naming the budget, non-zero exit) — never a raw traceback.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 3
- reject: 3
- addressed_findings:
  - `medium` `patch` `_check_cli`'s `subprocess.run` call only caught `FileNotFoundError`/`subprocess.TimeoutExpired` -- a non-executable/permission-denied target (`PermissionError`) or a `--cli` argv `subprocess.run` itself rejects (e.g. an embedded NUL byte, raising `ValueError`) would have escaped as a raw traceback, violating this same script's "never a raw traceback" doctrine (mirrors `_roundtrip_mount`'s identical, already-fixed 7.4 gap). Independently flagged by both reviewers. Fixed: added `except (OSError, ValueError)` after the existing specific handlers. Verified live with a new test (`test_non_executable_target_fails_cleanly_not_with_a_raw_traceback`).
  - `medium` `patch` A CLI that exits non-zero with empty stderr printed a bare `exited N: ` with no diagnostic content, and a CLI that explained its failure on stdout (not stderr) produced the identical empty-looking tail -- both flagged independently by both reviewers as a real triage-blocker for whoever reads a failed build log. Fixed: falls back to the stdout tail, then a `(no output captured)` placeholder, when stderr is empty. Verified live with two new tests.
  - `low` `patch` The `[-5:]` stderr-tail truncation had no test emitting more than one line, so the slicing logic itself had never been exercised. Fixed: added `test_broken_cli_with_long_stderr_reports_only_the_last_five_lines` (7 lines in, asserts only the last 5 survive).
  - `low` `patch` `cmd_cli_smoke`'s own timeout parameter-threading into `_check_cli` (the actual path `main()` takes) had no test of its own -- the existing timeout row called `_check_cli` directly, bypassing `cmd_cli_smoke` entirely. Fixed: added `test_cmd_cli_smoke_threads_its_timeout_override_to_every_check`, calling `cmd_cli_smoke` itself with a tiny override.
  - `low` `patch` The `_CLI_SMOKE_TIMEOUT_SECONDS` rationale comment's "~15x the slowest observed sample" measured a strictly slower proxy (`docker run --rm <image> <cli> --help`, including full container-startup overhead) than the code path it actually bounds (a bare in-container `subprocess.run`) -- not wrong, but imprecise about which path was measured. Fixed: reworded to state the multiplier is a floor on the real margin, not a precise ratio, and that the true in-container cost is lower still.
  - `defer` "SPEC.md's CAP-5 still names `steward provision --verify` as part of the gate; this story's implementation omits it" -- real: the canonical, more-recently-updated `epics.md`/PRD FR-26 (2026-08-02) narrowed the AC to exactly what this story implements and omits `provision --verify` entirely, so the implementation is correct against the canonical text, but SPEC.md itself was never updated to record that narrowing. Logged to `deferred-work.md`, owner `spec-unified-container`'s memlog reconciliation.
  - `defer` "The eight-station list is hand-duplicated between `pixi.toml`'s `pyforge-container` composition and the Containerfile's `cli-smoke` `RUN` line, with nothing tying them together" -- real, but matches this repo's already-accepted precedent (`secrets-scan`'s explicit root list, `volumes-roundtrip`'s explicit mount list) rather than a gap this story introduced. Logged to `deferred-work.md`.
  - `defer` "No test in any of the three container-gates stories (7.3/7.4/7.5) parses the actual Containerfile to confirm its gate `RUN`/`VOLUME` line is still present" -- real and pre-existing since Story 7.3, surfaced incidentally by this pass rather than caused by it. Logged to `deferred-work.md`.
  - `reject` "No CI wiring" -- already an explicit, named non-goal in this story's own spec, matching Stories 7.3/7.4's precedent.
  - `reject` "`--help` cannot catch a hypothetical lazy import inside a subcommand handler (vs. module-level import)" -- the reviewer raising it explicitly confirmed live that no station has this pattern today; speculative, and inherent to every `--help`/`--version`-based smoke check in this repo (including the pre-existing `pyforge-marshal-smoke` pixi task), not something this diff introduces or narrows.
  - `reject` "The timeout test's direct-import technique (`_load_container_gates`/`SourceFileLoader`) differs stylistically from the black-box, subprocess-only sibling test files" -- a reasonable, already-documented (in the test file's own docstring) engineering judgment call to keep that one test fast; no functional defect.

## Design Notes

**Why `--help`, not `--version`.** `pixi.toml`'s own `pyforge-marshal-smoke` task documents that `marshal --version` "always exits 0 (informational, never a gate)", so grepping its stdout is the only reliable check for that one station. `--help` sidesteps this uniformly: argparse's `-h/--help` handling requires the parser (and therefore every subcommand-defining import) to have built successfully, and it exits non-zero on failure for all eight stations without any station-specific output parsing — confirmed live (`docker run --rm <image> <cli> --help`, all eight rc 0, each printing its own `usage: <name> ...` banner). This also matches SPEC.md's CAP-5 wording ("each station CLI's `--help`") more precisely than the epic summary's `--version`-flavored framing. **Scope narrowing, recorded explicitly (review-pass finding):** CAP-5's own text additionally names `steward provision --verify` as part of the gate; the canonical, more-recently-updated `epics.md`/PRD FR-26 (2026-08-02) dropped that clause and narrowed the AC to exactly the `--help` + start-up-budget contract this story implements. This story follows the canonical, newer text deliberately — SPEC.md itself is unreconciled and logged to `deferred-work.md`.

**The budget number.** Measured live against a real built guild image: all eight stations' `docker run --rm <image> <cli> --help` completed between 0.31s and 0.74s, including full `docker run` container-startup overhead (the in-container-only cost, e.g. a plain subprocess call as this gate makes, is lower still). A documented constant of several seconds per CLI is generous (~10-20x observed) without being a meaningless hang-guard.

**No dedicated pixi task.** Unlike `secrets-scan`/`volumes-roundtrip` (each needed a *real* `steward`/`docker` binary, hence a dedicated `pyforge-steward-container-*-test` task so the generic `pyforge-doctor-scripts-test` sweep of `tests/scripts/` wouldn't just skip them), `cli-smoke`'s own test suite uses only synthetic fixture scripts and the stdlib `container-gates` script itself — the existing sweep already runs it for real with no skip condition, so a second dedicated task would add a name, not coverage.

## Verification

**Commands:**
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test` -- expected: new `cli-smoke` tests pass (collected via the existing `tests/scripts` sweep)
- `docker build -f Containerfile -t pyforge-guild-7-5-check .` -- expected: succeeds; the `cli-smoke` `RUN` step reports all eight stations OK
- A scratch Containerfile copy with a ninth, bogus `--cli` appended to the same `RUN` line, built with `-f <scratch>` -- expected: `docker build` FAILS at that step, never silently passes; scratch file discarded, not committed
- `python3 -m py_compile scripts/container-gates` -- expected: clean

**Manual checks (if no CLI):**
- Confirm the new `RUN` step sits after the Story 7.3 secrets-scan gate and before the Story 7.4 `VOLUME` line (per that line's own "add new RUN/COPY steps ABOVE this line" instruction).

## Auto Run Result

Status: done

Commit: `e0614e74f7b7c6f4e1149ee145644730c1465b9f` on `bmad-loop/20260809-114839-7af9/7-5-the-image-proves-itself-at-build-time` (baseline `73391d567255fa1b9ff7fbbddc8700fbf902097e`). Not pushed.

**Implemented:** CAP-5's first real implementation. `scripts/container-gates` gained a `cli-smoke` subcommand — duty-agnostic like `secrets-scan`/`volumes-roundtrip` (each `--cli` value is a full invocation string, `shlex.split`'d and run with no shell, so the script itself carries no station-name list). `Containerfile` gained a new `RUN` step (after Story 7.3's secrets-scan gate, before Story 7.4's `VOLUME` line) invoking `cli-smoke --help` against all eight real station CLIs — a failure here fails `docker build`/`podman build` itself, never a later `docker run`. This closes a real, previously-flagged gap: `pyforge-container`'s composed package resolution differs from any single per-station test env (e.g. `dagster` 1.13.17 vs. 1.13.16), so an import break there was invisible until manual inspection; a Story 7.1 deferred-work entry named this exact gap as "Story 7.5's build-time smoke-gate scope." `tests/scripts/test_container_cli_smoke.py` is new, covers every I/O-matrix row with synthetic `tmp_path` fixtures (no real station binary or Docker required), and rides the existing `pyforge-doctor-scripts-test` sweep with no dedicated pixi task added (a deliberate simplification recorded in Design Notes — unlike `secrets-scan`/`volumes-roundtrip`, this gate's own test suite never needs a real binary the generic sweep would otherwise skip).

**Files changed:** `Containerfile` (new RUN step), `scripts/container-gates` (new `cli-smoke` subcommand + docstring update), `tests/scripts/test_container_cli_smoke.py` (new, 13 tests), `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container/.memlog.md` (reconciliation entry naming both governed files), `scripts/.spec-surface-baseline.json` (re-stamped for this spec).

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, run independently with no shared context): 11 deduplicated findings — 0 intent_gap, 0 bad_spec, 5 patch (2 medium: `_check_cli`'s exception handling didn't catch `PermissionError`/`IsADirectoryError`/a `ValueError` from `subprocess.run` itself, an unhandled-traceback path independently flagged by both reviewers and mirroring `_roundtrip_mount`'s identical, already-fixed 7.4 gap; and a non-zero exit with empty stderr — or a CLI explaining itself on stdout instead — printed a bare, undiagnostic `exited N: `, also flagged independently by both reviewers; 3 low: the `[-5:]` stderr-tail truncation had no multi-line test, `cmd_cli_smoke`'s own timeout-parameter threading had no test going through that function itself, and the timeout-budget rationale comment measured a slower proxy path than the code it actually bounds), 3 defer (SPEC.md's CAP-5 text still names `steward provision --verify`, which the canonical, newer `epics.md`/PRD FR-26 already dropped — implementation follows the canonical text, SPEC.md itself is unreconciled; the eight-station list is hand-duplicated between `pixi.toml` and the Containerfile `RUN` line with no automated tie, matching pre-existing sibling-gate precedent; no container-gates story's test suite parses the Containerfile itself to confirm a gate line survives future edits), 3 reject (no-CI-wiring is an already-named non-goal; a hypothetical lazy-import-inside-a-handler gap the raising reviewer confirmed has no live instance today; a test-technique style preference with no functional defect). All 5 patches applied and re-verified live before this pass closed.

**Follow-up review recommendation: false.** All five patches are narrowly scoped (widened exception handling in one function, a diagnostic-fallback improvement, three additive tests, one comment reword) and don't change the gate's detection semantics (still: missing, non-zero exit, or timeout = failure) or its Containerfile wiring; each was independently re-verified end-to-end after applying, not just re-inspected.

**Verification performed:** `python3 -m py_compile scripts/container-gates` (clean, both before and after the review-pass patches); `pixi run -e pyforge-ci pyforge-doctor-scripts-test` (26 passed / 8 pre-existing skips, up from 21 passed before this story's 5 new post-review tests — all 13 `cli-smoke` tests green); a real `docker build -f Containerfile` succeeded with the `cli-smoke` `RUN` step reporting all eight real stations (`marshal`, `steward`, `pyforge-atlas`, `warden`, `doctor`, `mason`, `herald`, `scribe`) OK, re-confirmed after the review-pass patches with the built image's own `scripts/container-gates` content inspected directly; a negative-path scratch-Containerfile build with a ninth, bogus `--cli "does-not-exist-binary --help"` appended failed exactly at that `RUN` step with a clean message naming the missing binary (no traceback, no image produced) — scratch file and every throwaway image removed afterward, confirmed via `git status`/`docker images`; `python3 scripts/spec_surface_check.py` and `pixi run -e local-recipes spec-surface-check` both clean after the memlog reconciliation + baseline re-stamp.

**Residual risks:** the three deferred findings above are low-severity and logged to `deferred-work.md`; none are blocking. SPEC.md's own CAP-5 text (`steward provision --verify`) remains unreconciled against the canonical epics.md/PRD narrowing — a documentation gap, not a functional one, and out of this story's authority to resolve unilaterally (the fix is a `spec-unified-container` SPEC.md edit, a planning-artifact change beyond a single story's scope).

**Finalized:** 2026-08-09. All HALT-protocol steps complete (status `done`, `final_revision` recorded).
