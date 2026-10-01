---
title: "73.1: `steward session check` reads `marshal seed check`'s envelope, whatever its exit code"
type: 'fix'
created: '2026-09-28'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/session.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py
  - src/shared/packages/pyforge-steward/tests/fixtures/marshal_seed_check_envelope.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every `marshal factory dispatch` warns `MRS-DISP-049` (`cli/dispatch.py::_surface_session_precondition_findings`)
because `pixi run --frozen -e pyforge-guild steward session check --json` exits 1 with `token-kit` and `codegraph-index` both
`ok: false`, detail `pixi run --frozen -e pyforge-guild marshal seed check --json returned unparseable output:     "failing": true;   }; }`,
remedy `pixi run -e pyforge-guild marshal seed kit`. Diagnosed 2026-09-28 in a fresh worktree:

- `marshal seed check --json` writes **one valid JSON document** to stdout (8,302 bytes; stderr empty — no pixi banner,
  nothing merged) and exits 1 because its own report has HARD findings.
- Since marshal Story 12.5 (2026-08-23, FR-123 / NFR-12; `cli/seed.py::_json_ok_envelope` / `_json_error_envelope`) every
  `marshal seed` verb wraps its payload in a schema-stable envelope: `{"verb": "check", "ok": true, "result": {"strict", "findings",
  "model_version", "kit", "failing"}}` on success, `{"verb", "ok": false, "error": {…}}` on a `SeedError`. The kit sits at
  `result.kit`.
- `session.py::_seed_kit_findings` (Story 63.4, 2026-09-24) does `payload = json.loads(result.stdout); kit = payload["kit"]`.
  The `KeyError` falls into `except json.JSONDecodeError, KeyError, TypeError`, is reported as "returned unparseable output",
  and the detail quotes the last three stdout lines joined by `; ` — the closing `"failing": true`, `}`, `}` of a valid
  document.
- Not the cause: stderr (empty), the pixi banner (absent from stdout), the non-zero exit (the reader never looks at
  `returncode`), a line-joined rendering (only how the detail prints). A fix must keep the exit code out of the verdict:
  the seed check exits 1 whenever its own report is failing, whatever the kit says.
- `tests/unit/test_session.py` builds flat `{"kit": [...]}` payloads the CLI never emitted, so the suite stayed green while
  the check never read a real kit.

**Approach:** in `_seed_kit_findings`, parse stdout once. When it is not JSON, keep today's "unparseable output" finding
(stdout's tail; stderr's when present). When it is a JSON object whose `ok` is `false`, both findings are non-ok with the
envelope's `error` type and message as the detail (the kit remedy stays). Otherwise take `result.kit`; a document with no
`result` object or no `kit` list reads "no kit report" naming the top-level keys it found. The per-item rules for the two
findings are unchanged. `returncode` is never consulted on these paths. Record one live document for the tests:
`pixi run --frozen -e pyforge-guild marshal seed check --json > src/shared/packages/pyforge-steward/tests/fixtures/marshal_seed_check_envelope.json`
(it carries no absolute paths; check before committing), and move every existing kit fixture in `test_session.py` to the
envelope shape.

Ledger key: `73-1-steward-session-check-reads-marshal-seed-check-s-envelope-whatever-its-exit-code`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-162 (FR-35; extends CAP-5); AD-1 (wrap, never reimplement), AD-8 (`main()` owns the exit code).
- Kinship: marshal FR-123 / NFR-12 (the envelope, Story 12.5); the parallel marshal mint for `marshal seed check`'s own HARD
  findings (manifest paths whose slug placeholder is never rendered) — marshal's to fix, not this story's.

## Acceptance Criteria

