---
title: 'Structure-graph (codegraph) for dispatch — provisioning cost weighed against a single-story session'
type: 'spike'
created: '2026-09-10'
status: 'in-progress'
review_loop_iteration: 0
baseline_revision: 'd7280cee9791e1602a6e62d98df8ce2a2e0bd7c9'
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `structure-graph` (token-economy CAP-3) needs a real codegraph index build
(`codegraph init -y`), and Story 28.3's own docstring already flags "a first codegraph index
build runs unattended and can take minutes." For a LOOP HOME running many stories across its
lifetime, that one-time cost amortizes — Story 28.33 already wired the loop-home half directly,
confirmed live (`marshal preflight pyforge-marshal` built a real 229MB `.codegraph/codegraph.db`
in ~21s, well under the 900s ceiling). For a DISPATCH worktree living exactly one story's
lifetime, it may not: nothing has measured whether the index-build cost exceeds what that single
story's own file navigation would have spent without it.

**Approach:** A spike, not an implementation. Measure, on a representative dispatch worktree and
a representative story, (a) `codegraph init -y`'s real wall-clock/token cost for this repo's
actual size, and (b) the token cost that same story's own file navigation would have spent
without a graph. Record the comparison as a real artifact (matching Story 28.5's own
benchmark-artifact precedent) — not an assumption. The spike's own recommendation (build it
per-worktree, share a repo-level index across worktrees if `kit.py`'s existing `init`-vs-`sync`
split supports incremental sync from a shared base, or leave this layer spin-only) is itself the
acceptance criterion. This story does not pre-commit to writing follow-on code.

## Boundaries & Constraints

**Always:**
- The measurement is against a representative dispatch worktree and a representative story —
  real numbers, not estimates.
- The comparison (build cost vs. navigation cost without it) is recorded as a real artifact.
- The recommendation itself — build per-worktree, share a repo-level index, or stay spin-only —
  is the deliverable.

**Never:**
- Never pre-commit to implementing the recommendation in this story — a "build it" verdict gets a
  separate, scoped follow-on story, filed by the spike's own findings.
- Never touch Story 28.33's already-shipped loop-home wiring — this spike's scope is strictly the
  dispatch-worktree provisioning-cost question, narrowed 2026-09-10 when 28.33 split off the
  spin/loop-home half.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Index-build cost measured | A representative dispatch worktree, `codegraph init -y` run | Real wall-clock + token cost recorded | N/A |
| Navigation-without-graph cost measured | The same representative story, no codegraph available | Real token cost of file navigation recorded | N/A |
| Recommendation reached | Both costs compared | One of: build per-worktree / share a repo-level index / stay spin-only — recorded as the acceptance artifact | N/A |
| "Build it" verdict | The comparison favors building | A follow-on implementation story is filed separately, scoped by these findings | This story itself does not implement it |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/kit.py` — the existing `init`-vs-`sync` split a "shared repo-level index" recommendation would build on
- A new benchmark artifact (location matching Story 28.5's own precedent) — the measured comparison

## Tasks & Acceptance

**Execution:**
- `spike` — measure `codegraph init -y`'s real cost on a representative dispatch worktree.
- `spike` — measure the same representative story's file-navigation token cost without a graph.
- `docs` — record the comparison as a real benchmark artifact.
- `decision` — record the recommendation (build per-worktree / share a repo-level index / spin-only) as this story's own acceptance criterion.

**Acceptance Criteria:**
- Given `structure-graph`'s loop-home half already shipped (Story 28.33) and its dispatch-worktree half has never been measured, when this spike runs a representative dispatch worktree and story through both the index-build path and the no-graph navigation path, then both real costs are recorded as a benchmark artifact.
- And the spike's own recommendation — build it per-worktree, share a repo-level index (if `kit.py`'s `init`/`sync` split supports it), or leave this layer spin-only — is the acceptance criterion, not a specific implementation.
- And if the recommendation is "build it," a separate follow-on story is filed, scoped by these findings — never implemented inside this spike.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: full suite green

## Spec Change Log

## Review Triage Log
