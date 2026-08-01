<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: '`doctor check` CLI wiring, `--json`, and the speed budget (FR-9, NFR-4)'
type: 'feature'
created: '2026-07-31'
status: 'done'
baseline_revision: 'cfd607b311a9d5c889a83503231194a8afce70b6'
final_revision: '70be54b8a3a7ac33585acf4f96702588a1f641c8'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json',
  '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py',
  '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
  '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md',
]
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Stories 1.2/1.3/1.4 built engine-availability, tri-state/filtering, and env-hygiene as library calls only — no CLI runs them together, no `--json` machine contract exists, and nothing guards the "five-second pre-flight" promise (PRD SM-C1) the whole `check` verb exists to deliver. Two prior review passes (spec-1-3, spec-1-4) explicitly deferred "how should the CLI expose a single named check when its whole category degrades" and "validate check names against the catalog or pass through" to this story.

**Approach:** Add a `check` subcommand to `__main__.py`'s existing parser (top-level `subparsers` becomes `required=True`, mirroring `pyforge-warden`) composing `sources.warden.gather`, `checks.env_hygiene.gather`, and `checks.registry` (catalog + single-check filter) into one human-readable-or-`--json` `DoctorReport`, exiting via `verdict.exit_code_for`, backed by a real end-to-end benchmark pinning a documented 5-second budget (measured today at ~2.1-2.5s against this monorepo).

## Boundaries & Constraints

