---
title: "79.2: Dispatch verification runs `lint-types`, and the \"stopgap\" surfaces stop calling themselves one"
type: 'fix'
created: '2026-10-01'
status: 'done'
baseline_revision: '6701b2b15a70fa9df0f8ea0287e2edc4fbeca66a'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `dispatch/*` branches skip `pr-preflight` because the dispatch supervisor gates them, but the supervisor's verification
runs only the station's `verify_commands` plus the derived surface-reconcile guard (Story 53.1). `lint-types` is in
neither and is outside the `detectors-ci` merge gate, so scribe Story 25.1 landed `except (OSError,
subprocess.TimeoutExpired):`, which `ruff format` (py314, PEP 758) rewrites, and `lint-types` stayed red on `main` from
`a1dbda7915` until #1690 (DW-OPS-2026-10-01-2). Separately, marshal's `"22"` and `"28"` `epic_surfaces` entries still
say they are a stopgap until Story 28.15 ships; 28.15 is `done` (DW-FU-28-14-4, DW-OPS-2026-10-01-3).

**Approach:**

- **lint-types:** derive `pixi run --frozen -e pyforge-guild lint-types` in one place beside
  `_verify_commands_with_surface_guard`, so every station's dispatch verification runs it exactly once whatever its own
  `verify_commands` say; never by editing eight `verify_commands` lists. A red result refuses the landing with a finding
  that names `lint-types`. `gate.check_spec_binding` is one-directional (an extra policy command is never a finding), so
  no tracked spec's binding changes.
- **The "22"/"28" entries stay.** Their station-wide globs are the convention every later marshal epic declares, and Epic
  73's follow-up reviews of done 22.x/28.x stories dispatch against them. Only their comments change: they say the
  station-wide surface is the convention, not a stopgap. Their globs do not change.

Ledger key: `79-2-dispatch-verification-runs-lint-types-and-the-stopgap-surfaces-stop-calling-themselves-one`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-261 (a) (Story 53.1, the derived verification guard); `spec-marshal-token-economy` CAP-17 (Story 28.15, the
  scope-violation mode that ended the stopgap).
- A defect of the supervisor's verification gate, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given any station's dispatch When verification runs Then `pixi run --frozen -e pyforge-guild lint-types` runs exactly once, after the station's own `verify_commands`
- Given a change that fails `lint-types` When the dispatch verifies Then the landing is refused with a finding naming `lint-types`
- Given a station whose `verify_commands` already names `lint-types` When verification runs Then it still runs once
- Given every tracked story spec When `gate.check_spec_binding` runs against the widened commands Then no new finding appears
- Given marshal-policy.toml When it is read Then the `"22"` and `"28"` globs are unchanged and their comments no longer call them a stopgap
- Given the derived `lint-types` is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `dispatch_verify.py` (`_verify_commands_with_surface_guard` and its callers) and `core/gate.py::check_spec_binding`.
2. Derive the `lint-types` command beside the surface guard; dedupe against a station's own list.
3. Name the lane in the refusal finding.
4. Rewrite the `"22"`/`"28"` comments in marshal-policy.toml; leave the globs.
5. Tests: with and without the command in a station's list, a failing lint run refusing, the binding unchanged; run the mutation by hand.

## Boundaries & Constraints

**Always:**
- `lint-types` is added in one derived place for every station.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit any station's `verify_commands` list.
- Do not change the `"22"`/`"28"` globs or remove those entries.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| clean change | lint-types green | verification passes | — |
| lint-red change | lint-types red | landing refused, `lint-types` named | — |
| already listed | station lists lint-types | runs once | — |
| binding | every tracked spec | no new MRS-GATE-011 | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` -- `_verify_commands_with_surface_guard` (the one derived-commands site: three callers, `run_verify_commands_only`, `evaluate_dispatch_verification`, `cli/drain_plan.py::verify_commands`); the guard constant is imported from `adapters/harness_bmadloop.py::_SURFACE_RECONCILE_COMMAND`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` -- `classify_outcome` already emits `MRS-GATE-001` with `verify command '<command>' exited N`, so a red lane names `lint-types` with no new finding code; `check_spec_binding` is one-directional (read-only evidence).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py`, `tests/unit/test_dispatch_verify_merge_tree.py` -- assert the exact derived command lists; both widen by one entry.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` -- the `"22"` (line ~107) and `"28"` (line ~129) comments; the `"79"` surface already lists this file.
- `pixi.toml` `[feature.guild-tasks.tasks.lint-types]` -- the task the derived command runs (read-only).

## Binding

