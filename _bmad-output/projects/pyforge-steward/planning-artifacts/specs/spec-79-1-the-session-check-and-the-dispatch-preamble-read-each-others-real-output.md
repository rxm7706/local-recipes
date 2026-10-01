---
title: "79.1: The session check and the dispatch preamble read each other's real output"
type: 'fix'
created: '2026-10-01'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-63-4-steward-session-check-one-verdict-for-the-session-preconditions-run-from-every-entry-point.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-73-1-steward-session-check-reads-marshal-seed-check-s-envelope-whatever-its-exit-code.md
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

1. **Steward misreads marshal's seed envelope.** Already specced as Story 73.1 (CAP-162, 2026-09-28); this story lands
   beside it and does not restate it.
2. **Marshal misreads steward's verdict (this story).** `steward`'s `cli.py::main` prints a failed duty's summary to
   stderr (the convention several steward duties' tests pin, e.g. `test_workspace.py`: "a failed duty's summary goes to
   stderr"), so a non-ok `steward session check --json` writes its JSON report to stderr. `dispatch.py::
   _surface_session_precondition_findings` (Story 63.4) parses only `result.stdout`, fails, and falls back to the last
   stderr line, `}`. `test_dispatch.py` fakes the failing JSON on stdout, and nothing pins either side's output for the
   other.

**Approach:**

- **Marshal:** read the report from stdout, else stderr: the first JSON object carrying `findings` that opens at the
  start of a line, so a warning before it (even a JSON log line) or a line after it does not hide it. Only when neither
  stream holds one does the finding fall back to the tail line.
- **Pins, one per direction, each in its owner's suite:** marshal's seed-check CLI test pins `result.kit`'s three
  entries (`caveman-skill`/`output`, `ccr-store`/`wire`, `codegraph-index`/`structure-graph`, each with a `status`);
  steward's CLI test pins a failing `--json` report on stderr with stdout empty. A guild-env steward test also parses
  the real `marshal seed check --json` (skipped where marshal is not installed).

Ledger key: `79-1-the-session-check-and-the-dispatch-preamble-read-each-others-real-output`.
Type / Effort / Deps: fix / S / — (lands with Story 73.1).

### Living CAP citations

- CAP-5 (`steward session check`, Story 63.4); AD-8 (`DutyResult` is frozen evidence; duties never `sys.exit`).
- CAP-162 / Story 73.1: the steward half, landed in the same change.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `steward session check --json` exits 1 with its report on stderr and an empty stdout When the dispatch preamble runs Then MRS-DISP-049 names each non-ok finding
- Given a warning line (plain or JSON) before the report, or a line after it When the dispatch preamble runs Then MRS-DISP-049 still names the non-ok findings
- Given a report on stdout When the dispatch preamble runs Then it is read from stdout as before
- Given neither stream holds a JSON report When the dispatch preamble runs Then MRS-DISP-049 carries the tail line as before
- Given `marshal seed check --json` runs When its envelope is read Then `result.kit` holds three entries, `caveman-skill`/`output`, `ccr-store`/`wire`, `codegraph-index`/`structure-graph`, each with a `status` (pinned in marshal's suite)
- Given a non-ok session check When steward's CLI runs it with `--json` Then the JSON report is on stderr and stdout is empty (pinned in steward's suite)
- Given the stderr read is reverted When its new tests run Then they fail (mutation)

## Tasks

1. Read `cli.py::main`'s output routing and `dispatch.py::_surface_session_precondition_findings`, with both test files.
2. Marshal: read stdout, else stderr, scanning for the report.
3. Tests: marshal's stderr, noisy-stderr and end-to-end `dispatch_once` cases; the stdout-path test relabelled; the producer pin in `test_seed_cli_seed_check.py`; steward's stderr pin; the mutation by hand.
4. Run both station suites and `lint-types`; reconcile every Spec `spec-surface-check` names (memlog first, `git add`, then a scoped `--write-baseline --spec` for each).

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
| failing session report | exit 1, JSON on stderr, stdout empty | MRS-DISP-049 names the non-ok findings | — |
| noisy stderr | a warning (plain or JSON) line, then the report, then a trailer | MRS-DISP-049 names the non-ok findings | — |
| report on stdout | exit 1, JSON on stdout | read from stdout | — |
| garbage | neither stream holds a report | MRS-DISP-049 with the tail line | — |

</intent-contract>

## Binding

Parent capability: CAP-5 (defect; no new CAP). Sibling: CAP-162 / Story 73.1 (the steward half), landed together.
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-01 entry *the dispatch preamble reads the
session verdict from the wrong stream*.
Ledger key: `79-1-the-session-check-and-the-dispatch-preamble-read-each-others-real-output`.
Ledger status at mint: `backlog`; `done` at landing.
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
- The real streams of `steward session check --json`, fed to `_surface_session_precondition_findings` — expected: MRS-DISP-049 names `token-kit, codegraph-index`, not `}`.
- The mutation in Task 3 — expected: the stderr tests fail with the stderr read removed.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

### 2026-10-01 — Independent review (adversarial; a separate agent read the diff against this spec and 63.4)

- verdicts: first pass 7 findings (medium 2, low 5); follow-up pass on the patch commit: 1 high, 2 low new; all closed.
- findings:
  - `[medium]` `[patch]` The chain claimed the seed check's `{{ slug }}` gap was "recorded on marshal's deferred-work ledger"; no such row existed, and marshal Story 70.1 already covers it. Fixed: Binding, Dream and a correcting memlog entry point at 70.1; the ledger path left the `"79"` surface; no row added.
  - `[medium]` `[patch]` The anti-drift test (steward parsing the real `marshal seed check`) skips in `-e pyforge-steward`, the env CI and `verify_commands` use. Fixed: a producer pin in marshal's own suite, `test_seed_cli_seed_check.py::test_json_kit_entries_carry_the_fields_steward_reads`.
  - `[low]` `[patch]` Reading stderr as one JSON object: a warning line before the report brought back `}`. Fixed: scan for the first JSON object that opens a line (verified with a warning, a trailer, CRLF and a compact report).
  - `[low]` `[patch]` Two older marshal tests still sent the failing report on stdout. Fixed: the stdout test is labelled as the stdout path; the 63.4 `dispatch_once` test now sends it on stderr (the duplicate end-to-end test was dropped).
  - `[low]` `[reject]` An empty or partial kit reads token-kit ok. Not reachable through the CLI (marshal always reports three entries, now pinned), and Story 73.1's Always keeps Story 63.4's per-item rules; an absent-layer rule was tried and removed.
  - `[low]` `[patch]` The malformed-kit-entry guard had no test. Fixed: a parametrized case (`result.kit: ["x"]`).
  - `[low]` `[patch]` State: status, this log and the spec-surface stamp were outstanding. Fixed at landing.
  - `[high]` `[patch]` (follow-up) The steward half duplicated Story 73.1 (CAP-162, minted 2026-09-28, `backlog`). Fixed: this story is narrowed to the dispatch preamble and the pins; Story 73.1 lands in the same change to its own contract (recorded fixture, "no kit report", the error's type and message) and its ledger row moves to `done`.
  - `[low]` `[patch]` (follow-up) A kit entry with an unhashable `layer` crashed the duty. Gone with the absent-layer rule (no set over layers remains).
  - `[low]` `[patch]` (follow-up) The scan took the first column-0 JSON object even when it was not a report. Fixed: only an object carrying `findings` counts (a JSON log line before the report is a test case).

## Auto Run Result

Hand-built in an interactive session, reviewed by a separate agent (two passes). Verification:

- `pixi run --frozen -e pyforge-steward pyforge-steward-test` and `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: green (counts in the landing PR).
- `pixi run -e pyforge-guild lint-types`: green.
- The real `steward session check --json` streams (exit 1, 0 bytes on stdout, the report on stderr) fed to `_surface_session_precondition_findings`: `non-ok findings: token-kit, codegraph-index`.
- Mutation: removing the stderr read fails the stderr, noisy-stderr and end-to-end tests.
