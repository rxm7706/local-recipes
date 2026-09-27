---
title: '61.1: Every local-branch read names the full ref'
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-60-1-every-remote-tracking-read-names-the-full-ref.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** git resolves a short name through `refs/<n>`, `refs/tags/<n>`, `refs/heads/<n>` in that order, so a tag named `main` stands in for the local branch `main`. A probe on 2026-09-27 showed what that does to marshal's reads: `log main`, `show main:<path>` and `merge main` read the tag's commit with only a warning on stderr; `push origin main:main` and `worktree add -b <b> <path> main` refuse as ambiguous. Story 60.1 closed this for remote-tracking refs. Marshal still hands git its local branches by short name in:
- the landing subjects `status`, `deploy` (merge route and `batch-pr`), `retire` and `dispatch land` read (`commit_subjects(root, "main")` and the policy's base);
- `deploy land-story`'s `--since` default (`merge_base(branch, "main")`);
- `deploy batch-pr`'s and `land`'s merge base, wave range (`<sha>..<head_branch>`), base subjects and changed-files base;
- the gate's `--scope-check` diff base;
- the start point `init`, the loop-home adapter and `dispatch` mint a branch from (`add_worktree(base="main")`);
- the dispatch supervisor's landing subjects;
- the stage-push supervisor's retired-branch check, `merge_base(commit, <station branch>)`;
- the landing heal: its probe default (the local base), and its reads of the dispatch branch — the merge-tree probe, the merge base, the ledger text, and the local-`main` advance's merge;
- `GitVcs.push`'s source refspec.

And `core/policy._valid_landing_base_branch` accepts any non-empty string, so `landing_base_branch = "origin/main"` would reach every read above.

**Approach:** `core/refs.py` gains `local_branch_ref(branch) -> "refs/heads/<branch>"`. Every call site above wraps the branch it reads in it, at the call — the branch *name* stays a name wherever it is also used as one (`merge_branch(into=)`, `resolve_ref`, `is_branch_merged`, the forge's PR base, messages). `GitVcs.push` names its source `refs/heads/<branch>`; `<branch>@{upstream}` stays bare (the full form fails there). `_valid_landing_base_branch` refuses a full refname (`refs/…`), a remote's branch (`origin/…`), and any value git's branch-name rules refuse. A meta test scans every call to a `VcsPort` read's revision argument and flags a bare-name literal, a module constant bound to one, or a name reading `*branch*`, `base` or `into` that is not wrapped in `local_branch_ref`.

Ledger key: `61-1-every-local-branch-read-names-the-full-ref`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-271 (FR-217); CAP-270 (60.1).

## Acceptance Criteria

- Given a tag named `main` on an older commit than the branch `main` When status, deploy, retire or dispatch land read the landing subjects Then they read the branch's history
- Given the same tag When deploy or land compute the merge base, the wave range and the changed-files base Then each reads the branch
- Given the same tag When init, the loop-home adapter or dispatch mints a branch from `main` Then the new branch starts at the branch's tip (today: the mint refuses as ambiguous)
- Given a tag named like the dispatch branch When the landing heal probes, reads and merges the dispatch branch Then it reads the branch, and the local-`main` advance's push succeeds with a tag named `main` present
- Given `landing_base_branch = "origin/main"`, `"refs/heads/main"` or `"bad..name"` When the policy composes Then the value is refused with MRS-POLICY-002 and the default `main` holds; `"release/2026"` is accepted
- Given the package source When scanned Then no revision argument of a `VcsPort` read receives a bare local branch name (a meta test, every known spelling in its self-test)
- Given no tag shadowing a branch When any of these runs Then its behaviour is unchanged

## Boundaries & Constraints

**Always:** the helper lives in `core/refs.py`; the wrap is at the read, so a name used as a name elsewhere stays one; `core/` stays pure (AD-4).

**Ask First:** widening scope to another station's scripts.

**Never:**
- Do not qualify an argument git reads as a branch name: `branch -D`, attaching an existing branch to a worktree (`add_worktree`'s attach path is bare on purpose), `<branch>@{upstream}`.
- Do not change what is fetched, pushed or merged when no tag shadows a branch.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no shadow | ordinary repo | identical results | — |
| tag `main` on an older commit | branch `main` ahead | every read uses the branch | — |
| tag named like a dispatch branch | heal probe and merge | reads and merges the branch | — |
| push with tag `main` present | local-main advance | push succeeds (source `refs/heads/main`) | a rejected push fails as before |
| `landing_base_branch = "origin/main"` | project policy | MRS-POLICY-002, default holds | — |
| `landing_base_branch = "release/2026"` | project policy | accepted; reads `refs/heads/release/2026` | a missing branch fails as before |
| `deploy land-story --since <rev>` | operator-typed revision | passed through untouched | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-271 (FR-217).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (late) — Proposed: marshal names its own branches too, never a name a tag can wear*.
Deferred-work: closes `DW-marshal-local-branch-short-names-2026-09-27`.
Ledger key: `61-1-every-local-branch-read-names-the-full-ref`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log
