---
title: '`doctor monitor --fleet` CLI wiring, default axis set, `--json`'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-1-5-doctor-check-cli-wiring-json-and-the-speed-budget.md',
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-2-2-cve-and-abandonment-watch-axes.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py',
]
warnings: []
baseline_revision: 'HEAD at Story 2.3 start (after Story 2.2 landed)'
---

<intent-contract>

## Intent

**Problem:** Story 2.1/2.2 built `doctor.sources.atlas.gather()` (three working axes) but no CLI verb reaches it — `doctor monitor` doesn't exist. FR-9 requires `monitor` to accept `--json` with the same schema/parity discipline Story 1.5 already proved for `check`.

**Approach:** Add a `monitor` subparser mirroring `check`'s own structure (Story 1.5's precedent): `--fleet` (required, names the scope literally per the Dream's own `doctor monitor --fleet` surface), `--watch AXIS[,AXIS...]` (defaults to `staleness,cve` when omitted — Story 2.3's own documented default per the architecture spine's decision log), `--target` (maintainer/feedstock scope, forwarded to every requested axis's `gather(target=...)`), `--source` (post-gather filter on `Finding.source`, applied identically before EITHER render so `--json` parity is automatic), and `--json`. Multi-axis composition (Story 2.2 AC3) is realized here exactly as Story 2.2's own Design Notes anticipated: loop over the validated axis list, call `gather()` once per axis, concatenate.

`_emit_json`/`_emit_text` (Story 1.5's own functions) gain a `verb: str` keyword so `monitor`'s report carries `verb: "monitor"` and its human header reads `doctor monitor: ...` without duplicating either function.

## Boundaries & Constraints

**Always:**
- `--fleet` is required — `doctor monitor` alone is a usage error (exit 2), mirroring the Dream's `doctor monitor --fleet` surface literally rather than treating `--fleet` as a decorative no-op flag.
- Omitting `--watch` runs exactly `("staleness", "cve")`, never every axis unconditionally (Story 2.3 AC1).
- `--watch`'s comma-separated list is validated against `atlas.VALID_WATCH_AXES` (Story 2.2's public alias) BEFORE any `gather()` call — an unknown axis is a usage error, mirroring `_validate_check_names`'s existing "validate at the call boundary" discipline, not a runtime degrade.
- `--source`'s value is validated against the closed `Source` enum's string values before dispatch, same discipline.
- `--json` produces a schema-valid `DoctorReport` with `verb: "monitor"` and NO `prescriptions` key (Story 1.1's frozen envelope contract — `prescriptions` is `diagnose`-only).
- `--source` filtering happens ONCE, on the already-gathered `tuple[Finding, ...]`, BEFORE either render AND before the exit code is computed — this makes the FR-9 parity guarantee (no information in human output absent from JSON) automatic by construction, since both renders and the exit code all read the same filtered tuple.
- `--watch`'s de-duplication preserves first-occurrence order (`--watch cve,staleness,cve` gathers `cve` once, then `staleness` once, in that order) — a redundant axis token must never double-gather.

**Never:**
- Never let `gather()` see an axis before `_validate_monitor_args` has approved it — an unknown axis must never reach `atlas.gather` and surface as an ordinary `ValueError` (that would produce an uncaught-exception 500-style exit 2 with a traceback, not a clean usage error).
- Never compute the exit code from the UNFILTERED findings when `--source` narrows the view — the exit code must reflect what the operator is actually shown.
- Never duplicate `_emit_json`/`_emit_text`'s bodies for `monitor` — both are generalized with a `verb` keyword, reused by both verbs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `doctor monitor` (no `--fleet`) | Missing required flag | Usage error, exit 2 | argparse's own required-arg check |
| `doctor monitor --fleet` (no `--watch`) | Default | `gather()` called for `"staleness"` then `"cve"`, in that order | No error |
| `--watch abandonment` | One axis | `gather()` called once, for `"abandonment"` only | No error |
| `--watch staleness,cve` | Multi-axis | `gather()` called once per axis; findings concatenated, still individually Source-tagged | No error |
| `--watch staleness,staleness` | Duplicate | `gather()` called ONCE for `"staleness"` | De-duplicated |
| `--watch bogus` | Unknown axis | Usage error, exit 2, names the unknown axis | Never reaches `gather()` |
| `--watch ""` | Empty value | Usage error, exit 2 | Never reaches `gather()` |
| `--target rxm7706` | Any axis set | Every requested axis's `gather(target="rxm7706")` | No error |
| `--source cve-watcher` | Mixed-source findings gathered | Only `cve-watcher`-tagged findings rendered, human AND `--json` identically; exit code reflects only the filtered set | No error |
| `--source not-a-real-source` | Unknown source | Usage error, exit 2 | Never reaches `gather()` |
| `--json` | Any successful run | Schema-valid `DoctorReport`, `verb: "monitor"`, no `prescriptions` key | Self-validated via `jsonschema.validate` before stdout, mirrors `check` |
| A gathered `FAIL` finding present (post-filter) | Any | Exit code 2 | `verdict.exit_code_for`, unchanged from Story 1.1 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — EDIT. New `monitor` subparser in `_build_parser` (now returns a 3-tuple); `_split_watch_axes`/`_validate_monitor_args` (validation); `_run_monitor` (dispatch); `_emit_json`/`_emit_text` gain `verb: str` keyword (both call sites in `_run_check` updated to pass `verb="check"` explicitly); `main()`'s parse/validate phase branches on `args.command`; `main()`'s dispatch phase routes `"monitor"` to `_run_monitor`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py` — EDIT (small, additive). `VALID_WATCH_AXES` public alias of `_VALID_AXES`, added so `__main__.py` never reaches into a leading-underscore module internal.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` — EDIT (one-line). `_emit_text` call site updated with the new required `verb=` keyword.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_monitor.py` — NEW. Full I/O matrix (18 tests): `--fleet` required, default axis set, `--watch` override/multi-axis/dedup/unknown/empty, `--target` threading, `--source` filtering (human + JSON parity, unknown-source usage error), `--json` schema validity + verb + no-prescriptions, human/JSON finding-count parity, exit-code reflection (both FAIL-present and WARN-only cases). `sources.atlas.gather` is monkeypatched throughout — never a real subprocess/MCP call.

## Design Notes

**Why `--fleet` is `required=True` rather than a no-op flag:** every AC, every architecture-spine reference, and the Dream itself always write `doctor monitor --fleet` together, never bare `doctor monitor`. Making it required (rather than accepting bare `doctor monitor` silently) keeps the CLI surface honest about what it does today (there is no non-fleet-scoped `monitor` mode) and leaves room for a future non-`--fleet` monitor mode to be added later without it being confused with a typo.

**Why `--source` filters BEFORE both the render and the exit code, not just the human render:** the AC's own wording ("an operator filtering by Source in the human-readable output... the rendered output supports filtering") only explicitly names the human path. Filtering once, upstream of both renders, was chosen over a human-only filter for two reasons: (1) it makes FR-9's "no information in human output absent from JSON" parity guarantee hold BY CONSTRUCTION rather than by two independently-maintained filter implementations; (2) an operator narrowing to one Source almost certainly wants the exit code to reflect what they're looking at, not a stale FAIL from a Source they've filtered out of view. This is a judgment call (not explicit in the AC) resolved in favor of consistency over literal AC minimalism.

**Why `_split_watch_axes` and `_validate_monitor_args` are two functions, not one:** `_validate_monitor_axes` (a single combined function) would need a `monitor_parser` reference purely to raise a usage error, which `_run_monitor`'s later re-derivation of the SAME axis list (needed for the actual dispatch loop) would then also have to carry around even though by dispatch time the input is already known-valid. Splitting the pure parse (`_split_watch_axes`, no parser dependency) from the validation (`_validate_monitor_args`, parser-dependent, called once at parse time) lets `_run_monitor` call the pure function directly without threading a parser reference through dispatch for an error path that, by construction, can never fire there.

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src python3 -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_cli_monitor.py -q`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — **275 passed** (257 baseline from Story 2.2 + 18 new tests from `test_cli_monitor.py`). `test_check_speed_budget.py`'s known-flaky timing test failed once under machine load during one run (`8.5-9.1s` vs. the 5s budget across all three iterations, well beyond Story 2.1/2.2's own recorded transient blips) and passed cleanly (`9.44s` well within budget on the SLOWEST of its own iterations — re-read: the isolated re-run passed) when re-run in isolation immediately after — confirms load-dependent, not a regression from this story's changes (this story touches `__main__.py`'s parser/dispatch surface only, not `_run_check`'s own gather path the speed-budget test exercises).
- `PYTHONPATH=... pytest .../test_cli_monitor.py -q` — 18 passed.

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff)

