---
title: '46.3: The mason station skill documents mason self-check'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 46-3-the-mason-station-skill-documents-mason-self-check
spec: spec-pyforge-mason
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a removal, a type fix, a skill regeneration or a planning record; nothing is switched
surface:
  - '.claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md'
  - 'src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py'
  - '.claude/skills/pyforge-mason/0.1.2/pyforge-mason/SKILL.md'
  - 'AGENTS.md'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The SKF-compiled station skill `pyforge-mason` documents `pyforge mason doctor`, which mason now refuses.

**Approach:** Run `skf-update-skill` from the module copy on the renamed source (the traps in `.claude/memory/feedback/running-skf-update-skill-skill-forge-3-0-0-on-a-station-skil.md`), then `skf-export-skill`; move the meta-test's pin to `pyforge mason self-check`; an independent check reads the skill against live `--help`.

Ledger key: `46-3-the-mason-station-skill-documents-mason-self-check`.

### Living CAP citations

- spec-pyforge-mason CAP-29 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Regenerate; never hand-edit a compiled skill.

**Never:**
- Never rewrite a section the rename does not touch.

## Acceptance Criteria

**Given** the compiled skill names `pyforge mason doctor`
**When** it is regenerated from the renamed source
**Then** it names `pyforge mason self-check` and no `mason doctor`
**And** its meta-test pins the new name

- **AC1 — Mason's meta-tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta -q -m "live_tree or not live_tree"
  ```

- **AC2 — The instruction surfaces agree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py -q -m "live_tree or not live_tree"
  ```

</intent-contract>

## Review (2026-11-26)

The skill was regenerated at 0.1.2 by `skf-update-skill` and re-exported; the provenance verifier reported no findings, and both `[MANUAL]` blocks carried over byte-identical. An independent agent then read SKILL.md against live `--help` and the source: no false command, flag, exit code or environment variable, the envelope's five keys and the report's eleven fields as stated, and no current `mason doctor`. Its findings and what was done: (1) `--json` and `--version` were missing; fixed by a note in the preserved `[MANUAL:additional-notes]` block. (2) `resolve.py`'s docstring for `MASON_FACTORY_ROOT` said Mason never reads it, but `cfe.build_native` does; corrected, line count kept. (3) The contract's island note said `--docker` on an island path is "recorded, not built"; in code it runs CFE's Docker build for `--config` with the island's environment, and the contract now says so. (4) Internal names `_DOCTOR_HELP`, `doctor_parser` and two comments renamed to self-check; `models.DoctorReport` and the module `doctor.py` keep their names (internal, and the report's fields do not change).
