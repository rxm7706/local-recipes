---
title: '33.3: The warden station skill documents --self-check'
type: 'chore'
created: '2026-11-26'
status: 'done'
story: 33-3-the-warden-station-skill-documents-self-check
spec: spec-pyforge-warden
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a removal, a type fix, a skill regeneration or a planning record; nothing is switched
surface:
  - '.claude/skills/pyforge-warden/active/pyforge-warden/SKILL.md'
  - 'src/shared/packages/pyforge-warden/tests/meta/test_skf_domain_skill.py'
  - '.claude/skills/pyforge-warden/0.1.2/pyforge-warden/SKILL.md'
  - '.claude/skills/pyforge-warden/skill-brief.yaml'
  - 'AGENTS.md'
  - 'docs/reference/skills-catalog.md'
  - 'docs/reference/bmad-estate-llms-full.md'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The SKF-compiled station skill `pyforge-warden` documents `scan --doctor`, which warden now refuses.

**Approach:** Run `skf-update-skill` from the module copy on the renamed source (the traps in `.claude/memory/feedback/running-skf-update-skill-skill-forge-3-0-0-on-a-station-skil.md`), then `skf-export-skill`; move the meta-test's pin to `scan --self-check`; an independent check reads the skill against live `--help`.

Ledger key: `33-3-the-warden-station-skill-documents-self-check`.

### Living CAP citations

- spec-pyforge-warden CAP-8 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Regenerate; never hand-edit a compiled skill.

**Never:**
- Never rewrite a section the rename does not touch.

## Acceptance Criteria

**Given** the compiled skill names `scan --doctor`
**When** it is regenerated from the renamed source
**Then** it names `scan --self-check` and no `--doctor`
**And** its meta-test pins the new spelling

- **AC1 — Warden's meta-tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta -q -m "live_tree or not live_tree"
  ```

- **AC2 — The instruction surfaces agree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py -q -m "live_tree or not live_tree"
  ```

</intent-contract>

## Review (2026-11-26)

The skill was regenerated at 0.1.2 by `skf-update-skill` from `_bmad/skf/skf-update-skill` and re-exported by `skf-export-skill`; the provenance verifier reported 0 missing, orphaned, stale or citation findings, and both `[MANUAL]` blocks carried over byte-identical. An independent agent then read SKILL.md against live `--help` and the source: no false command, flag, exit code or environment variable, and no current `--doctor`. Its findings and what was done: (1) `--json` was missing, because `align_json_options` adds it at parse-build time where extraction cannot see it; fixed by a note in the preserved `[MANUAL:additional-notes]` block, which also names the advisory `tea` check and the JSON document's `doctor` key. (2) The self-check's text output still printed `warden: doctor status=` and `[doctor]` lines; renamed `self-check` in `cli.py` with the line count kept, and the tests follow; the JSON key `doctor` stays, a machine contract. (3) Two citations point a few lines off (the schema version at `report.py:193`, `TOOL_NAME` at `report.py:194`); hand-editing a compiled citation breaks the provenance map, so DW-warden-33-3-1 carries them to the next regeneration.
