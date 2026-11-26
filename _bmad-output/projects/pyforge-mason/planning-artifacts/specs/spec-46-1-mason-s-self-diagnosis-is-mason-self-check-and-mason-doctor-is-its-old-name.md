---
title: '46.1: Mason''s self-diagnosis is mason self-check, and mason doctor is its old name'
type: 'feature'
created: '2026-11-26'
status: 'done'
story: 46-1-mason-s-self-diagnosis-is-mason-self-check-and-mason-doctor-is-its-old-name
spec: spec-pyforge-mason
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a renamed spelling with the old one kept for a release; a flag would make the name differ by machine
surface:
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_cli.py'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md'
  - '.claude/skills/bmad-agent-mason/customize.toml'
  - '.claude/skills/bmad-agent-mason/SKILL.md'
  - 'docs/governance/machine-readiness.yaml'
  - 'docs/tutorials/onboard-a-machine.md'
  - '.claude/skills/bmad-agent-mason/transcripts/mason-doctor-e2e.json'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Mason's self-diagnosis is the top-level command `mason doctor`, the name of the fleet's doctor station.

**Approach:** Register the command as `self-check` with `doctor` as an argparse alias; the alias prints one line on stderr, and the envelope names the command as it was called so a reader of `"doctor"` keeps working. Move the tests to the new name and add one that runs both. Amend CAP-29's grammar list through its memlog and a render, rename FR-34 in place, and update the contract and the persona.

Ledger key: `46-1-mason-s-self-diagnosis-is-mason-self-check-and-mason-doctor-is-its-old-name`.

### Living CAP citations

- spec-pyforge-mason CAP-5 (no text change).
- spec-pyforge-mason CAP-29 (grammar list amended 2026-11-26).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep the old spelling working for one release: the same result, plus one line on stderr saying it is renamed.

**Never:**
- Never change the exit code or the report's fields.
- Never hand-edit the compiled station skill.

## Acceptance Criteria

**Given** mason's self-diagnosis is `mason doctor`
**When** the command is `mason self-check` and `doctor` kept as its alias
**Then** both report the same data with exit 0, and only the old name prints the notice
**And** CAP-29, FR-34, the contract and the persona use the new name

- **AC1 — Mason's suite passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pyforge-mason-test
  ```

- **AC2 — Mason's contract matches its parser.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pyforge-mason-live-test
  ```

</intent-contract>

## Review (2026-11-26)

An independent `bmad-review` pass read the diff against the stated intent only. Findings and what was done:

1. **The notice could reach stdout.** With fd 2 closed at start-up `sys.stderr` is `None`, and `print(file=None)` writes to stdout, breaking the one-JSON-document rule. Fixed: `_notice` drops the line when stderr is `None` and swallows a dead stream; a test runs `doctor --format json` with `sys.stderr = None` and parses stdout.
2. **`steward init` still ran `pyforge mason doctor`** (`docs/governance/machine-readiness.yaml`, rows `station-clis` and `mason-recipe`), and the onboarding tutorial quoted it. Fixed: both rows and the tutorial use `self-check`.
3. **The persona's golden transcript still ran `pyforge mason doctor`.** Fixed: its argv is `self-check`. The compiled station skill and the generated mirrors are named in DW-mason-46-1-2.
4. **The story reads `done` before the review finished.** This repository's hand-landed stories are written `done` with their PR; the review's fixes ride the same PR, and the record is this section.

Confirmed: `mason --help` lists `self-check (doctor)`; CAP-5's one documented alias is the bare-noun `package --ship` and is unaffected; `align_json_options` skips the alias's repeated parser.
