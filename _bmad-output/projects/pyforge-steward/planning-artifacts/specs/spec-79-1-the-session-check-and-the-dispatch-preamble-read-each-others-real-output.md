---
title: "79.1: The session check and the dispatch preamble read each other's real output"
type: 'fix'
created: '2026-10-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-63-4-steward-session-check-one-verdict-for-the-session-preconditions-run-from-every-entry-point.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/session.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/tests/unit/test_session.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_check.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every `marshal factory dispatch` prints `MRS-DISP-049: steward session check reported a non-ok
session-precondition verdict: }`. CAP-5's one session verdict (Story 63.4) has two halves, and each reads output the
other half never writes. Found 2026-10-01 while dispatching Story 78.1; verified on `main` at `a9636014f5`.

1. **Steward misreads marshal's seed verdict.** `session.py::_seed_kit_findings` does
   `json.loads(result.stdout)["kit"]`. `marshal seed check --json` emits the schema-stable envelope every seed verb
   shares (`cli/seed.py::_json_ok_envelope`, marshal Story 12.5): `{"verb": "check", "ok": true, "result": {...,
   "kit": [...]}}`. The `KeyError` lands in the "returned unparseable output" branch, so the token-kit and
   codegraph-index findings are always non-ok with a meaningless detail. `test_session.py` fakes a bare
   `{"kit": [...]}`.
2. **Marshal misreads steward's verdict.** `steward`'s `cli.py::main` prints a failed duty's summary to stderr (the
   convention several steward duties' tests pin, e.g. `test_workspace.py`: "a failed duty's summary goes to stderr"),
   so a non-ok `steward session check --json` writes its JSON report to stderr. `dispatch.py::
   _surface_session_precondition_findings` parses only `result.stdout`, fails, and falls back to the last stderr line,
   `}`. `test_dispatch.py` fakes the failing JSON on stdout.

**Approach:**

- **Steward:** read `kit` from the envelope's `result`. When the envelope reports `ok: false`, report its
  `error.message` (and remedy) as the detail. A payload with no envelope or no `kit` is non-ok, naming what was
  missing. AC5's strictness is unchanged: `layer-off`, missing or stale entries are non-ok, and so is a context
  layer (`output`, `wire`, `structure-graph`) with no entry at all.
- **Marshal:** parse the report from stdout, else stderr: the first JSON object opening at the start of a line, so
  a warning before it or a line after it does not hide it. Only when neither stream holds one does the finding
  fall back to the tail line.
- **Tests** fake the other side's real output: steward's fakes use the envelope; marshal's fakes put a failing
  report on stderr with an empty stdout. Each side pins what the other reads: marshal's seed-check CLI test pins
  the envelope's `result.kit` entries (`item`, `layer`, `status`), and steward's CLI test pins a failing
  `--json` report on stderr; both run in their station's own suite. A steward test also parses the real
  `marshal seed check --json` output where the `marshal` CLI is on PATH (`-e pyforge-guild`) and skips elsewhere.

Ledger key: `79-1-the-session-check-and-the-dispatch-preamble-read-each-others-real-output`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-5 (`steward session check`, Story 63.4); AD-8 (`DutyResult` is frozen evidence; duties never `sys.exit`).
- `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `marshal seed check --json` returns its `{verb, ok, result}` envelope with three `ok` kit entries When the session check runs Then token-kit and codegraph-index are ok
- Given the envelope's kit reports `ccr-store: layer-off` and `codegraph-index: stale` When the session check runs Then token-kit is non-ok naming `ccr-store: layer-off`, and codegraph-index is non-ok naming `stale`
- Given the envelope reports `ok: false` with an `error` When the session check runs Then both kit findings are non-ok and carry the error's message
- Given stdout that is not JSON, or JSON with no `result.kit` When the session check runs Then both kit findings are non-ok and say what was missing
- Given the envelope's kit has no entry for a context layer (an empty or partial kit) When the session check runs Then token-kit is non-ok naming each absent layer
- Given `marshal seed check --json` runs When its envelope is read Then `result.kit` holds three entries, `caveman-skill`/`output`, `ccr-store`/`wire`, `codegraph-index`/`structure-graph`, each with a `status` (pinned in marshal's suite)
- Given the `marshal` CLI is installed When the real `marshal seed check --json` runs against this repo Then the session check's kit findings carry real kit statuses, never "unparseable"
- Given `steward session check --json` exits 1 with its report on stderr and an empty stdout When the dispatch preamble runs Then MRS-DISP-049 names each non-ok finding
- Given a report on stdout When the dispatch preamble runs Then it is read from stdout as before
- Given a warning line before the report, or a line after it When the dispatch preamble runs Then MRS-DISP-049 still names the non-ok findings
- Given neither stream holds a JSON report When the dispatch preamble runs Then MRS-DISP-049 carries the tail line as before
- Given either fix is reverted When its new tests run Then they fail (mutation)

## Tasks

1. Read `session.py::_seed_kit_findings`, `cli.py::main`'s output routing, `cli/seed.py`'s envelope helpers and `dispatch.py::_surface_session_precondition_findings`, with both test files.
2. Steward: read the envelope; report an error envelope's message; keep the existing `AttributeError` guard.
3. Marshal: parse stdout, else stderr.
4. Tests: rewrite steward's seed fakes to the envelope, add the error-envelope and missing-`result` cases and the real-CLI test; add marshal's stderr cases and an end-to-end `dispatch_once` case with the report on stderr; run both mutations by hand.
5. Run both station suites and `lint-types`; reconcile every Spec `spec-surface-check` names (memlog first, `git add`, then a scoped `--write-baseline --spec` for each).

## Boundaries & Constraints

**Always:**
- Marshal calls the steward CLI and never imports `pyforge.steward`; steward never imports `pyforge.marshal`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not change steward `main()`'s stream for a failed duty's summary; other duties and their tests depend on it.
- Do not relax AC5: a `layer-off`, missing or stale kit entry stays non-ok.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| healthy kit | envelope, three `ok` entries | token-kit ok, codegraph-index ok | — |
| declared-off layer | envelope, `ccr-store: layer-off` | token-kit non-ok, names it | — |
| seed error | envelope `ok: false`, `error` | both non-ok, error message | — |
| bare payload | `{"kit": [...]}` (no envelope) | both non-ok, "no result.kit" | — |
| failing session report | exit 1, JSON on stderr, stdout empty | MRS-DISP-049 names the non-ok findings | — |
| noisy stderr | a warning line, then the report, then a trailer | MRS-DISP-049 names the non-ok findings | — |
| absent layer | envelope, kit missing the `wire` entry | token-kit non-ok, "no wire layer entry reported" | — |
| passing report on stdout | exit 1, JSON on stdout | read from stdout | — |
| garbage | neither stream parses | MRS-DISP-049 with the tail line | — |

</intent-contract>

## Binding

Parent capability: CAP-5 (defect; no new CAP).
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-01 entry *the session check reports false
failures on every dispatch*.
Ledger key: `79-1-the-session-check-and-the-dispatch-preamble-read-each-others-real-output`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1).
Out of scope: `marshal seed check` on a repo with no seed state reports the manifest's init-only `{{ slug }}` entries
as HARD `artifact-missing` under their literal paths. That is marshal Story 70.1
(`spec-70-1-seed-check-judges-the-paths-the-manifest-means-never-its-placeholders.md`, `backlog`), which already names
steward's session check as a reader; no second record is added.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass.
- `pixi run --frozen -e pyforge-guild python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_session.py` — expected: pass, including the real `marshal seed check --json` test (skipped in `-e pyforge-steward`).
- `pixi run --frozen -e pyforge-guild steward session check --json` on the primary checkout — expected: token-kit and codegraph-index carry real kit statuses, never "unparseable".
- The two mutations in Task 4 — expected: each side's new tests fail with its fix removed.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
