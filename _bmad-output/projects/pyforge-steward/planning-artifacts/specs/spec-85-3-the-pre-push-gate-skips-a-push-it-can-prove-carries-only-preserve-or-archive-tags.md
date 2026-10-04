---
title: "85.3: The pre-push gate skips a push it can prove carries only preserve or archive tags"
type: 'feature'
created: '2026-10-04'
status: 'done'
baseline_revision: '7722e81e77cf7813d425b2f901633458f6414809'
flag-exempt: detector-or-gate   # the pre-push preflight is a gate; a gated gate reports a silent green
review_loop_iteration: 0
followup_review_recommended: false
review_loop_iteration: 0
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - scripts/pre_push_preflight.sh
  - tests/scripts/test_lint_types_gate.py
  - .pre-commit-config.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The pre-push hook runs the full `pr-preflight` on every push. It skips only branch deletes and `dispatch/*` branches (`scripts/pre_push_preflight.sh:46-58`), and it refuses on a red tree (`:79-81`). A preserve is usually taken from a failing attempt's worktree, so `git push origin refs/tags/preserve/…` would run the preflight against that red tree and be refused exactly when it matters (review M1). The ruling chose a hook-side skip (review Q13). CAP-156's review found that under pre-commit the hook sees only the **first** ref of a multi-ref push, so a skip keyed on the first ref alone would let a branch ride along unchecked.

**Approach:** The hook gains one journaled skip, for a push it can **prove** is tag-only under `refs/tags/preserve/` or `refs/tags/archive/`:
- **Bare-git form.** When the hook reads every ref from stdin, the skip fires only if every line names such a tag with a non-zero sha.
- **Pre-commit form.** When only the first ref arrives, the skip fires only with a proof the pushing tool supplies. `pyforge.core.preserve_refs` pushes one refspec per tag and supplies that proof (marshal Story 87.15). The proof is never inferred from the first ref alone.
- **Journal.** Each skip writes a `.steward/preflight-skips.log` line naming the refs and shas, like the other skips (CAP-156).
- **Everything else.** A mixed push, and any push without the proof, runs the preflight as today.

Ledger key: `85-3-the-pre-push-gate-skips-a-push-it-can-prove-carries-only-preserve-or-archive-tags`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-165 (FR-38) and CAP-156 as amended 2026-10-04; CAP-154 (the gate). Flag-exempt `detector-or-gate`.

## Acceptance Criteria

- Given a bare-git push whose every stdin line names a `refs/tags/preserve/…` or `refs/tags/archive/…` remote ref with a non-zero local sha When the hook runs Then it exits 0 without running the preflight and journals the refs and shas.
- Given the same push with one `refs/heads/…` line added When the hook runs Then it runs the preflight; a red preflight refuses the push.
- Given the pre-commit form with a first ref under `refs/tags/preserve/` and no proof from the pushing tool When the hook runs Then it runs the preflight; with the proof present Then it skips and journals it.
- Given a tag push under any other prefix When the hook runs Then nothing changes from today.
- Given each rule removed When the tests run Then a test fails (mutation); the existing branch-delete, `dispatch/*` and opt-out cases are unchanged.

## Boundaries & Constraints

**Always:** Journal every skip with what was pushed. Fail toward running the preflight.

**Never:** Never skip on the first ref alone. Never skip a push that carries a branch. Never add a silent skip.

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-165 (FR-38); CAP-156 (amended 2026-10-04), CAP-154.
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-04 (later) entry.
Research: review M1 and Q13.
Ledger key: `85-3-the-pre-push-gate-skips-a-push-it-can-prove-carries-only-preserve-or-archive-tags`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_lint_types_gate.py -q` — expected: pass (the hook's tests, in both forms).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).

## Spec Change Log

- 2026-10-04: Implemented CAP-165 tag-only skip in `scripts/pre_push_preflight.sh` with `PYFORGE_PREFLIGHT_PRESERVE_TAGS_PROOF=1` for the pre-commit form; tests in `tests/scripts/test_lint_types_gate.py`.

## Review Triage Log

### 2026-10-04 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 0, false 1, maybe-false 0
- findings:
  - `[false]` `[reject]` Heredoc in `_stdin_is_tag_only_preserve_archive` might mishandle trailing content — verified: tab-separated git stdin lines parse correctly in throwaway-repo tests covering one and two tags.

## Auto Run Result

Status: done

**Summary:** The pre-push hook now skips `pr-preflight` for pushes proved tag-only under `refs/tags/preserve/` or `refs/tags/archive/`, with a journaled line naming refs and shas. Bare-git form inspects every stdin line; pre-commit form requires `PYFORGE_PREFLIGHT_PRESERVE_TAGS_PROOF=1` from the pushing tool (contract for `pyforge.core.preserve_refs`, Story 87.15).

**Files changed:**
- `scripts/pre_push_preflight.sh` — preserve/archive tag-only skip, proof env var, nested-tag ref matching via grep
- `tests/scripts/test_lint_types_gate.py` — AC coverage and hook script pins
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` — surface reconcile (CAP-156 / CAP-165)

**Review:** One blind-hunter-style note rejected as false after test verification. No patches or deferrals.

**Follow-up review recommended:** false

**Verification:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0 (2028 passed, 2 skipped)
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_lint_types_gate.py -q` — 27 passed
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — 1176 passed, 11 skipped
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile

**Residual risks:** Story 87.15 must set `PYFORGE_PREFLIGHT_PRESERVE_TAGS_PROOF=1` when pushing preserve tags through pre-commit; until then, pre-commit-form tag pushes still run the preflight (by design).
