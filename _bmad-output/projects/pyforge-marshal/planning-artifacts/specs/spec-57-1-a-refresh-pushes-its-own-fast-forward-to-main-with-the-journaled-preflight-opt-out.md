---
title: '57.1: A refresh pushes its own fast-forward to `main` with the journaled preflight opt-out'
type: 'fix'
created: '2026-09-27'
status: 'in-review'
review_loop_iteration: 0
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

**Approach:** `VcsPort.push` gains a keyword-only `preflight_skip_reason: str | None = None` (additive; every existing caller unchanged). `GitVcs.push` carries a given reason to that one `git push` process as `PYFORGE_PREFLIGHT_SKIP=1` and `PYFORGE_PREFLIGHT_SKIP_REASON=<reason>` through the POSIX `env` utility (the process port takes no environment; nothing is exported to anything else). `cli/refresh.py` passes a reason only when its own `fast_forward` step to `tip_ref` succeeded and `tip_ref == "origin/main"`: "marshal refresh: loop/<slug> fast-forwarded to origin/main (<sha12>); every pushed commit is already on origin/main". Any other `--base` passes none.

Ledger key: `57-1-a-refresh-pushes-its-own-fast-forward-to-main-with-the-journaled-preflight-opt-out`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-267 (FR-213); cross-station: `spec-pyforge-steward` CAP-154/156 (the hook and its journal).

## Acceptance Criteria

- Given a clean loop home behind `origin/main` and the default base When `marshal refresh` runs Then its push passes a reason naming `loop/<slug>`, `origin/main` and the new sha
- Given `--base` other than `main` When `marshal refresh` runs Then its push passes no reason
- Given a repo with a real `pre-push` hook When `GitVcs.push` runs with a reason Then the hook sees `PYFORGE_PREFLIGHT_SKIP=1` and the reason; without one, it sees neither variable
- Given every other push caller When it pushes Then its behaviour is unchanged

## Boundaries & Constraints

**Always:** the proof is `refresh`'s own successful fast-forward to `origin/main`, nothing else; the opt-out is the existing journaled one.

**Never:**
- Do not export the opt-out beyond the one `git push` process.
- Do not pass a reason for a home that was already current (no push happens) or whose fast-forward failed.
- Do not change the hook (steward's); do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| behind, base main | clean home, 2 behind | ff to origin/main; push with reason | push failure → existing WARN |
| behind, other base | `--base release` | ff to origin/release; push without reason | preflight runs in the hook |
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
