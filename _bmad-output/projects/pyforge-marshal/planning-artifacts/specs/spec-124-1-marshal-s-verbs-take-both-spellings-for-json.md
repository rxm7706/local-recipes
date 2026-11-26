---
title: '124.1: Marshal''s verbs take both spellings for JSON'
type: 'feature'
created: '2026-11-26'
status: 'done'
story: 124-1-marshal-s-verbs-take-both-spellings-for-json
spec: spec-pyforge-marshal
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # not gated: an added spelling of an existing option; a flag would make one spelling work on some machines only
surface:
  - 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/contract.md'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Most of marshal's verbs take `--format {text,json}` and its `seed` verbs take `--json`, each only one, so a caller who learned the other spelling on another station gets a usage error here.

**Approach:** Call `pyforge.core.cli_output.align_json_options` at the end of the parser builder, and list the added spelling in `contract.md`.

Ledger key: `124-1-marshal-s-verbs-take-both-spellings-for-json`.

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

**Given** each marshal verb takes one spelling only
**When** the parser builder calls the kernel helper
**Then** each such verb also takes the other spelling with the same result
**And** nothing that parsed before changes

- **AC1 — Marshal's contract matches its parser.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_public_contract.py -q -m "live_tree or not live_tree"
  ```

- **AC2 — Every station's built parser is aligned.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pytest tests/scripts/test_json_output_spellings.py -q
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent only. Applied from the review: the prose said marshal's verbs all take `--format`; its `seed` verbs take `--json` and gained `--format`. The contract rows were already right.
