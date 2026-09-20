---
title: 'Dispatch structure-graph — shared index provisioning via sync-from-base'
type: 'feature'
created: '2026-09-10'
status: 'draft'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/benchmarks/structure-graph-dispatch-28-31.json
declared_low_risk: false
parent_spike: spec-28-31-structure-graph-codegraph-for-dispatch-provisioning-cost-weighed-against-a-single-story-session
archived: '2026-09-20'
archive_reason: 'unminted design draft from the 28.31 spike (auto-checkpoint 6a674c4f14, 2026-09-10); never a ledger row, never an epics.md story. Kept per steward 41.1 (archived, never deleted); tracked as marshal DW-FU-28-31-1.'
---

<intent-contract>

## Intent

**Problem:** Story 28.31 measured dispatch-worktree `codegraph init -y` at ~19s / 222MiB
against ~52k estimated navigation tokens for the same representative story. Fresh init
per one-story dispatch worktree duplicates cost; `codegraph sync -q` from a shared base
index completes in ~4s.

**Approach:** At dispatch worktree creation, when `[context."structure-graph"]` is enabled,
copy or reference the primary checkout / loop-home `.codegraph/` base and run
``build_codegraph_index(..., stale=True)`` (sync) — never ``init`` — unless no base exists.

## Boundaries & Constraints

**Always:** Reuse `seed/verbs/kit.py`'s existing init-vs-sync split. Degrade with a named
finding when codegraph is unavailable.

**Never:** Re-run Story 28.33's loop-home step-01 reference work. Init per dispatch worktree
when a shared base index is reachable.

</intent-contract>

## Tasks & Acceptance

**Execution:** Scoped by Story 28.31 benchmark artifact — implement only after operator
promotes this draft from the spike recommendation.

**Acceptance Criteria:**
- Given a dispatch worktree and an existing repo-level `.codegraph/codegraph.db`, when
  structure-graph is enabled, then provisioning runs sync not init and completes under the
  sync ceiling.
- Given no base index, when structure-graph is enabled for dispatch, then provisioning
  degrades with a named finding and dispatch proceeds without an index.
