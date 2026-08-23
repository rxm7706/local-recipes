---
title: A repo set opens as one workspace
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 69298271500222597047416a4edbf7104280ceb7
---

<intent-contract>

## Intent

**Problem:** Multi-repo features still require hand-cut worktrees per repo; there is no declarative set that opens as one workspace (spec-multi-repo-workspaces CAP-1).

**Approach:** Extend steward workspace so `steward workspace start <feature>` against a declarative `[projects.<slug>]` repo set cuts one worktree per registered repo on branch `f-<feature>`, generates a `.code-workspace`, names missing members (never guesses), and records a dated Spec Change Log entry resolving the registry-location open question.

## Acceptance Criteria

- Declarative `[projects.<slug>]` repo set supported.
- `steward workspace start <feature>` creates one worktree per registered repo on `f-<feature>`.
- Generates a `.code-workspace` file.
- Missing members are named, never guessed.
- Registry-location open question resolved with a dated Spec Change Log entry.

## Boundaries & Constraints

**Never:** Implement 13.4 teardown/reporting. Own-worktrees-only HARD rule still holds. Never `scripts/bmad-switch`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py` — repo-set load/start, `.code-workspace` generation
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — start help text
- `src/shared/packages/pyforge-steward/tests/unit/test_workspace_repo_set.py` — multi-repo start + missing-member naming
- `.steward/repo-sets.example.yaml` — tracked example registry
- [spec-multi-repo-workspaces/SPEC.md](./spec-multi-repo-workspaces/SPEC.md) — registry-location Spec Change Log

## Spec Change Log

### 2026-08-23 — Registry location

- **Decision:** Tracked **`.steward/repo-sets.yaml`** with top-level `projects:` (see parent spec log).
- **Why:** Same `.steward/` operational-config precedent as sync/budget/keys; paths are operator-declared.
- **Known-bad avoided:** Inventing `pyforge.toml`; guessing clone paths for absent members.

## Verification

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q` — **759 passed**

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

- **Summary:** `steward workspace start <feature>` detects a `projects.<feature>` entry in `.steward/repo-sets.yaml`, creates one worktree per registered repo on branch `f-<feature>`, writes `.steward/workspaces/f-<feature>.code-workspace`, and fails with named missing members (no partial start, no path guessing). Single-repo 13.1 start unchanged when the slug is not a registered project.
- **Files changed:** `workspace.py`, `cli.py`, `test_workspace_repo_set.py`, `.steward/repo-sets.example.yaml`, `spec-multi-repo-workspaces/SPEC.md`, this spec.
- **Review findings:** none requiring patch.
- **Follow-up review recommendation:** false
