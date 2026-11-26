---
title: '33.1: Warden''s self-check is --self-check, and --doctor is its old spelling'
type: 'feature'
created: '2026-11-26'
status: 'done'
story: 33-1-warden-s-self-check-is-self-check-and-doctor-is-its-old-spelling
spec: spec-pyforge-warden
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a renamed spelling with the old one kept for a release; a flag would make the name differ by machine
surface:
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py'
  - 'src/shared/packages/pyforge-warden/tests/unit/test_cli_doctor.py'
  - 'src/shared/packages/pyforge-warden/tests/integration/test_doctor.py'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md'
  - 'docs/how-to/scan-for-compliance-with-warden.md'
  - 'docs-site/src/content/dossier/dossier.yml'
  - '.claude/skills/bmad-agent-warden/customize.toml'
  - 'docs/governance/machine-readiness.yaml'
  - 'docs/tutorials/onboard-a-machine.md'
  - 'docs/foundry/marketplace/skills/warden/scan/SKILL.md'
  - 'docs/foundry/marketplace/skills/warden/scan/steps.md'
  - 'docs/foundry/marketplace/site/skills/warden/scan.html'
  - 'docs/foundry/frames/stations/warden.frame.md'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Warden's environment self-check is `scan --doctor`, the name of the fleet's doctor station.

**Approach:** Register one switch with two option strings, `--self-check` and `--doctor`, writing the same destination; the old spelling prints one line on stderr. Move the tests to the new spelling and add one that runs both. Update the contract, the how-to, the dossier and the persona prompt. Leave the exit codes, the JSON document and the MCP face alone.

Ledger key: `33-1-warden-s-self-check-is-self-check-and-doctor-is-its-old-spelling`.

### Living CAP citations

- spec-pyforge-warden CAP-8 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep the old spelling working for one release: the same result, plus one line on stderr saying it is renamed.

**Never:**
- Never change an exit code or the JSON document.
- Never hand-edit the compiled station skill.

## Acceptance Criteria

**Given** warden's self-check is `scan --doctor`
**When** the flag is renamed `--self-check` and `--doctor` kept as its old spelling
**Then** both spellings run the same self-check with the same exit code and stdout, and only the old one prints the notice
**And** the contract, the how-to, the dossier and the persona prompt use the new spelling

- **AC1 — Warden's suite passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-warden pyforge-warden-test
  ```

- **AC2 — Warden's contract matches its parser.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-warden pyforge-warden-live-test
  ```

</intent-contract>

## Review (2026-11-26)

An independent `bmad-review` pass read the diff against the stated intent only. Findings and what was done:

1. **`steward init` still ran `warden scan --doctor`** (`docs/governance/machine-readiness.yaml`, row `warden-doctor`), and the onboarding tutorial quoted it; after the alias's removal init would misread exit 2. Fixed: the row and the tutorial use `--self-check`, and the removal row says so.
2. **Hand-written pages still showed `--doctor`**: the marketplace scan skill (`SKILL.md`, `steps.md`, its rendered `site/.../scan.html`) and the warden Frame. Fixed. The generated mirrors (the SKF block of `AGENTS.md`, `skills-catalog.md`, `bmad-estate-llms-full.md`) are named in DW-warden-33-1-2; the dated decks keep the spelling of their day.
3. **The text output still says `doctor`** (`warden: doctor status=…`, `[doctor] <check>`). Kept: the intent froze the self-check's output, and its JSON key is `doctor`; revisit when the alias is removed.
4. **The notice prints under `--quiet`-like settings.** Kept on purpose: a rename notice is for the person who typed the old spelling.
5. **The story reads `done` before the review finished.** This repository's hand-landed stories are written `done` with their PR; the review's fixes ride the same PR, and the record is this section.

Confirmed: `--doc` resolves to `--doctor` (with the notice) and `--self` to `--self-check`; `--format json` keeps stdout one document, with stderr closed too; `align_json_options` is unaffected; the doctor station calls `run_doctor_checks` in-process and no MCP face reaches the flag.
