---
title: 'Gate report interface'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '64e717d13554938e03ceac5a6a98c2aae407b957'
final_revision: 'c47a46d1b7'
---

<intent-contract>

## Intent

**Problem:** Herald's deck pipeline has no shared, extensible way for visual-QA gates (a
future headless-render gate, an image-slot scan, and three parked `.pptx`-contingent gates)
to report findings — nothing proves a machine-readable report round-trips or that a new gate
id slots in without reworking the schema, the entrypoint, or a consumer.

**Approach:** Add `src/pyforge/herald/deck_qa.py` defining a JSON-round-trippable report
schema keyed by gate id, an `run()` entrypoint that executes a caller-supplied gate mapping
(starts empty — the real gates land in Stories 14.2/14.3) without ever aborting on one gate's
failure, and wire it to a new `herald deck qa <slug>` CLI subcommand alongside the existing
`deck` subcommand family — resolving the Spec's entrypoint-placement open question.

## Boundaries & Constraints

**Always:**
- Report-only: `deck_qa.run` never mutates deck sources and never triggers a rebuild.
- Report JSON shape: `{"slug": str, "gates": {<gate_id>: {"status": "ok"|"error", "findings":
  [{"slide_id": str, "message": str}, ...], "artifacts": [str, ...], "error": str|None}}}`.
  `to_dict(report)` / `parse_report(data)` round-trip it; `parse_report` rejects any
  missing/unrecognized field or bad `status` value by raising `errors.HeraldError` (mirrors
  `state.py`'s AD-6 strictness — no silently-dropped typo).
- Gates are a `Mapping[str, GateFn]` (`GateFn = Callable[[GateContext], GateResult]`) passed
  into `run()`; `GateContext` carries `slug` + `repo_root` only (14.2/14.3 may extend it —
  they edit this same file). `DEFAULT_GATES: dict[str, GateFn] = {}` ships empty in this story.
- A gate function that raises is caught per-gate inside `run()`, becomes that gate's own
  `status="error"` result (message in `error`), and never aborts the whole report or the
  other gates.
- `herald deck qa <slug> [--repo-root PATH]` joins the existing `deck` subparser family
  (matches `seed`/`pull`/`status`/`watch`/`push`'s `slug` + `--repo-root` shape). `_run_deck_qa`
  builds a `GateContext`, calls `deck_qa.run(...)`, and prints `json.dumps(to_dict(report))` as
  the whole stdout output (mirrors `_run_deck_status`'s "the report IS the output" convention),
  through the existing `dispatch()` boundary. No `McpTransport`/`bridge.run` — this is local-only,
  unlike the Design-sync deck subcommands.

**Never:**
- No real gates in this story — `DEFAULT_GATES` ships empty; 14.2/14.3 populate it later.
- No new dependency (no playwright/browser code here at all).
- No persisted report file — stdout only; 14.2 decides where PNGs/contact sheets live.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Zero gates | `herald deck qa x` with `DEFAULT_GATES={}` | prints `{"slug":"x","gates":{}}` | No error |
| Two gates, one flags | `gates={"a": ok_fn, "b": finding_fn}` | both keys present; `b`'s findings non-empty | No error |
| A gate raises | `gates={"boom": raising_fn}` | `gates["boom"]` has `status:"error"` + message; other gates unaffected | `run()` itself does not raise |
| Round trip | any built `DeckQaReport` | `parse_report(json.loads(json.dumps(to_dict(r))))` equals `r` | No error |
| Malformed input | dict missing `"gates"` or with an unknown key | `parse_report` raises | `errors.HeraldError` |
| Third gate added | same test's `gates` mapping grows a 3rd key | report gains a 3rd top-level key; zero other code touched | No error |

</intent-contract>

## Code Map

- `src/pyforge/herald/deck_qa.py` -- new: `Finding`, `GateResult`, `DeckQaReport`, `GateContext`
  dataclasses, `GateFn` alias, `DEFAULT_GATES`, `run()`, `to_dict()`, `parse_report()`.
- `src/pyforge/herald/cli.py` -- `deck_subparsers` (after `push`) and `_route`; new
  `_run_deck_qa`, mirroring `_run_deck_status`'s shape.
- `src/pyforge/herald/state.py` -- reference only, for the asdict/strict-round-trip idiom to match.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/herald/deck_qa.py` -- add the report schema, `DEFAULT_GATES={}`, `run()`,
      `to_dict()`, `parse_report()` -- the interface Stories 14.2/14.3 register gates into.
- [x] `src/pyforge/herald/cli.py` -- add `deck qa <slug> [--repo-root]`, route it to a new
      `_run_deck_qa` that calls `deck_qa.run` + `dispatch()`, printing one JSON line.
- [x] `src/shared/packages/pyforge-herald/tests/test_deck_qa.py` -- new: covers every I/O
      matrix row above.
- [x] `src/shared/packages/pyforge-herald/tests/test_cli_deck_qa.py` -- new: `main(["deck",
      "qa", slug, "--repo-root", str(tmp_path)])` returns 0; stdout parses via `parse_report`.

**Acceptance Criteria:**
- Given the Spec's entrypoint-placement open question, when this story lands, then `herald
  deck qa <slug>` exists on the CLI dispatcher (not a standalone per-deck `scripts/` step).
- Given two gates supplied to `run()`, when the report is produced, then it is one JSON object
  keyed by gate id that round-trips through `to_dict`/`json.dumps`/`json.loads`/`parse_report`
  back to an equal `DeckQaReport`.
- Given a third gate id added to the same test's `gates` mapping, when `run()` runs again, then
  `deck_qa.py`'s schema, `run()`, `to_dict`/`parse_report`, and `cli.py` need zero changes.
- Given one gate that raises alongside one that passes, when `run()` executes both, then the
  raising gate's entry is `status:"error"` with a message, the passing gate is unaffected, and
  `run()` does not raise.
- Given a JSON document missing or carrying an unrecognized field, when `parse_report` parses
  it, then it raises `errors.HeraldError` naming the problem.

## Design Notes

`DEFAULT_GATES` is a plain module-level dict, not a decorator-based registration API — all
gates live in this one file per the epic's Surface lines, so there is no cross-module registry
to build. `run()` also accepts an explicit `gates` mapping so tests exercise the "add a third
gate" claim without mutating shared state. `GateResult` never repeats its own gate id — the
dict key in `DeckQaReport.gates` already carries it, so the two can never disagree.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/test_deck_qa.py src/shared/packages/pyforge-herald/tests/test_cli_deck_qa.py -v` -- expected: all new tests pass
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: full existing suite stays green

## Auto Run Result

Status: done

**Summary.** Story 14.1 adds `herald deck qa <slug>`: the deck visual-QA gate report
interface -- a JSON-round-trippable `DeckQaReport`/`GateResult`/`Finding` schema keyed by gate
id, a `run()` entrypoint that executes a caller-supplied gate mapping without ever aborting on
one gate's own failure, and the CLI wiring resolving the Spec's entrypoint-placement open
question in favor of the existing `deck` subcommand family. `DEFAULT_GATES` ships empty by
design -- Stories 14.2 (headless-render) and 14.3 (image-slot scan) each register one entry
here later with zero change to this module's public shape, `run()`'s signature, or `cli.py`.

**Files changed:**
- `src/pyforge/herald/deck_qa.py` (new) -- `Finding`/`GateResult`/`DeckQaReport`/`GateContext`
  dataclasses, `GateFn` alias, `DEFAULT_GATES`, `run()`, `to_dict()`, `parse_report()`.
- `src/pyforge/herald/cli.py` -- `deck qa <slug> [--repo-root]` subparser, `_route` branch,
  `_run_deck_qa` (composes `deck_qa.run` + `dispatch()`; no `McpTransport`/`bridge.run` --
  this subcommand is fully local, unlike every other `deck` subcommand).
- `tests/test_deck_qa.py` (new) -- the full I/O & Edge-Case Matrix plus the review-pass fixes.
- `tests/test_cli_deck_qa.py` (new) -- CLI wiring: exit code, JSON parseability, `--repo-root`
  default, and a regression proving `McpTransport` is never constructed.
- `tests/test_bridge.py` -- classifies `deck_qa.py` in the bridge-core module sweep (required
  by an existing meta-test; matches the sweep's own chronological-append convention).

**Review findings breakdown:** 3 patches applied, all in `deck_qa.py`, each with dedicated
regression tests -- `run()`'s `gates` parameter no longer binds a stale default (a future
`DEFAULT_GATES = {...}` reassignment, as opposed to an in-place mutation, would otherwise have
left the CLI path silently stuck on today's empty dict forever); `run()` now isolates a gate
returning a malformed value (wrong type, bad `status`, or a `status`/`error` invariant
violation) exactly the way it already isolated a raised exception, instead of letting garbage
flow silently into the report; `parse_report` now rejects a `status`/`error` pairing that
contradicts itself. 2 items deferred (`DW-FU-14-1`: a gate returning a non-JSON-serializable
field crashes the CLI with an unhandled `TypeError` instead of a controlled `HeraldError`;
`DW-FU-14-1-2`: no timeout wraps a gate call, so a hanging gate -- most plausibly Story 14.2's
render gate -- blocks indefinitely) -- both real but currently inert (`DEFAULT_GATES` is empty
in this story) and squarely Story 14.2/14.3's own concern when they land a real gate. 9 items
rejected, each verified against the actual code or spec before dropping (see the Review Triage
Log entry above for the full list and evidence per item) -- the most notable being a false
claim that `_BRIDGE_CORE_MODULES`'s tuple ordering regressed, which on inspection is
chronological/append-at-tail (not alphabetical), so appending `deck_qa` last is correct.

**Follow-up review recommendation:** false. The three patches are localized to one new file
(`deck_qa.py`), each independently covered by a new regression test (6 added), with the full
suite green throughout -- matches the "a few localized low-consequence fixes" case the
workflow's own guidance says does not warrant an independent follow-up pass.

**Verification performed:**
- `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/test_deck_qa.py src/shared/packages/pyforge-herald/tests/test_cli_deck_qa.py -v`: 26 passed (20 from
  implementation + 6 review-pass regression tests).
- `pixi run -e pyforge-herald pyforge-herald-test`: 1066 passed, 4 skipped (1060 baseline + 6
  new), run independently after the implementation subagent's own report and again after the
  review-pass patches.
- `git status`/`git diff` inspected directly (not just the implementation subagent's
  self-report) before and after the review pass; confirmed no changes outside this story's
  intended files (no `pixi.toml`, no `.github/workflows/`, no `recipes/`).

**Residual risks:** `DW-FU-14-1` and `DW-FU-14-1-2` (both deferred, currently inert -- see
above). This is a `local-recipes` monorepo PR touching files outside `recipes/`
(`src/shared/packages/pyforge-herald/`) -- per `CLAUDE.md`'s PR CI gate rule, the PR needs the
`maintenance` label at open/update time; `pixi.toml` was not touched, so the `environment.yaml`
sync gate does not apply.

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 2, low 1)
- defer: 2 (medium 1, low 1)
- reject: 9 (low 9)
- addressed_findings:
  - `[medium]` `[patch]` `run(gates=DEFAULT_GATES)` bound the default parameter to the dict
    object live at function-definition time; a future story reassigning
    `DEFAULT_GATES = {...}` (rather than mutating it in place) would leave `cli.py`'s
    no-`gates=`-passed call path silently stuck on the original empty dict forever, with no
    test failure. Changed the signature to `gates: Mapping[str, GateFn] | None = None` and
    resolve `DEFAULT_GATES` fresh inside the call; also fixes `run(slug, repo_root, gates=None)`
    raising `AttributeError` (`.items()` on `None`). Added
    `test_run_reads_default_gates_fresh_even_after_reassignment`.
  - `[medium]` `[patch]` `run()` isolated a gate's raised exception but not a gate silently
    returning something other than a well-formed `GateResult` (wrong type, an unrecognized
    `status`, or a `status`/`error` pairing violating the invariant `parse_report` enforces) --
    such a value flowed straight into the report and out through `to_dict`/`json.dumps` with no
    error at all, corrupting the promised schema silently. `run()` now validates each gate's
    return the same way `parse_report` validates parsed JSON, converting any violation into that
    gate's own `status: "error"` entry -- identical containment to a raised exception. Added
    `test_a_gate_returning_none_becomes_status_error`,
    `test_a_gate_returning_a_bad_status_value_becomes_status_error`,
    `test_a_gate_violating_the_status_error_invariant_becomes_status_error`.
  - `[low]` `[patch]` `parse_report` validated every field's presence/type/enum but not the
    `status == "error"` <=> `error is not None` cross-field invariant the module's own docstring
    describes -- a hand-edited or corrupted report with `status: "ok"` and a non-null `error` (or
    the reverse) passed validation despite being self-contradictory. Added the check to
    `_gate_result_from_dict`. Added `test_parse_report_rejects_ok_status_with_a_non_null_error`,
    `test_parse_report_rejects_error_status_with_a_null_error`.

Deferred (real, but not this story's problem to solve -- both currently inert since
`DEFAULT_GATES` ships empty in this story and become live only once Story 14.2/14.3 register a
real gate): `DW-FU-14-1` (a gate returning a non-JSON-serializable field value, e.g. a `Path` in
`artifacts`, crashes the CLI with an unhandled `TypeError` instead of a controlled
`HeraldError`) and `DW-FU-14-1-2` (`run()` has no timeout around a gate call, so a hanging
gate -- most plausibly Story 14.2's headless-Chromium render gate -- blocks the whole
`herald deck qa` invocation indefinitely).

Rejected (9, all low-consequence or resting on a false premise, verified against the actual
code/spec before dropping): no exit-code/pass-fail semantics tied to gate status (the spec's own
non-goals explicitly disclaim automated pixel/finding pass-fail -- "the PNGs feed a reviewer's
judgment, not an automated pass/fail"); no `slug`/`repo_root` existence validation (no gate reads
any file yet in this story -- premature); `@dataclass(frozen=True)` not deep-freezing nested
`list`/`dict` fields (matches `state.py`'s own existing convention, not a new gap); the `qa`
subcommand's help text (its "..., JSON (Story N)" phrasing mirrors `status`'s existing "..., JSON
(CAP-3)" convention verbatim); `_BRIDGE_CORE_MODULES`'s tuple ordering (verified against the
actual tuple -- it is chronological/append-at-tail, not alphabetical; `deck_qa` appended last is
correct, not a regression -- the reviewer conflated it with the unrelated, separately-alphabetized
`from . import (...)` block); the module docstring's "zero change to `run()`'s signature" claim
(accurate -- `GateContext` is explicitly documented as extensible by 14.2/14.3, which does not
touch `run()`'s signature); raw exception text in `error` messages (matches `dispatch()`'s
existing repo-wide convention of surfacing exception text unredacted); no lazy-import convention
for gates not yet written (speculative -- this story adds no dependency at all); no schema-version
field (the schema is additive-by-design, gate ids are the extension point, no spec requirement).
