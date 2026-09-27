---
title: '68.2: The pre-push gate skips a push that carries nothing new, and its journal names what was pushed'
type: 'fix'
created: '2026-09-27'
status: 'in-review'
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

**Problem:** `scripts/pre_push_preflight.sh` (CAP-154) runs the full ~10-minute `pr-preflight` for every push except branch deletes and `dispatch/*`. `marshal refresh` fast-forwards eight `loop/<slug>` homes to `origin/main` and pushes each — every pushed commit is already on `main` and passed CI there — so a loop-home resync cost ~80 minutes of preflight, or the manual `PYFORGE_PREFLIGHT_SKIP=1` (2026-09-27). And every `.steward/preflight-skips.log` line records the checked-out branch and its HEAD (`main`, eight times), not the refs pushed, so the journal cannot say what left the machine unchecked.

**Approach:** after the existing delete and `dispatch/*` skips, a nothing-new skip: when `origin/main` resolves and, for every non-delete pushed sha, `git rev-list <sha> --not origin/main` is empty, the hook journals "already on origin/main: nothing new to preflight" and exits 0. Any new commit, an unresolvable `origin/main`, or a sha `rev-list` cannot read runs the full preflight. One `journal_skip` helper writes every skip line with the pushed remote ref(s) and local sha(s), falling back to the checked-out branch and HEAD only when no ref information arrived.

Ledger key: `68-2-the-pre-push-gate-skips-a-push-that-carries-nothing-new-and-its-journal-names-what-was-pushed`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-156 (extends CAP-154).

## Acceptance Criteria

- Given a push of `loop/<slug>` whose tip is `origin/main` (both the `PRE_COMMIT_*` env form and the stdin form) When the hook runs Then it exits 0 without running the preflight and journals a line naming `refs/heads/loop/<slug>` and the sha
- Given a push carrying one new commit, or a multi-ref push where one ref is new When the hook runs Then it runs the preflight
- Given no `origin/main` in the repository When the hook runs Then it runs the preflight
- Given `PYFORGE_PREFLIGHT_SKIP=1` on a push of `refs/heads/feature` from a checkout on `main` When the hook runs Then the journal line names `refs/heads/feature` and its sha, not `main`
- Given the existing delete and `dispatch/*` cases When the hook runs Then they behave as before

## Boundaries & Constraints

**Always:** the automatic skip covers only commits reachable from `origin/main`; anything the hook cannot determine runs the preflight; every skip is journaled.

**Never:**
- Do not widen the skip to "already on some remote branch" — only `main` has passed CI.
- Do not add a second opt-out variable.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ff to main | `loop/x` at `origin/main` | skip, journal `refs/heads/loop/x` | none |
| new commit | one commit beyond `origin/main` | preflight runs | red preflight refuses the push |
| multi-ref, one new | `loop/x` at main + `main` ahead | preflight runs | — |
| no origin/main | remote-tracking ref absent | preflight runs | never skip on a guess |
| manual opt-out | `PYFORGE_PREFLIGHT_SKIP=1` | skip, journal names pushed ref + sha | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-156.
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 (later) — Proposed: housekeeping that leaks, and a gate that re-checks what `main` already checked*.
Ledger key: `68-2-the-pre-push-gate-skips-a-push-that-carries-nothing-new-and-its-journal-names-what-was-pushed`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_lint_types_gate.py -q` — expected: pass.
