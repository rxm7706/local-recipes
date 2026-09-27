---
title: '68.2: The pre-push gate skips a push that carries nothing new, and its journal names what was pushed'
type: 'fix'
created: '2026-09-27'
status: 'done'
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every `.steward/preflight-skips.log` line `scripts/pre_push_preflight.sh` (CAP-154) writes records the checked-out branch and its HEAD — `main`, eight times, for the 2026-09-27 loop-home refresh — not the refs pushed, so the journal cannot say what left the machine unchecked; and the delete skip is not journaled at all. The refresh itself paid ~80 minutes of preflight for eight fast-forwards to `origin/main`.

**Approach (after review 1):** one `journal_skip` helper writes every skip line — branch delete, `dispatch/*`, the manual `PYFORGE_PREFLIGHT_SKIP=1` — with the pushed remote ref(s) and local sha(s), falling back to the checked-out branch and HEAD only when the hook received no ref information. The hook adds **no** skip of its own: the "nothing new" skip this story first shipped was refused in review, because under pre-commit the hook receives only the first ref of a multi-ref push and cannot prove what the others carry. The refresh's cost is fixed where the proof lives — `marshal refresh` sets the journaled opt-out for its own proven fast-forward push (marshal Story 57.1, pyforge-marshal:CAP-267). This story's title is the ledger key of record and is kept.

Ledger key: `68-2-the-pre-push-gate-skips-a-push-that-carries-nothing-new-and-its-journal-names-what-was-pushed`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-156 (extends CAP-154); the refresh skip is `spec-pyforge-marshal` pyforge-marshal:CAP-267.

## Acceptance Criteria

- Given a push of `loop/<slug>` whose tip is `origin/main`, in both the pre-commit (env) and bare-git (stdin) forms When the hook runs Then it still runs the preflight
- Given `PYFORGE_PREFLIGHT_SKIP=1` on a push of `refs/heads/feature` from a checkout on `main` When the hook runs Then the journal line names `refs/heads/feature` and its sha, not `main`
- Given a `dispatch/*` push and a branch delete When the hook runs Then each skips and its journal line names the pushed ref
- Given a push whose preflight is red, without the opt-out When the hook runs Then the push is refused, as CAP-154 requires

## Boundaries & Constraints

**Always:** every skip is journaled with what was pushed; CAP-154's refusal of a red push has no new exception.

**Never:**
- Do not add a skip the hook cannot prove — under pre-commit it sees one ref.
- Do not add a second opt-out variable.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ff to main, no opt-out | `loop/x` at `origin/main` | preflight runs | red preflight refuses |
| manual opt-out | `PYFORGE_PREFLIGHT_SKIP=1` from a `main` checkout | skip; line names pushed ref + sha | — |
| dispatch branch | `refs/heads/dispatch/...` | skip; line names the ref | — |
| delete | all-zero local sha | skip; line names the ref | — |

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

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, commit `cda3257cff` — FAIL (1 high here, 2 medium on 68.1)

Verified clean: no `set -euo pipefail` path exits 0 by accident; tab/newline injection through ref names is impossible (`check-ref-format`); a stale-behind `origin/main` was conservative.

- `[high]` `[intent_gap → operator decision]` **H1 — the hook-side "nothing new" skip let unchecked commits leave under pre-commit.** pre-commit 4.6.2's `_pre_push_ns` returns on the first stdin line that updates an existing remote branch, so the hook sees only that ref's sha. Probe: `git push origin loop/x zfeature` (checked out on zfeature with a new commit) exited 1 before this commit, 0 after — the new commit reached the remote unchecked; `--all` leaked the same way; the stdin-only test gave false assurance. The reviewer's sound alternative (skip only when no local branch/tag/HEAD holds a commit outside `origin/main` or the remote) was measured never to hold here: local tags alone carry ~111k such commits. **Operator decision (2026-09-27):** remove the hook-side skip; `marshal refresh` sets the journaled opt-out for its own proven fast-forward push (marshal Story 57.1). Tests now pin that a push already on `origin/main` still runs the preflight in both forms.
- `[low]` `[moot]` **L1 — `origin/main` resolved by DWIM; L2 — the loop skipped when it examined no sha; tag-to-tree skip.** All three lived in the removed skip.
- `[low]` `[patch]` **L4 — the delete skip was not journaled although the header said so.** **Fix:** the delete path journals through `journal_skip`; the header lists only the skips that exist.
- `[low]` `[note]` In the pre-commit root-commit case (`PRE_COMMIT_TO_REF` unset) a manual-skip line pairs the pushed ref with HEAD's sha — the documented fallback.
- Test gaps "dispatch journal line", "multi-ref only in stdin form" — closed: the automatic-skip test covers dispatch and delete journaling; the multi-ref hazard no longer exists.

### Review 2 — 2026-09-27, independent adversarial reviewer, commit `db044dad6a` — PASS with lows (none here)

Verified closed under real pre-commit 4.6.2 with the real script: H1 (no ref-based skip remains; a push already on `origin/main` with a failing preflight is refused and not journaled), L4 (the delete skip journals through `journal_skip`). The skip journal names the pushed ref and sha for the manual, `dispatch/*` and delete lines.

- `[nit]` `[patch]` `_hook_repo(with_origin_main=…)` in `tests/scripts/test_lint_types_gate.py` was always true after H1; the dead branch and parameter are removed.
