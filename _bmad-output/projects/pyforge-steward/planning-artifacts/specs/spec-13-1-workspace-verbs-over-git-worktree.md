---
title: Workspace verbs over git worktree
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
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
  - summary: >-
      No tracked schema/example for `.steward/workspaces.yaml`.
    evidence: |-
      Review noted operators only get a gitignore entry; shape is discoverable only from code.
    severity: low
  - summary: >-
      Distinct slugs that normalize to the same sibling path (e.g. a/b vs a-b) can collide.
    evidence: |-
      scratch_path_for replaces `/` with `-` without collision detection.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
    severity: low
  - summary: >-
      Stale bookkeeping entries (missing path / moved checkout) stay listed by ls.
    evidence: |-
      CAP-2 deliberately avoids per-worktree git; staleness is out of 13.1.
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

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q` → **747 passed**
- Unit tests for start/ls/clean + foreign-worktree invisibility (in `tests/unit/test_workspace.py`)

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 4, medium 3, low 1)
- defer: 3: (high 0, medium 0, low 3)  # plus 3 more appended in frontmatter this pass
- reject: 12
- addressed_findings:
  - `[high]` `[patch]` start rolls back orphan worktree if bookkeeping save fails after `git worktree add`
  - `[high]` `[patch]` clean deletes local branch after archive so same-slug restart works
  - `[high]` `[patch]` verification: declined-confirm, CLI `--from`, EXIT_FAILED duplicate, non-JSON path print, slug reuse
  - `[high]` `[patch]` clean persists bookkeeping for already-archived entries if mid-loop archive fails
  - `[medium]` `[patch]` load_bookkeeping guards non-mapping root + YAMLError
  - `[medium]` `[patch]` merge-base non-{0,1} raises WorkspaceError
  - `[medium]` `[patch]` Duty.run maps RuntimeError/OSError to ok=False
  - `[low]` `[patch]` interfaces Duty docstring lists sync + workspace

## Auto Run Result

- **Summary:** Added `steward workspace start|ls|clean` as a sixth duty. Bookkeeping in `.steward/workspaces.yaml` enforces own-worktrees-only; clean archives to `.steward/workspace-archive/` (tar.gz) then removes the worktree and local branch — never raw-deletes without archive. Foreign Marshal-style loop-home worktrees are invisible to ls/clean (tested).
- **Files changed:**
  - `workspace.py` (new) — duty implementation + review hardenings
  - `cli.py` — wire duty + verbs + `--json` / `--from` / `--merged-only`
  - `interfaces.py` — Duty docstring lists registered duties
  - `test_workspace.py` (new) — CAP coverage + review verification patches
  - `test_cli.py` — six-duty expectations
  - `.gitignore` — ignore machine-local bookkeeping/archives
  - `README.md` — list `workspace` among duties
  - this spec — status done + triage/result
- **Review findings:** 8 patches applied (4 high, 3 medium, 1 low); 6 low deferred; ~12 rejected (out of scope / intentional safety / process).
- **Follow-up review recommendation:** true (patched: high 4, medium 3, low 1 → any high ⇒ true; score also ≫ 5)
- **Verification:** full pyforge-steward suite **747 passed**.
- **Residual risks:** concurrent bookkeeping writers; no auto-fetch of `origin/main`; freshly created equal-tip branches look "merged" to `--merged-only`; slug path normalization collisions.
