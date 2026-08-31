---
title: Status and the feed-mirror decision
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 3cd7abf25bd60a1c4b714af152d45dbc95f31842
deferred:
  - summary: >-
      status ahead/behind uses local source ref; no fetch of origin before counting.
    evidence: |-
      Same thin-git posture as 13.1 start (no auto-fetch). Stale origin/main makes
      behind under-count until the operator fetches.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** `steward workspace ls` deliberately avoids per-worktree git cost; operators still need dirty/ahead/behind/merged status, and two open questions from spec-scratch-worktree-lifecycle CAP-3 remain unresolved (Tier-3 feed rsync-mirror verb vs join `start`; whether `workspace update` exists).

**Approach:** Add `steward workspace status [<slug>]` that pays the per-worktree git-subprocess cost. Record dated Spec Change Log decisions for the two open questions — decisions recorded, not silently implemented beyond status.

## Boundaries & Constraints

**Always:** Own-worktrees-only HARD (bookkeeping only); every verb `--json`; status reports dirty/clean, ahead/behind vs source, merged?; `ls` cost/shape unchanged.

**Block If:** Intent requires inventing multi-repo set behavior (13.3–13.4).

**Never:** Implement multi-repo set (13.3–13.4). Never `scripts/bmad-switch`. Do not silently invent `workspace update` without the logged decision. Do not join Tier-3 rsync into `start` in this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All owned | bookkeeping has N worktrees | status lists N rows with dirty/ahead/behind/merged | No error |
| Named slug | `status <slug>` for owned slug | one row for that slug | No error |
| Unknown slug | slug not in bookkeeping | duty ok=False; clear error | EXIT_FAILED / error JSON |
| Clean equal tip | no dirty; tip == source tip | dirty=false; ahead=0; behind=0; merged=true | No error |
| Dirty tree | uncommitted change in worktree | dirty=true | No error |
| Ahead | unique commits on branch | ahead>0; merged=false | No error |
| Foreign invisible | Marshal-style path on disk, not in bookkeeping | never appears in status | No error |
| Missing path | bookkeeping entry path gone | row with error/unreachable signal; other rows still reported | duty still ok=True for reachable; document per-row |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py` — extend: `status_workspaces`, formatters; add `"status"` to `_WORKSPACE_VERBS`; reuse `_branch_merged_into`, `_git`/`_git_ok`, `load_bookkeeping` (do not scan `git worktree list` for discovery)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `_add_workspace_subparsers`: add `status` optional slug + `--json`; metavar `{start,ls,clean,status}`
- `src/shared/packages/pyforge-steward/tests/unit/test_workspace.py` — matrix coverage + foreign invisibility for status
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-scratch-worktree-lifecycle/SPEC.md` — close Open Questions via dated Spec Change Log here (and optionally a one-line pointer there); **do not implement** mirror/`update` verbs

## Tasks & Acceptance

**Execution:**
- `workspace.py` — add `status_workspaces(slug=None)` returning per-owned-worktree health (dirty, ahead, behind, merged) via git in each path; optional slug filter; unknown slug → WorkspaceError
- `workspace.py` / `cli.py` — wire `status` verb + human/JSON formatters; keep start/ls/clean behavior identical
- `test_workspace.py` — cover matrix rows + foreign worktree never listed by status
- this spec — Spec Change Log entries dated 2026-08-23 for the two CAP-3 open questions (below)

**Acceptance Criteria:**
- Given owned worktrees, when `steward workspace status [--json]`, then each row reports dirty/clean, ahead, behind, and merged? against the record's source
- Given a slug, when `steward workspace status <slug>`, then only that owned worktree is reported (or error if not owned)
- Given a foreign Marshal-style worktree on disk not in bookkeeping, when status runs, then it is invisible
- Given the two CAP-3 open questions, when this story lands, then dated Spec Change Log entries resolve them without implementing mirror or `update`

## Spec Change Log

### 2026-08-23 — CAP-3 open question: Tier-3 feed rsync-mirror

- **Decision:** Own verb, **deferred** — does **not** join `start` in Story 13.2 (or later without a dedicated story).
- **Why:** `start` stays a thin `git worktree add` + bookkeeping. Tier-3 `implementation-artifacts/` mirroring is only needed when a story touches the gitignored feed; baking rsync into every `start` would surprise operators and couple CAP-1 to BMAD Tier-3 layout. A future story may add an explicit verb (name TBD, e.g. `workspace mirror-feed`) when a real ritual needs it.
- **Known-bad avoided:** Silently teaching `start` to rsync without a logged decision; inventing a half-implemented mirror in 13.2.

### 2026-08-23 — CAP-3 open question: does `workspace update` exist?

- **Decision:** **No** — `workspace update` does **not** exist. Omitted until a real observed need surfaces (matches the Dream's "Omitted, not ruled out").
- **Why:** No landing-pass evidence in Epic 13 required fast-forwarding a scratch branch from its source as a named verb; operators can `git merge`/`rebase` inside the worktree. Inventing the verb now would expand surface without demand.
- **Known-bad avoided:** Silently shipping `workspace update` without a decision; blocking status on inventing update semantics.

## Design Notes

Status fields (JSON keys): `slug`, `path`, `branch`, `source`, `dirty` (bool|null), `ahead` (int|null), `behind` (int|null), `merged` (bool|null). Optional `error` string when the path is missing or git fails for that row — when `error` is set, the four health fields are JSON null (never false/0 placeholders).

Ahead/behind: `git rev-list --left-right --count <source>...<branch>` from the worktree (or root with refs). Dirty: `git status --porcelain` in the worktree path. Merged: reuse `_branch_merged_into(root, branch, source)`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 1: (high 0, medium 0, low 1)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` unreachable status rows used dirty=false/ahead=0 placeholders that could be misread as healthy — health fields are now JSON null when `error` is set; Design Notes + test updated

## Auto Run Result

- **Summary:** Added `steward workspace status [<slug>]` (CAP-3): per-owned-worktree dirty/ahead/behind/merged via git in each path; optional slug filter; foreign Marshal loop homes stay invisible; missing paths report per-row `error` with null health fields. Dated Spec Change Log resolves: Tier-3 feed rsync-mirror → own verb deferred (not join `start`); `workspace update` → does not exist. Parent `spec-scratch-worktree-lifecycle` open questions cleared.
- **Files changed:**
  - `workspace.py` — `WorkspaceStatus`, `status_workspaces`/`status_of`, formatters, wire `status` verb
  - `cli.py` — `status` subparser with optional slug + `--json`
  - `test_workspace.py` — CAP-3 matrix + foreign invisibility + missing-path soft-fail
  - `spec-13-2-…` — Spec Change Log decisions + triage/result
  - `spec-scratch-worktree-lifecycle/SPEC.md` — open questions closed; pointer to 13.2 log
- **Review findings:** 1 medium patch applied; 1 low deferred (no-fetch); ~6 rejected (out of scope / intentional decisions / cosmetic).
- **Follow-up review recommendation:** false (patched: medium 1, low 0 → score 3 < 5; no high)
- **Verification:** `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests -q` → **754 passed** (workspace unit 22 passed after patch).
- **Residual risks:** stale remote refs without fetch; concurrent bookkeeping writers (13.1 deferred).
