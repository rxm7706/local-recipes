---
title: "70.1: Steward reads the workspace source and branch, and origin/main, by their full refs"
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pyforge.steward.workspace` hands git its recorded source (`origin/main`) and branch by short name in `start` (`worktree add`), `status` (`_ahead_behind`, `_branch_merged_into`) and `clean` (`--merged-only`'s `_branch_merged_into`, `_source_commit`, the branch-drop `_commit_of`). Git resolves a short name to `refs/tags/<n>` and `refs/heads/<n>` before `refs/remotes/<n>`. Probed on the old code: with a local branch or tag named `origin/main` at an unmerged workspace's tip, `clean --merged-only` archived the worktree and deleted its branch (its commits then reachable only through the stray ref); `status` reported it merged; `start` refused ("ambiguous object name"); and a tag named like the branch stood in for it in the merged check. Two smaller reads: the platform's deliberate copy of the kit's diff guard (`src/platform/tests/test_warden_portal_audit_start_get.py`) diffs from `origin/main`, and the `tea-test-review` pixi task passes `--base origin/main` — as does its one documented caller, marshal's review lens (`_bmad/custom/bmad-review.toml`), whose own `--base` replaces the task's (`DW-steward-platform-diff-guard-short-origin-main-2026-09-27`, steward's half of `DW-warden-tea-advisory-short-base-2026-09-27`).

**Approach:** two private helpers in `workspace.py` — `_source_ref(source)` (`origin/<b>` → `refs/remotes/origin/<b>`, anything else unchanged) and `_branch_ref(branch)` (`refs/heads/<branch>`) — used at every git read of a record's source and branch; `start` passes `_source_ref(from_ref)` to `worktree add` and records `from_ref` as written, so old bookkeeping reads the same way. The platform guard's `rev-parse`, skip text and `diff` name `refs/remotes/origin/main` (the platform CI fetch already writes that ref). The pixi task passes `--base refs/remotes/origin/main` and its description says so; the review lens defaults to the same and writes a stated `origin/<b>` as `refs/remotes/origin/<b>`; `environment.yaml` is re-exported (tasks are not in it, so it should not change).

Ledger key: `70-1-steward-reads-the-workspace-source-and-branch-and-origin-main-by-their-full-refs`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-158 (extends CAP-107 / CAP-155 / CAP-157); `pyforge-warden:CAP-23`; `marshal:CAP-272` (the kit the platform guard copies).

## Acceptance Criteria

- Given a local branch or tag named `origin/main` at an unmerged workspace's tip When `workspace clean --merged-only` runs Then the workspace is skipped `not-merged`, its worktree and branch kept
- Given a tag named like the workspace's branch, on the source When `clean --merged-only` runs Then the workspace is skipped `not-merged`
- Given the same shadow When `workspace status` runs Then it reports the branch ahead and unmerged
- Given a local branch or tag `origin/main` at a local-only commit When `workspace start` runs on its default source Then the new worktree starts at `refs/remotes/origin/main` and the record's source reads `origin/main`
- Given no shadow When any of them runs Then every result is unchanged (a merged workspace still cleans)
- Given the platform CI's fetched `refs/remotes/origin/main` When the platform guard runs Then it diffs that ref, still importing no `pyforge.*`

## Boundaries & Constraints

**Always:** anything `clean` cannot prove still archives (CAP-155); recorded sources stay as written.

**Never:** rewrite bookkeeping; import `pyforge.*` in `src/platform`; change a caller's explicit non-`origin/` source.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| source `origin/main` | any read | `refs/remotes/origin/main` | missing ref → the existing error path |
| source `origin/release/x` | any read | `refs/remotes/origin/release/x` | — |
| source a sha / `refs/...` / local branch | any read | unchanged | — |
| branch `<slug>` | merged / ahead-behind | `refs/heads/<slug>` | — |
| shadow at the unmerged tip | `clean --merged-only` | skipped `not-merged` | — |
| no shadow, merged | `clean --merged-only` | cleaned as before | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-158.
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 (night) — Proposed: steward reads `origin/main` and its own branches by their full refs*.
Deferred-work: closes `DW-steward-platform-diff-guard-short-origin-main-2026-09-27`; with warden Story 13.1, `DW-warden-tea-advisory-short-base-2026-09-27`.
Ledger key: `70-1-steward-reads-the-workspace-source-and-branch-and-origin-main-by-their-full-refs`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass.

## Review Triage Log

- **Review 1 (2026-09-27, independent agent) — FAIL, then fixed:**
  - [fixed] MEDIUM: marshal's review lens (`_bmad/custom/bmad-review.toml`) passed its own `--base origin/main`,
    and TEA keeps the last `--base` (commander) -- the lens now names `refs/remotes/origin/main`; CAP-158 amended.
  - [fixed] MEDIUM: no test pinned the confirmed clean's branch-drop proof or the landed proof past a shadow --
    both added; each full-ref read in `workspace.py`, reverted alone, now fails a test (7/7 mutants killed).
  - [fixed] LOW-MEDIUM: CAP-157's success still listed a shadowed source among the cases that archive -- amended
    (memlog, then its rendered line); its two tests renamed to what they prove (an unlanded commit past a shadow).
  - [fixed] LOW: `_branch_ref` passed a slug beginning `refs/` through (`refs/heads/main` read the real `main`) --
    it always prefixes now; a test pins it.
  - [fixed] nit: a test docstring said the deleted branch's commits existed nowhere else -- they stayed reachable
    through the stray ref.