Parent capabilities: CAP-261 (a); `spec-marshal-token-economy` CAP-17 (defects; no new CAP). DW-OPS-2026-10-01-2, DW-OPS-2026-10-01-3, DW-FU-28-14-4.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `79-2-dispatch-verification-runs-lint-types-and-the-stopgap-surfaces-stop-calling-themselves-one`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).

### 2026-10-01 — Review pass
- verdicts: 22 findings — high 4, medium 2, low 16, false 0, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: `default_epic_surface` docstring in `core/gate.py` and the `[epic_surfaces]` header in marshal-policy.toml still called the "28" entry a stopgap / "not a wildcard" — verified real, a direct comment correction; both rewritten (comments only, globs unchanged).
  - `[low]` `[reject]` Blind: the new "28" comment's rationale ("convention every later epic declares", "Epic 73's follow-up reviews", "28.15 (done)") — the wording is the spec's own Approach, entries 54/66/78 do restate the surface, and `done` is terminal; no named harm.
  - `[low]` `[patch]` Blind: comments beside the changed code now wrong (`evaluate_dispatch_verification` "guard alone", `run_verify_commands_only` "the guard is always present", `drain_plan.verify_commands` docstring) — verified; comments updated to name both derived commands. The proposed helper rename is rejected: three callers plus two cross-references for no behaviour.
  - `[low]` `[reject]` Blind: the dispatched session's prompt (`_SPEC_SURFACE_OBLIGATION`) does not mention `lint-types` — an enhancement, not a defect of this change; the refusal finding names the lane for the retry, and the fix adds prompt text plus pinned tests.
  - `[low]` `[reject]` Blind: loop sessions (`render_policy_toml`) do not get `lint-types` — the intent scopes the defect to `dispatch/*` branches, which skip `pr-preflight`; loop branches are not exempt from it (AGENTS.md § Running and verifying).
  - `[low]` `[reject]` Blind: `lint-types` is a whole-tree gate with no baseline, so a red `main` refuses every station's dispatch — this is the intent's own rule ("a red result refuses the landing"), not an accident; recorded as a residual risk below.
  - `[low]` `[reject]` Blind: no timeout on the heavier lane — `_run_verify_command` has never passed `timeout_s` for any command, a hang needs a wedged ruff/mypy, and a timeout is a new policy knob (more than a direct correction).
  - `[medium]` `[patch]` Blind: test gaps — the drain-plan caller is unpinned (verified by mutation: reverting `drain_plan.py:168` kept every test green); fixed with a new `test_drain_plan.py` test. Its other sub-items are rejected as low: the sweep is AC4's own wording (one-directional by construction), `parents[6]`/skip mirrors neighbouring tests, the `--frozen`-less spelling is not deduped (same whitespace-only rule as the guard; no station lists it), the literal is duplicated on purpose so the mutation bites.
  - `[low]` `[reject]` Blind: the spec records no AC6 mutation result and its Verification lacks the new tests — the fix is to edit this build's spec; the mutation was run by hand (see Auto Run Result).
  - `[low]` `[reject]` Blind: a station-listed `lint-types` is moved to the end; the Binding block still says ledger status `backlog` at mint — the docstring states the move, and the mint-time fact is the spec's own text.
  - `[high]` `[patch]` Edge: a real `lint-types` red is downgraded to MRS-GATE-014 WARN by `reclassify_pre_existing_gate_findings` — reproduced live: ruff-format, ruff-check and mypy print package-relative paths (`src/pyforge/scribe/catalog.py`, cwd = the package), which never match the story's repo-relative changed files, so the verdict was `verified`. Fixed in `evaluate_dispatch_verification`: the derived lane's report is not handed to the reclassifier, so its MRS-GATE-001 stands. Re-run: all three shapes refuse.
  - `[high]` `[patch]` Edge: `FakeProcessLintFails` emitted stderr that matches no failure-path regex, so the tests never reached the downgrade branch — same root cause as the row above; new parametrized tests use the three real output shapes and assert REFUSED with one MRS-GATE-001 naming `lint-types` and no MRS-GATE-014.
  - `[high]` `[patch]` Edge: AC2 does not hold on the real path (restates the first Edge finding as a claim) — same root cause; resolved by the same fix.
  - `[low]` `[reject]` Edge: a `lint-types` spelling without `--frozen` or with reordered flags is not deduped and runs twice — same whitespace-only rule as the guard; no station declares it; collapsing variants would change which string spec binding sees.
  - `[low]` `[patch]` Edge: stale comments in `dispatch_verify.py` ("runs the guard alone") — same root cause as the third Blind row; fixed.
  - `[low]` `[reject]` Edge: `render_policy_toml` still appends only the S-13.7 guard, so loop and dispatch gates diverge — same as the fifth Blind row; the intent names `dispatch/*`.
  - `[medium]` `[patch]` Gap: the drain-plan consumer of the derived command has no test — pre-verified by mutation; same fix as the Blind test-gap row (a new test that fails when `drain_plan.py:168` returns the raw list or the derivation drops `lint-types`).
  - `[high]` `[patch]` Intent, divergence 1: the refusal test never passes through the downgrade branch, so on real output a red outside the diff is WARN — same root cause as the first Edge row; fixed and covered with real output.
  - `[low]` `[patch]` Intent, divergence 2: the merge-tree preview refuses any red while `evaluate_dispatch_verification` downgraded one — resolved by the same fix; both paths now refuse a red `lint-types`.
  - `[low]` `[reject]` Intent, divergence 3: the real `pixi run` is never exercised and has no timeout — `pixi run --frozen -e pyforge-guild lint-types` exits 0 in this very worktree, and the timeout is the seventh Blind row.
  - `[low]` `[reject]` Intent, divergence 4: the session is not told about the lane — same as the fourth Blind row.
  - `[low]` `[reject]` Intent, divergence 5: AC5 has no test — satisfied by inspection (the diff changes comment lines only; the parsed TOML is identical), and a test that pins comment wording would be brittle.