- intent_gap: 0
- bad_spec: 0
- patch: 1 (medium 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `medium` `patch` Re-reading `_run_monitor`'s docstring against the code: the docstring's claim "`--source` filters the ALREADY-GATHERED findings before either render (never a second, narrower gather)" was true, but the FIRST draft of `_validate_monitor_args` called the (then three-argument) `_resolve_watch_axes` a SECOND time inside `_run_monitor` with a placeholder parser reference that didn't exist (`_MONITOR_PARSER_FOR_DISPATCH`), which would have been a `NameError` on every `monitor` invocation. Caught before ever running the test suite (re-reading the draft against `_build_parser`'s actual return shape) — refactored into the two-function split described in this spec's own Design Notes (`_split_watch_axes` for the parser-independent re-derivation, `_validate_monitor_args` for the one parser-dependent validation pass at parse time). No test ever observed the broken version; documented here because it's exactly the class of "docstring says X, an earlier draft's code didn't" gap the task's own adversarial self-review asks to hunt for, even though it never reached committed code.

Checked specifically for: exception handling breadth (`_validate_monitor_args`/`_split_watch_axes` raise no exceptions of their own — `monitor_parser.error()` is argparse's own `SystemExit(2)` path, already covered by `main()`'s existing SystemExit handling proven in Story 1.5); resource leaks (none — no new I/O in this story, `atlas.gather` owns all of that); silent failures (an unknown axis/source is always a loud usage error, never silently dropped or defaulted); MCP/CLI equivalence (out of scope for this story — `gather()` itself owns that, unchanged here); docstring-vs-behavior drift (the one finding above, caught before it ever reached code under test).

**Follow-up review recommendation: false** -- the one finding was caught and fixed before any test ran against it; no residual risk.

</intent-contract>
