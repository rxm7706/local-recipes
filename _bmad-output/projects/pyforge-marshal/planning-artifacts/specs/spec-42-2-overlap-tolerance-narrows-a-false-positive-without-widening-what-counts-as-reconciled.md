---
title: '42.2: overlap tolerance narrows a false positive without widening what counts as reconciled'
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

**Problem:** An OR across co-governors could hide a genuine FAIL if a second spec only moved for something else.

**Approach:** Keep the strongest residual severity. Existing single-owner fixtures stay green; a neither-named fixture still finds; mixed never-moved + presumed stays FAIL.

</intent-contract>