- Given the recorded live document (`ok: true`, `result.failing: true`, kit `caveman-skill: missing`, `ccr-store: layer-off`, `codegraph-index: instrument-unavailable`) returned with exit 1 When `_seed_kit_findings` runs Then `token-kit` is non-ok naming all three items with their statuses, `codegraph-index` is non-ok naming `instrument-unavailable`, and neither detail contains "unparseable"
- Given the same document with every kit item's status `ok` When it is returned with exit 0 and again with exit 1 Then both findings are ok both times
- Given `{"verb": "check", "ok": false, "error": {"type": "ManifestError", "message": "bad manifest", "remedy": "…"}}` When `_seed_kit_findings` runs Then both findings are non-ok and their detail names `ManifestError` and `bad manifest`
- Given stdout `not json` When `_seed_kit_findings` runs Then both findings read "unparseable output" as today
- Given `{"verb": "check", "ok": true, "result": {}}` When `_seed_kit_findings` runs Then both findings are non-ok with a "no kit report" detail naming the keys found, never "unparseable"
- Given the top-level `payload["kit"]` read restored When the recorded-document test runs Then it fails (mutation)
- Given the change When `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Steward shells `marshal seed check --json` exactly as today (`_SEED_CHECK_ARGV`); it reads marshal's published envelope and
  never imports `pyforge.marshal`.
- The kit's per-item rules stay Story 63.4's: any status but `ok` makes `token-kit` non-ok; the `codegraph-index` entry drives
  `codegraph-index`.
- `session.py` stays the one module that composes the session findings; `main()` keeps the exit domain (0 / 1 / 70).

**Never:**
- Do not treat the seed check's exit code as the verdict, and do not surface its HARD findings as kit findings — they are
  marshal's (Kinship: the parallel marshal mint).
- Do not change marshal's envelope, `MRS-DISP-049`, or `cli/dispatch.py`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| live document, failing seed report | envelope `ok: true`, exit 1, kit non-ok | `token-kit` / `codegraph-index` name the kit's statuses | never "unparseable" |
| all-ok kit | envelope `ok: true`, exit 0 or 1 | both findings ok | — |
| seed error | envelope `ok: false`, `error` | both non-ok, detail names the error type and message | kit remedy kept |
| not JSON | `not json` | "unparseable output" (tail named) | as today |
| JSON, no kit | `result` missing or `kit` not a list | "no kit report", keys named | — |
| launch failure | `OSError` / timeout | "could not run" | as today |

</intent-contract>

## Source

Contract authored from `docs/dreams/pyforge-steward.md`'s 2026-09-28 (later) Realization-log entry *Proposed:
`steward session check` reads the seed check it asks*, and `spec-pyforge-steward` CAP-162 with its 2026-09-28 direction
entry in the Spec's `.memlog.md` (the diagnosis above).

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-162 (FR-35).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-28 (later) — Proposed: `steward session check` reads the seed check it asks*.
Ledger key: `73-1-steward-session-check-reads-marshal-seed-check-s-envelope-whatever-its-exit-code`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-guild steward session check --json` — expected: `token-kit` and `codegraph-index` details name
  kit statuses, never "unparseable output"; the exit code follows the findings.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log

### 2026-10-01 — Independent review (with Story 79.1, which found this story's defect again and landed beside it)

A separate agent reviewed the change in two passes against this spec and Story 79.1's. Its findings on this half:

- `[high]` `[patch]` The first cut was minted as Story 79.1 and never cited this story or CAP-162. Fixed: this story's
  contract is the one realized here, and 79.1 is narrowed to the dispatch preamble and the cross-station pins.
- `[medium]` `[patch]` Tests faked a bare `{"kit": ...}`. Fixed: every fake uses the envelope, plus the recorded document.
- `[low]` `[reject]` An empty or partial kit reads `token-kit` ok. Not reachable through the CLI (marshal always reports
  three entries; Story 79.1 pins that in marshal's suite), and this spec's Always keeps Story 63.4's per-item rules.
- `[low]` `[patch]` The malformed-kit-entry guard had no test. Fixed: a parametrized case.

**Deviation (recorded, not silent):** AC1 names the statuses of the 2026-09-28 recording (`codegraph-index:
instrument-unavailable`). The fixture was recorded from the live CLI on 2026-10-01 (8,263 bytes, exit 1, stderr
empty, no absolute paths), where the worktree's kit reads `caveman-skill: missing`, `ccr-store: layer-off`,
`codegraph-index: missing`; the test derives its expectations from the recorded document rather than restating them.

**Also found while here:** the two bmad-method fallback tests assumed the `pyforge-steward` env (no doctor) and failed
under `-e pyforge-guild`; they now hide `pyforge.doctor` themselves (`_hide_doctor`).

## Auto Run Result

Hand-built in an interactive session together with Story 79.1. Verification:

- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: green (counts in the landing PR).
- `pixi run --frozen -e pyforge-guild python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_session.py`:
  green, including the real `marshal seed check --json` parse.
- `pixi run --frozen -e pyforge-guild steward session check --json`: `token-kit` reads `caveman-skill: missing;
  ccr-store: layer-off; codegraph-index: missing` and `codegraph-index` reads `missing`; no "unparseable"; exit 1.
- Mutation (AC6): restoring the top-level `payload["kit"]` read fails the recorded-document test and 11 others.
