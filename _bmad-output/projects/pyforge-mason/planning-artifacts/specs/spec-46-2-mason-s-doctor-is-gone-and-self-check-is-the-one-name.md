---
title: '46.2: Mason''s doctor is gone, and self-check is the one name'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 46-2-mason-s-doctor-is-gone-and-self-check-is-the-one-name
spec: spec-pyforge-mason
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a removal, a type fix, a skill regeneration or a planning record; nothing is switched
surface:
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_cli.py'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md'
  - 'src/shared/packages/pyforge-mason/README.md'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py'
  - 'src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 46.1 kept `doctor` as an alias of `self-check` for one release; the operator ruled it removed now. SPEC.md's `companions:` comments also trailed the reviewed chain (DW-mason-37-2).

**Approach:** Drop the alias, the notice and its helper; the envelope always names `self-check`; test that `doctor` is refused. Re-render CAP-29's grammar list and the `companions:` comments from a memlog decision; drop the alias from the contract and the spine's command table.

Ledger key: `46-2-mason-s-doctor-is-gone-and-self-check-is-the-one-name`.

### Living CAP citations

- spec-pyforge-mason CAP-29 (grammar list re-rendered 2026-11-26).
- spec-pyforge-mason CAP-5 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep the report's fields.

**Never:**
- Never change an exit code.

## Acceptance Criteria

**Given** `doctor` is an alias
**When** it is removed
**Then** `mason doctor` exits 2 as an invalid choice
**And** the self-check's report and exit code are unchanged

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

An independent `bmad-review` pass read the diff against the stated intent only (the skill files excluded, being regenerated). It found nothing blocking; for this story it found the PRD's 46.1 reconciliation and `updated:` note still calling `doctor` an alias (a Story 46.2 reconciliation section now records the removal), a stale comment in the self-check branch and three persona-test fixtures naming `doctor` (all fixed), and mason's README and module docstring naming `doctor` (fixed, line counts kept). The `As-built surface` prose in SPEC.md sits in the dated 2026-08-26 reconciliation section and keeps the name of its day.
