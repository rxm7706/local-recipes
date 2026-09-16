---
title: '45.1: a pixi task generates .mdc from SKILL.md'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: 'a799295fd6'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Cursor chat had no mechanical .mdc for the bmad-build / bmad-build-auto pilot.

**Approach:** scripts/bmad_cursor_mdc_check.py --write derives .cursor/rules/*.mdc from SKILL.md frontmatter plus the two-step trigger. Pixi task bmad-cursor-mdc-generate.

</intent-contract>
