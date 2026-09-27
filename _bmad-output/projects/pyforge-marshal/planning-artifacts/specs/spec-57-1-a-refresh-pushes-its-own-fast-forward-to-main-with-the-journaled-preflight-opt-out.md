---
title: '57.1: A refresh pushes its own fast-forward to `main` with the journaled preflight opt-out'
type: 'fix'
created: '2026-09-27'
status: 'in-review'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `marshal refresh` fast-forwards each clean `loop/<slug>` home to `origin/main` and pushes the branch. The repo's `pre-push` hook (steward CAP-154) runs the full ~10-minute `pr-preflight` for each push, although every pushed commit is already on `main` and passed CI there: eight homes cost ~80 minutes on 2026-09-27, or the operator's manual `PYFORGE_PREFLIGHT_SKIP=1`. Steward's hook-side "nothing new" skip (Story 68.2) was refused in review — under pre-commit the hook sees only the first ref of a multi-ref push — so only the tool that made the push can prove it carries nothing new.

**Approach:** `VcsPort.push` gains a keyword-only `proven_on_main_sha: str | None = None` (additive; every existing caller unchanged). `cli/refresh.py` runs `commits_behind` and `fast_forward` on the full refname `refs/remotes/origin/<base>` and, only when `base == "main"` and its own fast-forward succeeded, passes the sha it fast-forwarded to. `GitVcs.push` re-checks that sha with `git merge-base --is-ancestor <sha> refs/remotes/origin/main` (a `VcsCommandError` refusal otherwise), pushes exactly `<sha>:refs/heads/<remote_branch>`, and carries the repo's journaled opt-out to that one `git push` process as `PYFORGE_PREFLIGHT_SKIP=1` and `PYFORGE_PREFLIGHT_SKIP_REASON=marshal refresh: loop/<slug> at <sha12> is a fast-forward to origin/main; every pushed commit is already on origin/main` through the POSIX `env` utility (the process port takes no environment; nothing is exported to anything else). Where `env` is not on `PATH` (win-64) the push goes through the preflight instead. Any other `--base` passes no proof.

Ledger key: `57-1-a-refresh-pushes-its-own-fast-forward-to-main-with-the-journaled-preflight-opt-out`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-267 (FR-213); cross-station: `spec-pyforge-steward` CAP-154/156 (the hook and its journal).

## Acceptance Criteria

- Given a clean loop home behind `origin/main` and the default base When `marshal refresh` runs Then its push passes the sha it fast-forwarded to as the proof
- Given `--base` other than `main` When `marshal refresh` runs Then its push passes no proof
- Given a repo with a real `pre-push` hook When `GitVcs.push` runs with a proven sha Then the hook sees `PYFORGE_PREFLIGHT_SKIP=1` and a reason naming the branch, `origin/main` and the sha; without one, it sees neither variable
- Given a sha not on `refs/remotes/origin/main` — a local branch named `origin/main` included — When `GitVcs.push` is given it as the proof Then it refuses and nothing is pushed
- Given a commit made on the branch after the fast-forward When the proven push runs Then exactly the proven sha is pushed
- Given every other push caller When it pushes Then its behaviour is unchanged

## Boundaries & Constraints

**Always:** the proof is `refresh`'s own successful fast-forward to `refs/remotes/origin/main`, re-checked by the adapter, and the commit pushed is the proven one; the opt-out is the existing journaled one.

**Never:**
- Do not export the opt-out beyond the one `git push` process.
- Do not pass a proof for a home that was already current (no push happens) or whose fast-forward failed.
- Do not change the hook (steward's); do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| behind, base main | clean home, 2 behind | ff to refs/remotes/origin/main; push the proven sha with the opt-out | push failure → existing WARN |
| behind, other base | `--base release` | ff to refs/remotes/origin/release; push without a proof | preflight runs in the hook |
| shadowing ref | a local branch or tag named `origin/main` | never consulted; the proof is checked against `refs/remotes/origin/main` | a sha not on it → `VcsCommandError`, nothing pushed |
| branch moved after the ff | a commit made on the home before the push | the proven sha is pushed; the later commit stays local | — |
| no `env` utility | win-64 | push without the opt-out | preflight runs in the hook |
| already current | 0 behind | no ff, no push | — |
| dirty home | uncommitted changes | ff refused, no push | existing refusal |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-267 (FR-213).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (later) — Proposed: a loop-home refresh does not pay a preflight for `main`'s own commits*.
Ledger key: `57-1-a-refresh-pushes-its-own-fast-forward-to-main-with-the-journaled-preflight-opt-out`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, commit `db044dad6a` (the 68.x pair's review 2) — PASS with lows

Verified clean: the opt-out reaches only the one `git push` process and its hook; any `--base` other than `main` gets none; a failed base fetch stops the fleet before any home; refresh pushes one ref per `git push`, so pre-commit's first-ref-only hand-off does not apply; the reason cannot be injected into (no shell, hex sha, `check-ref-format` names). Under real pre-commit 4.6.2 a push without a proof was refused by a failing preflight and one with a proof passed, journaled.

- `[low]` `[patch]` **L-B — a local ref named `origin/main` could stand in for the remote-tracking ref.** `tip_ref` was the short name `origin/<base>`; git resolves `refs/heads/origin/main` (or a tag) before `refs/remotes/origin/main`, and the proof was a text comparison. Probe: a local branch `origin/main` with one unverified commit — refresh fast-forwarded to it and pushed it with the opt-out. **Fix:** `commits_behind` / `fast_forward` run on `refs/remotes/origin/<base>`; the adapter re-checks the proven sha with `merge-base --is-ancestor` against `refs/remotes/origin/main` and refuses otherwise; `test_push_refuses_the_opt_out_for_a_sha_not_on_origin_main`.
- `[low]` `[patch]` **L-C — what was pushed was not tied to the proof.** The push re-read `refs/heads/loop/<slug>`, so a commit made between the fast-forward and the push would leave with the older sha's journal line. **Fix:** `push` takes `proven_on_main_sha` (not a free-text reason), pushes exactly `<sha>:refs/heads/<remote_branch>` and builds the reason itself; `test_push_sends_exactly_the_proven_commit_even_if_the_branch_moved`.
- `[low]` `[patch]` **L-D — `env` as argv[0] failed on hosts without it.** On win-64 every proven push would fail as "git executable not found". **Fix:** without `shutil.which("env")` the push goes through the preflight instead (safe, slower). A process port that takes an environment mapping remains the long-term shape; not needed for this story.
- Test gaps "pushed sha bound to the fast-forward" and "full refname" — closed by L-B's and L-C's tests; the refresh fake records the proof it was handed.