**Always:**
- `check` composes Story 1.2/1.4's gather functions and Story 1.3's `registry.list_checks`/`gather_one` — never reimplements detection logic.
- Neither `--engines` nor `--env` given -> both run (FR-2); either given -> only the given categories run.
- `--engines`/`--env` take an optional check-NAME (`nargs="?"`, `const`=an internal "run whole category" sentinel). A NAME not in `registry.list_checks(category=...)` is an argparse usage error (`.error()`, exit 2) — resolves both prior stories' "validate vs pass through" deferral: validate, so a degradation-sentinel name (`pyforge-warden`/`env-hygiene`) is never directly requestable.
- Single-name dispatch is **category-aware** for a `None` result from `gather_one` (see Design Notes for why these differ): for `"engines"`, `None` for a validated name always means the category degraded to its sentinel (warden's gather is all-or-nothing) — render ONE synthetic `FAIL` `Finding(check=name, source=Source.WARDEN_DOCTOR)` explaining the degradation and pointing at an unfiltered `--engines` re-run, never a bare "not found", never a second `gather` call. For `"env"`, `None` legitimately means "clean, no match" (its gather is additive, never sentinel-replaced) — return zero Findings, no synthetic anything.
- `--json` emits exactly one `DoctorReport.to_json_dict()` document (`verb="check"`, no `prescriptions` key), self-validated via `jsonschema.validate` against the packaged `data/report-schema.json` before writing to stdout.
- Exit code is `verdict.exit_code_for(all_findings)` returned from `check`'s dispatch function — never a literal exit call outside `verdict.py`.
- `--list` prints `registry.list_checks()`'s full catalog as plain text and returns 0 without gathering/running anything (ignores `--engines`/`--env`/`--json`/`path`).
- `check` accepts an optional positional `path` (default `.`), forwarded verbatim as `target` to every gather call (mirrors warden's `scan <path>`); no extra target pre-validation — the gather functions already degrade safely on a bad path (see Design Notes).
- Top-level parser: `add_subparsers(dest="command", required=True)` (mirrors warden) — bare `doctor` is now a usage error, exit 2; Story 1.1's stub docstring already anticipated this.
- `doctor check --version` is a usage error (exit 2) — identical in shape to `warden scan --version` (verified live); `--version` stays top-level only. `doctor check --help` works for free via argparse's per-subparser help.
- A `BrokenPipeError` while writing stdout is absorbed (mirrors warden's `cli.py`), never a raw traceback.

**Block If:** none identified — every question the two prior stories deferred to this one was resolvable from cited precedent/live measurement (see Design Notes).

**Never:**
- Never modify `models.py`, `verdict.py`, `registry.py`'s dispatch semantics, `env_hygiene.py`'s detection logic, or `sources/warden.py`'s OK/FAIL mapping (frozen).
- Never re-run a category's gather twice in one invocation (the whole point of the speed budget).
- Never make `--list` gather/run anything or emit JSON (plain text only, v1 scope).
- Never narrow the default scanned target to make the benchmark pass artificially — the budget is documented and monitored, not gamed.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default combined run | `doctor check` at repo root, healthy env | Both categories' Findings, human summary, exit = `verdict.exit_code_for` | No error |
| JSON parity | `doctor check --json` | One schema-valid `DoctorReport` (`verb=check`, no `prescriptions`), every Finding present | No error |
| Single named check | `doctor check --engines osv-scanner` | Identical to full `--engines` suite filtered to that Finding (Story 1.3 AC3) | No error |
| Unknown check name | `doctor check --engines bogus-name` | Usage error, exit 2, names the bad value | Argparse `.error()`, never reaches `gather_one` |
| Degraded category + named check | warden absent/crashing, `--engines osv-scanner` | One synthetic `FAIL` Finding naming the degradation + re-run hint | No crash, no second gather |
| Clean env-hygiene, named check | No injection pattern present, `--env unconditional-credential-injection` | Zero Findings, exit 0 | No error (NOT treated as degradation) |
| List only | `doctor check --list` | Full catalog as text, exit 0, nothing gathered | No error |
| Bare invocation | `doctor` (no subcommand) | Usage error, exit 2 | Argparse `required=True` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- extend: top-level `subparsers` becomes `required=True`; add `check` subparser (`path` positional default `.`, `--engines`/`--env` `nargs="?"`, `--list`, `--json`); a `_run_check(args)` dispatch function; `datetime.now(UTC).isoformat()` for `generated_at`; `jsonschema.validate` self-check before `--json` emission; `BrokenPipeError`-safe stdout write (mirrors warden's `cli.py`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py` -- read-only reference: `list_checks`/`gather_one`, unmodified.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py` -- read-only reference: `gather`'s all-or-nothing sentinel shape, unmodified.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py` -- read-only reference: `gather`'s additive (never sentinel-replacing) shape, `CHECK_NAME`, unmodified.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py`, `models.py`, `data/report-schema.json` -- read-only references (`exit_code_for`, `DoctorReport`/`Finding`, packaged schema for self-validation).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` -- read-only reference: `_run_doctor`'s text/JSON rendering idiom, `required=True` subparser convention, `BrokenPipeError` absorption -- the cited precedent for matching "the convention warden's own CLI already established" (AC4).
- `src/shared/packages/pyforge-doctor/tests/unit/test_main_stub.py` -- update: bare-invocation assertion changes from `== 0` to a usage-error exit 2 (rename the test + refresh the module docstring, no longer a "stub"); `--version`/`--help`/`--bogus` assertions stay green unchanged.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` (NEW) -- covers every I/O-matrix row: default combined run, `--engines`/`--env` filters (incl. unknown-name usage error and the degraded-vs-clean asymmetry), `--list`, `--json` (schema-valid via `jsonschema`), `--version`/`--help` parity with warden, `path` positional forwarding.
- `src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py` (NEW) -- NFR-4 benchmark: real, unmocked end-to-end `doctor check` against the monorepo root (`Path(__file__).resolve().parents[N]`, mirroring the existing golden-fixture repo-root idiom, skipped outside a monorepo checkout), asserting completion within the documented 5-second budget.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- append one NEW entry: closes the two prior stories' "Story 1.5 CLI-wiring decision" items (record the argparse-catalog-validation + category-aware-synthetic-Finding resolution); notes `gather_one`'s first-match-only limit for multi-file "env" matches was weighed and deliberately left as-is (fixing it means redesigning frozen `gather_one` filter semantics, out of scope); notes single-name `--env` filtering cannot surface the category's incomplete-scan signal (a different, non-requested check name) — documented, not fixed.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- add `check` subcommand + `_run_check` dispatch, `required=True` top-level subparsers, `--json`/text rendering, `BrokenPipeError` guard -- realizes FR-9/NFR-4 end-to-end. (Implementation review caught and fixed one bug beyond the spec's explicit call-outs: `KeyboardInterrupt` during `_run_check` -- real multi-second gather work, this story's whole subject -- escaped `main()` uncaught; `_run_check`'s dispatch is now inside the same try/except as parsing, so it returns `EXIT_SIGINT` like every other interrupt path.)
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_main_stub.py` -- update the bare-invocation test + docstring for the new required-subcommand behavior; added `test_keyboard_interrupt_during_check_dispatch_returns_exit_sigint` regression test for the fix above.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` (NEW) -- full behavioral coverage of the I/O matrix above.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py` (NEW) -- real end-to-end timing assertion against the monorepo root.
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- append the one NEW entry closing/documenting the items above.

**Acceptance Criteria:**
- Given `doctor check` at repo root with no flags, when it runs, then both categories run, a human-readable summary prints, and the exit code equals `verdict.exit_code_for` over the combined Findings (epics AC1).
- Given `doctor check --json`, when it runs, then stdout is exactly one schema-valid `DoctorReport` (no info present in text absent from JSON) (epics AC2).
- Given a normal repository checkout, when `doctor check` is timed by the new benchmark test, then it completes within the documented 5-second budget (epics AC3).
- Given `doctor check --engines osv-scanner`, when it runs, then its result equals the full `--engines` suite filtered to that Finding (Story 1.3 AC3, reused here).
- Given `doctor check --engines bogus-name`, when it runs, then it is a usage error (exit 2) that never reaches `gather_one`.
- Given warden fully degraded and a named `--engines` check requested, when `gather_one` returns `None`, then the CLI renders one synthetic `FAIL` Finding naming the degradation, never a bare "not found".
- Given a clean tree and `--env unconditional-credential-injection`, when `gather_one` returns `None`, then the CLI reports zero Findings and exits 0 (not treated as failure).
- Given `doctor check --list`, when it runs, then it enumerates the full catalog as text and exits 0 without gathering anything.
- Given `doctor check --version`/`--help`, when run, then `--version` is a usage error (exit 2, matching `warden scan --version`) and `--help` exits 0 (epics AC4).
- Given bare `doctor` with no subcommand, when run, then it is a usage error, exit 2.

## Spec Change Log

## Review Triage Log

### 2026-07-31 — Review pass (follow-up, fresh pass on the done spec)
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 2, low 6)
- defer: 2: (medium 1, low 1)
- reject: 8: (low 8)
- addressed_findings:
  - `medium` `patch` A `SystemExit` raised INSIDE dispatch (a component calling bare `sys.exit()` during a gather — `SystemExit(None)`) fell into the argparse-mapping handler and returned **0**: a crashed run reporting success, the worst failure mode for a pre-flight gate. Warden's own `cli.py` (the convention this module cites, AC4) explicitly projects dispatch-raised `SystemExit` as an untrusted-code internal error. Fixed by nesting the argparse mapping around the parse/validate phase only and adding warden's sole-ownership containment (`→ 2` + stderr diagnostic) for dispatch-phase `SystemExit`; added `test_system_exit_during_check_dispatch_returns_two_never_its_own_code` (covers both `None` and `0` carried codes).
  - `medium` `patch` The last-resort `except Exception` net emitted only a one-line `{exc!r}` while claiming to mirror warden's — warden's net (cli.py:775) emits `traceback.format_exception(exc)` to stderr first, and Doctor's consumers are unattended loop agents whose only diagnostic surface is stderr, so a future `jsonschema.validate` self-check trip would have been an undiagnosable `ValidationError(...)` repr with no failing frame. Fixed by emitting the formatted traceback before the internal-error line, exactly as warden does (exit stays contained at 2, never the interpreter's uncaught-traceback exit 1); renamed/extended the regression test to pin both lines.
  - `low` `patch` `_emit_text` interpolated `finding.message` raw where warden's mirrored `_run_doctor` wraps every message in `_single_line` (warden's own Story 1.8 review finding) — env-hygiene messages embed scanned file paths verbatim, and a path legally containing `\n` would forge extra `[source] check: status` lines and desync the header's `N finding(s)` count. Added a local `_single_line` mirroring warden's `report.py` idiom; added `test_text_output_neutralizes_embedded_newlines_in_messages`.
  - `low` `patch` The path-ordering hint (added by the previous pass) had two edge defects: `--engines=` (empty NAME) hinted nonsense because `Path("")` normalizes to `Path(".")` which exists ("`''` looks like a path" + a double-spaced suggested command), and the suggested command interpolated the value raw so a path with whitespace/newlines produced an uncopyable suggestion. Fixed with a truthiness guard + `shlex.quote`; added `test_empty_check_name_is_usage_error_without_the_path_hint` and `test_path_hint_shell_quotes_a_path_containing_whitespace`.
  - `low` `patch` `_forbid_warden_gather`'s `AssertionError` sentinel was silently defused — `sources.warden.gather`'s `except Exception` degrade-never-crash net (verified live) swallows `AssertionError` into a FAIL Finding, so the five "never gathers" tests enforced nothing via the sentinel and a regression that gathered would have passed on secondary assertions alone. Fixed with a `BaseException` subclass (`_ForbiddenGatherError`), which `gather` deliberately lets through and `main()`'s handlers don't catch, so a forbidden gather now fails loudly.
  - `low` `patch` The NFR-4 benchmark could pass VACUOUSLY: it asserted only wall-clock + `exit in {0, 2}`, and a fully-degraded warden collapses the engines category to one instant sentinel Finding — "fast" and "broken-and-therefore-fast" were indistinguishable. Now each iteration parses the emitted header's findings count and asserts it ≥ the engines catalog size (warden's gather is all-or-nothing: healthy or engines-missing both yield every named check).
  - `low` `patch` The benchmark's module-level `Path(__file__).resolve().parents[6]` raised `IndexError` at collection time for a shallower-than-7-levels layout (e.g. an extracted sdist) — a collection ERROR for the whole file instead of the skip the docstring promises (the mirrored sibling idiom in `test_checks_env_hygiene.py` has the same latent hazard; left untouched there, out of this diff's scope). Guarded with try/except → `None` → skip.
  - `low` `patch` The two degradation shapes a machine (`--json`) consumer actually sees were untested at the CLI layer: the whole-category degraded-engines sentinel (`check == "pyforge-warden"` flowing through schema self-validation and `exit_code_for` → 2) and env-hygiene's incomplete-scan sentinel (`SCAN_INCOMPLETE_CHECK_NAME`, WARN, exit stays 0). Added `test_degraded_whole_engines_category_emits_schema_valid_sentinel_json` and `test_env_incomplete_scan_sentinel_flows_through_check_json` (trigger idiom mirrors `test_checks_env_hygiene.py`'s `_DISCOVERY_ENTRY_CAP` monkeypatch).
- deferred: `medium` — env-only run against a nonexistent/typo'd path false-greens (exit 0, "0 finding(s)"): root cause is Story 1.4's deliberate documented-empty non-dir case in `env_hygiene._discover_python_files` composed with this story's contract-mandated no-pre-validation forwarding; the default combined run does NOT false-green (warden FAILs on the bad path). Both candidate fixes (env_hygiene sentinel for non-dir targets, or a warden-style `_resolve_scan_target`) are frozen-surface or intent-contract changes outside this story's authority — ledgered for a product-level decision. `low` — the specific engines degradation reason (absent vs. unimportable vs. crashed — three deliberately distinct sentinel messages) is computed inside `gather_one` and discarded by its frozen first-match filter, so the named-check synthetic FAIL can only be generic + a re-run hint; joins the two existing spec-1-3 ledger entries flagging the same frozen filter contract from other directions.
- rejected: `low` (x8) — (1) sentinel names (`pyforge-warden`/`env-hygiene`) being unreachable via `--engines`/`--env` is the intent contract's explicit, deliberate decision ("never directly requestable"), and the usage error already lists the valid names, so the `[env-hygiene]`-source-label-vs-check-name confusion self-corrects in one step. (2) `--list` winning over `--json` with plain text on stdout is contract-mandated verbatim ("never emit JSON... ignores --json"), documented in help, and tested. (3) The `nargs="?"` grammar ambiguity was adjudicated by the previous pass (restructuring would contradict the spec's own positional-`path` convention); the residual "no hint when the path doesn't exist" case still names the known checks. (4) The benchmark's ~7s suite tax / no `slow` marker: the spec mandates a real unmocked benchmark in the unit suite and argues the iteration count in its own docstring; the headroom-shrink risk is already a ledger entry from the previous pass. (5) `mypy` `object`-sentinel typing: re-litigates the previous pass's rejection — still no mypy task/gate for this package. (6) Single-name `--env` dropping the INCOMPLETE sentinel: explicitly documented as a v1 boundary in this story's own prior ledger entry. (7) Catalog-vs-installed-warden drift misdiagnosing a healthy category as degraded: doctor and warden version in lockstep in this monorepo — speculative cross-version skew. (8) `_write_stdout` catching only `(OSError, ValueError)` (a `TypeError` from an exotic swapped-in stream double would escape to the net and replace the exit code): matches warden's deliberately-chosen exception set verbatim — the mirrored convention IS the spec'd behavior; the scenario has no live reproduction.

### 2026-07-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 3, low 2)
- defer: 1: (medium 1)
- reject: 4: (low 4)
- addressed_findings:
  - `medium` `patch` `--list` did not actually ignore an invalid `--engines`/`--env` check name despite its own help text promising "ignores --engines/--env/--json/path" — `_validate_check_names` ran unconditionally before `_run_check` ever checked `args.list`, so `doctor check --list --engines bogus-name` was itself a usage error instead of listing the catalog. Fixed by returning early from `_validate_check_names` when `args.list` is set; added `test_list_ignores_an_unknown_engines_check_name_and_a_path`.
  - `medium` `patch` `main()`'s try/except caught only `SystemExit`/`KeyboardInterrupt` — any other exception (e.g. a future schema/model drift tripping `_emit_json`'s `jsonschema.validate` self-check, or an unforeseen crash anywhere in `_run_check`) escaped uncaught, violating the module's own documented `{0, 2, 130}` exit-code domain (AD-2) and diverging from the exact sibling convention this story's own Design Notes cite (`pyforge-warden/cli.py`'s last-resort `except Exception` net). Added the same last-resort net, returning `2` with a stderr diagnostic, never a raw traceback; added `test_unexpected_exception_during_check_dispatch_returns_two_not_a_traceback`.
  - `medium` `patch` `--engines`/`--env`'s `nargs="?"` shape is structurally ambiguous with the adjacent bare positional `path` in argparse's own token matching (confirmed empirically, including via `parse_intermixed_args`, which does not resolve it either) — `doctor check --engines /some/dir` silently parses the path as the check NAME, producing a confusing "unknown check name" error with no hint at the real cause. Not restructured into a `--target` flag (would contradict this spec's own Design Notes, which explicitly justify mirroring warden's positional-`path` convention, and the ambiguity isn't hit by either PRD-named user journey UJ-1/UJ-2). Instead, `_validate_check_names`'s error message now detects when the rejected value is an existing path and appends a concrete ordering hint; added `test_unknown_check_name_that_is_also_a_real_path_hints_at_ordering`.
  - `low` `patch` `_write_stdout` did not guard `sys.stdout is None` (a detached/frozen process can legitimately have this) the way the sibling `_stderr` already guards `sys.stderr` — inconsistent within the same file. Added the same guard; added `test_write_stdout_does_not_crash_when_sys_stdout_is_none`.
  - `low` `patch` (found independently by this session's own implementation-verification pass, before the two review subagents ran): `KeyboardInterrupt` during `_run_check` — real multi-second gather work, this story's whole subject — escaped `main()` uncaught, since dispatch lived OUTSIDE the try/except that only wrapped `parser.parse_args`/`_validate_check_names`. Fixed by moving `return _run_check(args)` inside the same try; added `test_keyboard_interrupt_during_check_dispatch_returns_exit_sigint`.
- deferred: `medium` — the new NFR-4 benchmark's ~2x headroom (measured 2.6-2.7s per iteration during this review pass, up from 2.14-2.45s when the spec was drafted, consistent with organic repo growth) will shrink over time as the monorepo continues growing; the 5s figure itself (PRD SM-C1's own number, not invented) isn't wrong today, but the margin needs periodic re-measurement. Logged in `deferred-work.md` for a future recalibration/performance pass, not fixed here (no current test failure, no code defect).
- rejected: `low` (x4) — only the FIRST invalid check name surfaces when both `--engines` and `--env` are simultaneously bad (matches argparse's own single-error-at-a-time convention, not a defect). `mypy` flags 4 type errors from the `object`-typed `_WHOLE_CATEGORY` sentinel: no `mypy` task/gate exists for `pyforge-doctor` (confirmed via `pixi.toml`), zero current consequence. No `path`/target existence pre-validation before forwarding to gather functions: contradicts this spec's own Design Notes, which already verified live that both gather functions degrade safely (typed FAIL Finding / empty tuple) on a bad path — not a gap. Empty-catalog / empty-`known_names` cosmetic rendering: `checks.registry._CATALOG` is frozen and always non-empty today (2 categories); a hypothetical future empty state is speculative, out of this story's scope.

## Design Notes

**Why the `None`-handling is category-aware, not uniform.** `sources.warden.gather` is all-or-nothing: a healthy run always returns all 6 named Findings, so `gather_one`'s `None` for any cataloged engines name can ONLY mean total degradation to warden's sentinel — safe to treat uniformly as a failure. `checks.env_hygiene.gather` is additive: it returns zero-to-many real Findings PLUS, independently, an incomplete-scan sentinel when the walk itself had trouble — `gather_one`'s `None` there is the ordinary "nothing found" healthy outcome. Treating both categories the same would false-positive every clean env-hygiene scan into a fabricated failure. Only 2 categories exist today; a per-category dispatch `if` is simpler and more honest than a speculative shared abstraction (Epic 2's `monitor` verb gets its own CLI-wiring story, 2.3, to extend this if needed).

**Why no target pre-validation (unlike warden's ~40-line `_resolve_scan_target`).** Verified live: `sources.warden.gather(Path("/nonexistent"))` and `checks.env_hygiene.gather(Path("/nonexistent"))` both degrade safely today (typed FAIL Findings / empty tuple respectively, no exception) — the downstream gather functions already own this guarantee, so re-validating in the CLI would be a duplicated, unrequested code path.

**Why `--version` isn't added to the `check` subparser.** Verified live against `pyforge.warden.cli.main(["scan", "--version"])`: it is `unrecognized arguments: --version`, exit 2 (warden's `--version` lives only on its top-level parser). Mirroring that exactly is both the minimal-code answer (no new argument) and the literal "matches the convention warden's own CLI already established" (AC4).

**The 5-second budget.** PRD SM-C1 names "the five-second pre-flight promise" directly — this story adopts that exact, already-documented number rather than inventing a new one. Measured live against this monorepo's own worktree (897 `.py` files under the env-hygiene walk): 3 consecutive runs of `warden.gather` + `env_hygiene.gather` combined = 2.14s / 2.37s / 2.45s (engines ~0.13-0.21s, env-hygiene ~2.0-2.24s — the dominant cost, exactly the SM-C1 counter-metric risk). The budget carries genuine headroom (~2x) for slower CI hardware and repo growth without being vacuous, and — unlike warden's own orchestration-only `test_perf_overhead.py` (which stubs real engines to isolate code-level regressions) — this benchmark measures the REAL end-to-end promise unmocked, because Doctor's whole NFR-4 claim is about actual wall-clock, not internal overhead.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full unit + meta suite green, including the new CLI and speed-budget tests.
- `pixi run -e pyforge-doctor doctor check --json` -- manual smoke check once implemented: one schema-valid document on stdout.

## Auto Run Result

Status: done (follow-up review pass, 2026-07-31; orchestrator-invoked fresh pass on the already-done spec).

**Summary of implemented change:** No re-derivation — the shipped Story 1.5 implementation (`check` subcommand, `--json`, NFR-4 benchmark, commit `ce81c49086`) was independently re-reviewed by two fresh subagents (adversarial + edge-case). 18 unique findings after dedup; 0 intent_gap, 0 bad_spec, 8 patched, 2 deferred to the ledger as NEW entries, 8 rejected. All patches are hardening of this story's own surfaces (`__main__.py` + its three test files); nothing frozen was touched.

**Files changed (commit `70be54b8a3`):**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — dispatch-phase `SystemExit` contained as internal error 2 (was: fell into the argparse mapping, `SystemExit(None)` → 0 — a crashed run reporting success); last-resort net now emits the formatted traceback before the repr line (warden parity, stderr-only consumers); `_single_line` message neutralization in `_emit_text`; path-ordering hint hardened (empty-NAME truthiness guard + `shlex.quote`).
- `tests/unit/test_main_stub.py` — new dispatch-`SystemExit` regression test; internal-error test extended to pin the traceback emission.
- `tests/unit/test_cli_check.py` — `_ForbiddenGatherError(BaseException)` sentinel (the old `AssertionError` was silently swallowed by `gather`'s `except Exception` net); 5 new tests: degraded whole-engines `--json` sentinel shape, env incomplete-scan sentinel flow, empty-NAME hint suppression, whitespace-path hint quoting, newline-forgery neutralization.
- `tests/unit/test_check_speed_budget.py` — vacuous-pass guard (per-iteration findings count ≥ engines catalog size) + `parents[6]` collection-crash guard (IndexError → skip).

**Review findings breakdown:** 8 patched (2 medium, 6 low — all listed in the follow-up triage-log entry above), 2 deferred (env-only false-green on a nonexistent path — pre-existing Story 1.4 documented-empty boundary; engines degradation detail discarded by the frozen `gather_one` filter), 8 rejected (contract-mandated behaviors, previously-adjudicated items, and speculative scenarios — itemized in the triage log).

**Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` → 193 passed in 8.63s (was 187), including the benchmark's 3 real end-to-end runs against the monorepo root, all within the 5s budget with the new non-degenerate guard active. Working tree clean after commit.

**Residual risks:** the two ledgered defers (false-green env-only flow needs a product-level decision on target validation vs. an env_hygiene sentinel; the generic synthetic degradation message is bounded by Story 1.3's frozen filter contract). The benchmark's shrinking headroom remains under watch via the previous pass's ledger entry.