## Auto Run Result

Status: done

**Summary.** Every dispatch verification (`evaluate_dispatch_verification`), merge-tree preview (`run_verify_commands_only`) and drain-plan binding (`cli/drain_plan.py`) now runs `pixi run --frozen -e pyforge-guild lint-types` exactly once, after the station's own `verify_commands` and the S-13.7 guard, derived in `_verify_commands_with_surface_guard` and de-duplicated against a station's own list. A red lane is an ordinary `MRS-GATE-001` naming `lint-types` and refuses the landing; the review pass found and fixed that the 28.22 reclassifier downgraded it to a WARN on real ruff/mypy output. The "22"/"28" `epic_surfaces` comments (and the header above them and the `default_epic_surface` docstring) no longer say stopgap; the globs are unchanged.

**Files changed.**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` — `_LINT_TYPES_COMMAND`; the derivation; the lane kept out of the pre-existing reclassifier; comments.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py` — docstring only.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` — `default_epic_surface` docstring only.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py`, `test_dispatch_verify_merge_tree.py`, `test_drain_plan.py` — widened expectations; once/dedupe/refusal/binding tests; real-output refusal tests; the drain-plan pin.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` — comments only.
- `.memlog.md` of `spec-pyforge-marshal`, `spec-pyforge-core` and `spec-risk-tiered-review-depth` — surface reconcile naming every governed path; no baseline stamped.

**Review findings.** 22 findings: 10 rows routed to patch over 4 root causes (the reclassifier downgrade, high; the unpinned drain-plan caller, medium; stale stopgap wording, low; stale comments beside the changed code, low), none deferred, 12 rejected as low with the reasons in the log above. `patch` entries at entry verdict: high 1, medium 1, low 2.

**Follow-up review recommendation: true.** A `high` entry was patched. The unverified risk: the exemption from the reclassifier is proven against fake `ProcessPort` output of the three real shapes, not against a real `pixi run ... lint-types` red inside a dispatch worktree.

**Verification** (exit codes read directly, none through a pipe):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — exit 0, 9272 passed, 1 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
- `python scripts/spec_surface_reconcile.py` — exit 0; `pixi run -e pyforge-guild spec-surface-check` — exit 0.
- AC6 by hand: with `_LINT_TYPES_COMMAND` removed from the derived tuple, 17 tests failed across `test_dispatch_verification.py`, `test_dispatch_verify_merge_tree.py` and `test_drain_plan.py`; the file was restored byte for byte.
- Live reproduction of the downgrade before the patch (ruff-format, ruff-check, mypy → `verified` with MRS-GATE-014) and after (all `refused`, MRS-GATE-001).

**Residual risks.**
- A red `main` now refuses every station's dispatch until it is fixed — the intent's own rule, and by design it is the point of "stop the inflow".
- Every verification and merge-tree preview now includes the whole `lint-types` lane (ruff, ruff format, mypy over ten packages); no timeout, as for every other verify command.
- Not run: `pr-preflight` (a `dispatch/*` branch is supervisor-gated) and the coverage floors.
- The `[epic_surfaces]` header still says the default for an undeclared epic is `()`, stale since Story 28.14 and outside this story's comment scope.
