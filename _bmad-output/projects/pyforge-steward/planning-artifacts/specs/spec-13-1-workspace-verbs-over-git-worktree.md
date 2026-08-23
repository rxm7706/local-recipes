---
title: Workspace verbs over git worktree
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 686de783c4cf20a8c1edd71b36e802b523c87265
deferred:
  - summary: >-
      Bookkeeping YAML is not locked; concurrent start/clean in one checkout can race.
    evidence: |-
      save_bookkeeping uses atomic_write but two processes can still interleaved
      read-modify-write over .steward/workspaces.yaml.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
    severity: low
  - summary: >-
      start does not `git fetch` before branching from origin/main.
    evidence: |-
      Thin git wrap: if origin/main is stale or missing locally, start fails with a
      git error rather than refreshing remotes first.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
    severity: low
  - summary: >-
      A freshly started branch with no unique commits is treated as merged by --merged-only.
    evidence: |-
      merge-base --is-ancestor is true when tip equals source; accurate but surprising
      immediately after start.
    severity: low
---

<intent-contract>

## Intent

**Problem:** Scratch worktrees for steward work lack first-class CLI verbs — operators improvise git worktree commands without bookkeeping or an own-worktrees-only boundary (spec-scratch-worktree-lifecycle CAP-1/2/4/5).

**Approach:** Add `steward workspace start|ls|clean` under pyforge-steward: start creates a worktree from `origin/main` (or `--from`), prints path, records bookkeeping; ls enumerates cheaply without per-worktree subprocess; clean archives-not-deletes (bmad-loop discipline), optional `--merged-only`. All verbs emit `--json`. HARD: ls/clean never see Marshal loop-home worktrees (bookkeeping enforces; test plants foreign worktree and proves invisible).

## Acceptance Criteria

- `steward workspace start <slug> [--from <branch>]` creates worktree, prints path, records bookkeeping; default from `origin/main`.
- `steward workspace ls` cheap enumeration; `--json`.
- `steward workspace clean [--merged-only]` archive-not-delete; `--json`.
- Own-worktrees-only: foreign Marshal loop-home worktree invisible to ls/clean (tested).

## Boundaries & Constraints

**Never:** Touch Marshal loop homes. No `workspace status` / multi-repo set (13.2–13.4). Never `scripts/bmad-switch`.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py` — start/ls/clean + bookkeeping + archive-not-delete
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — sixth duty `workspace` + verb parsers
- `src/shared/packages/pyforge-steward/tests/unit/test_workspace.py` — CAP-1/2/4/5 coverage incl. foreign loop-home invisibility
- `.gitignore` — ignore `.steward/workspaces.yaml` and `.steward/workspace-archive/`

## Verification

- `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q` → **742 passed**
- Unit tests for start/ls/clean + foreign-worktree invisibility (in `tests/unit/test_workspace.py`)

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 3: (high 0, medium 0, low 3)
- reject: 8
- addressed_findings:
  - `[low]` `[patch]` README duties line now lists `workspace` alongside the existing five.

## Auto Run Result

- **Summary:** Added `steward workspace start|ls|clean` as a sixth duty. Bookkeeping in `.steward/workspaces.yaml` enforces own-worktrees-only; clean archives to `.steward/workspace-archive/` (tar.gz) then removes the worktree registration — never raw-deletes without archive. Foreign Marshal-style loop-home worktrees are invisible to ls/clean (tested).
- **Files changed:**
  - `workspace.py` (new) — duty implementation
  - `cli.py` — wire duty + verbs + `--json` / `--from` / `--merged-only`
  - `test_workspace.py` (new) — CAP coverage
  - `test_cli.py` — six-duty expectations
  - `.gitignore` — ignore machine-local bookkeeping/archives
  - `README.md` — list `workspace` among duties
  - this spec — status done + triage/result
- **Review findings:** 1 low patch applied (README); 3 low deferred; 8 rejected (out of scope / intentional safety / already covered).
- **Follow-up review recommendation:** false (patched: high 0, medium 0, low 1 → score 1 < 5)
- **Verification:** full pyforge-steward suite 742 passed after rebase onto `origin/main`.
- **Residual risks:** concurrent bookkeeping writers; no auto-fetch of `origin/main`; freshly created equal-tip branches look "merged" to `--merged-only`.
