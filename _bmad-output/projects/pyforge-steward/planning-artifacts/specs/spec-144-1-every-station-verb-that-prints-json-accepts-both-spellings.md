---
title: '144.1: Every station verb that prints JSON accepts both spellings'
type: 'feature'
created: '2026-11-26'
status: 'done'
story: 144-1-every-station-verb-that-prints-json-accepts-both-spellings
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # not gated: an added spelling of an existing option; a flag would make one spelling work on some machines only
surface:
  - 'src/shared/packages/pyforge-core/src/pyforge/core/cli_output.py'
  - 'src/shared/packages/pyforge-core/tests/unit/test_cli_output.py'
  - 'tests/scripts/test_json_output_spellings.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Doctor, herald and steward take `--json`; marshal, mason and warden take `--format json`. A caller scripting several stations must know which each verb takes.

**Approach:** Add `pyforge.core.cli_output.align_json_options`, which walks a built `argparse` tree once and gives every parser that accepts one spelling the other, writing to the same destination. Call it at the end of steward's `build_parser`. Hold every station's built parser to it with a repo-root test. Leave a `--format` with other choices alone.

Ledger key: `144-1-every-station-verb-that-prints-json-accepts-both-spellings`.

### Living CAP citations

- spec-pyforge-steward:CAP-185 (minted 2026-11-26); FR-59 ← CAP-185.
- spec-pyforge-core:CAP-3 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every invocation that parsed before parsing the same way.

**Never:**
- Never rename or remove an option.
- Never give a twin to a `--format` whose choices are not exactly `text` and `json`.
- Never edit a compiled station skill.

## Acceptance Criteria

**Given** the stations spell a request for JSON two ways
**When** the kernel helper is added and steward calls it
**Then** every steward verb that prints JSON takes both spellings with the same result, and the tests fail by name when one is missing
**And** nothing is renamed or removed

- **AC1 — The kernel helper's tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/unit/test_cli_output.py -q
  ```

- **AC2 — Every station's built parser is aligned.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pytest tests/scripts/test_json_output_spellings.py -q
  ```

- **AC3 — Steward's contract matches its parser.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py -q -m live_tree
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent only. Applied from the review: a twin is now matched only when spelled in full, because the first version made abbreviations that resolved before (`doctor monitor --f`, `steward workspace start <slug> --f`, `marshal seed init <path> --fo`) ambiguous; choices are compared as a set; a parser whose subcommand has a `--format` of another kind gets no `--format` twin (`steward glass`); the kernel tests cover a global option repeated on a subparser; the fleet test is in the scripts-lib lane, checks each twin's destination, and warden's suite holds warden. Not done: the compiled station skills still show one spelling in their usage lines (they are regenerated, not edited); atlas's module entry points keep `--json` alone.
