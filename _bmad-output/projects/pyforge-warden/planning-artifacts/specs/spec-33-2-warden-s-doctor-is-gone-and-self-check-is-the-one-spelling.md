---
title: '33.2: Warden''s --doctor is gone, and --self-check is the one spelling'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 33-2-warden-s-doctor-is-gone-and-self-check-is-the-one-spelling
spec: spec-pyforge-warden
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a removal, a type fix, a skill regeneration or a planning record; nothing is switched
surface:
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py'
  - 'src/shared/packages/pyforge-warden/tests/unit/test_cli_doctor.py'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md'
  - 'src/shared/packages/pyforge-warden/README.md'
  - 'src/shared/packages/pyforge-warden/tests/integration/test_doctor.py'
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 33.1 kept `--doctor` as an old spelling of `--self-check` for one release; the operator ruled it removed now.

**Approach:** Make `--self-check` a plain switch writing `args.doctor` (the JSON key stays), drop the custom action and the notice, test that `--doctor` is refused, and drop the old spelling from the contract, the how-to, the marketplace skill and the Frame. `steward init` already runs `--self-check` (Story 33.1).

Ledger key: `33-2-warden-s-doctor-is-gone-and-self-check-is-the-one-spelling`.

### Living CAP citations

- spec-pyforge-warden CAP-8 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep the JSON document's `doctor` key.

**Never:**
- Never change an exit code.

## Acceptance Criteria

**Given** `--doctor` is an old spelling
**When** it is removed
**Then** `warden scan --doctor` exits 2 as an unrecognized argument
**And** the self-check and its JSON document are unchanged

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

An independent `bmad-review` pass read the diff against the stated intent only (the skill files excluded, being regenerated). It found nothing blocking; for this story it found two stale descriptions of the removed spelling, both fixed: warden's package README (`run --doctor first`, the self-check paragraph) and steward's contract cell naming what `steward init` runs; and two source comments naming `--doctor`, reworded with the line count kept so the regenerated skill's citations hold. It confirmed nothing in scripts, workflows, tasks, docs-site, the Frames or steward init's data still invokes `--doctor`.
