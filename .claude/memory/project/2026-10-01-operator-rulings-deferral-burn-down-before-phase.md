---
name: "2026-10-01-operator-rulings-deferral-burn-down-before-phase"
description: "2026-10-01 operator rulings (deferral burn-down, before Phase 2): run the 'stop the inflow' items first, after steward…"
metadata:
  type: project
---

2026-10-01 operator rulings (deferral burn-down, before Phase 2): run the 'stop the inflow' items first, after steward 78.1 lands. (1) doctor sources/hygiene.py (Story 9.2, CAP-8) is WIRED IN as a warn-only source (dispatch + detector list), not deleted; it reports 5 orphan-file warnings today. (2) marshal's already-specced follow-up review chain (66.1, 72.1 -> 73.1 -> 73.2, CAP-281) runs in this wave, LAST, with a cap on how many follow-up reviews one drain schedules (218 finished specs carry followup_review_recommended: true). New chains: marshal finalize writes the Tier-3 feed row (+ DW-FU-53-2-4), marshal lint-types in dispatch verification (+ remove the '28' wildcard), doctor verified-line must cite file:line, doctor surface globs that match nothing, doctor env-hygiene walk prunes untracked dirs, steward helm in platform CI with skipped chart tests failing under CI.
