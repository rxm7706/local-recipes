---
name: "2026-10-01-marshal-story-79-1-dispatch-land-finalize-s-scan"
description: "2026-10-01 marshal Story 79.1: dispatch_land_finalize's _scan_promotions reads origin/main and local main commit subjec…"
metadata:
  type: project
---

2026-10-01 marshal Story 79.1: dispatch_land_finalize's _scan_promotions reads origin/main and local main commit subjects BEFORE finalize's first fetch, so any gate fed only by scan.combined_subjects is closed right after a GitHub merge (reproduced with real git: before the fetch the key is not corroborated, after it it is). Story 79.1's own gate (_landing_corroboration) fetches origin/main itself. The Tier-3 spec promotion (_execute_promotion_plan, deploy-promote-commit) is still fed the pre-fetch subjects and probably never fires on the normal path (6 of 38 finalize journals carry one, none of the last 8); deferred, because widening it would let commit_paths commit onto the primary checkout (CAP-233) and needs its own Spec decision. A test that stubs the scan cannot see this class of bug: pin gate ordering with a real-git test.
