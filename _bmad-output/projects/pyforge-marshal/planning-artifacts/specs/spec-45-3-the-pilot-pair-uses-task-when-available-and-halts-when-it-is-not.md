---
title: '45.3: the pilot pair uses Task when available and HALTs when it is not'
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

**Problem:** Review must not silently skip on a no-Task Cursor surface.

**Approach:** Generated .mdc files instruct Task when available, HALT blocked/no subagents otherwise, forbid cursor-agent -p as a substitute, and reach team memory via Read/@file.

</intent-contract>
