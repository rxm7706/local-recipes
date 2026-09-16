---
title: '45.2: a drift detector fails a stale generated .mdc'
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

**Problem:** A generated .mdc can rot the first time SKILL.md changes.

**Approach:** Same script without --write is a scope=repo detector (bmad-cursor-mdc-check) discovered by scripts/detectors.py.

</intent-contract>
