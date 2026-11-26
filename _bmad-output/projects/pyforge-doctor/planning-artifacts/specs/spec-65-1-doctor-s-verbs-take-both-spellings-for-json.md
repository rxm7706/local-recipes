---
title: '65.1: Doctor''s verbs take both spellings for JSON'
type: 'feature'
created: '2026-11-26'
status: 'done'
story: 65-1-doctor-s-verbs-take-both-spellings-for-json
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # not gated: an added spelling of an existing option; a flag would make one spelling work on some machines only
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/pyforge-doctor.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Doctor's verbs take `--json` and not `--format {text,json}`, so a caller who learned the other spelling on another station gets a usage error here.

**Approach:** Call `pyforge.core.cli_output.align_json_options` at the end of the parser builder, and list the added spelling in `contract.md`, with the kernel module in its import-closure table.

Ledger key: `65-1-doctor-s-verbs-take-both-spellings-for-json`.

### Living CAP citations

- spec-pyforge-steward:CAP-185 (minted 2026-11-26; realized here).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every invocation that parsed before parsing the same way.

**Never:**
- Never rename or remove an option.
- Never edit the compiled station skill.

## Acceptance Criteria

**Given** doctor's verbs take `--json` only
**When** the parser builder calls the kernel helper
**Then** each such verb also takes `--format {text,json}` with the same result
**And** nothing that parsed before changes

- **AC1 — Doctor's contract matches its parser.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py -q -m "live_tree or not live_tree"
  ```

- **AC2 — Every station's built parser is aligned.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pytest tests/scripts/test_json_output_spellings.py -q
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent only. Applied from the review: doctor's second command line, `python -m pyforge.doctor.sources`, is aligned too, with its contract row.
