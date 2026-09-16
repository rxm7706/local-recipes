---
title: '42.1: a co-governed file is clean when any one of its governing specs reconciled it'
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

**Problem:** spec-surface-check judged each governing spec independently, so a kernel spec stayed red after a narrower spec already named the same path.

**Approach:** Group _drift_findings by path and OR the existing clean-pass bar (memlog moved AND names the path) across co-governors.

</intent-contract>
