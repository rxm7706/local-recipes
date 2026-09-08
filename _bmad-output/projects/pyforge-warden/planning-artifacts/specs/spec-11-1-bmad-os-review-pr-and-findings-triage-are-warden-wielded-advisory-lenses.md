---
title: 'Story 11.1: bmad-os-review-pr and findings-triage are warden-wielded advisory lenses'
type: 'feature'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: '32d0971b961c32ab2453fc00a6cb87f6ec711b40'
---

<intent-contract>

## Intent

**Problem:** Warden must wield the two utility-skills steward Story 46.2 provisioned
(`bmad-os-review-pr` for PR-review depth, `bmad-os-findings-triage` for finding
consolidation) as advisory lenses beside its compliance gate, with a durable,
executable proof that neither lens can ever influence the composed verdict or
exit code.

**Approach:** Finish the persona-level routing steward 46.2 started (a generic
pointer line already landed in `bmad-agent-warden/SKILL.md`) by mapping each
skill to its specific role, and add a warden-owned hook-book test that uses the
existing `pyforge.core.hooks` `PluginRegistry` machinery to structurally prove
an advisory-lens plugin's notes never reach `plugin_findings`/`rungs`/
`compose()`, and can never publish the PR-gate verdict.

## Boundaries & Constraints

**Always:** No new hook-book plugin class ships in production code
(`hooks.py`/`scanner_plugins.py` stay unchanged) -- the two lenses are
documentation-level routing at the persona layer, proven safe by a test built
on the existing `PluginRegistry`/`compose()` infrastructure. Advisory content
stays out of the five frozen `Finding`-id families (no schema bump). Routing
stays documented in exactly one durable home: `bmad-agent-warden/SKILL.md`
(suite:AD-2); `adoption-register.md` § 2 and the `AGENTS.md` pointer line already
name warden sole wielder -- verify, do not restate elsewhere.

**Never:** Do not add per-skill routing lines to `CLAUDE.md` or `AGENTS.md` --
both already carry (or intentionally omit) exactly the right level of detail.
Do not add a new PR-gate hook spec, a new `Finding` family, or a new
`scanner_plugins.py` plugin class. Do not implement the vendored
`bmad-os-review-pr`/`bmad-os-findings-triage` skill content itself -- steward
46.2 already installed it; this story only proves the boundary and finishes
the routing text.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Advisory lens registered, contributes a note only | `PluginRegistry` with a test-local stub plugin owned `bmad-os-review-pr`, attached to `PR_GATE_SCAN`, writing into `context["advisory_notes"]` (never `context["plugin_findings"]`) | `findings_from_plugin_context(context)` returns `()`; `compose()` over the same real rungs is identical with vs without the plugin registered/invoked | No error expected |
| Advisory lens attempts to publish the PR-gate verdict | A plugin owned `bmad-os-findings-triage` calls `publish_verdict(PR_GATE_VERDICT, plugin, "stolen")` | Raises `SecondVerdictError` | Exception propagates uncaught to the caller |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py` -- existing hook book (`PR_GATE_SCAN`/`AGGREGATE`/`VERDICT` specs, `invoke_pr_gate`, `publish_pr_gate_verdict`, `WardenVerdictOwner`) -- read-only, no changes.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py` -- existing plugin shapes (`OptionalScanPlugin`, `findings_from_plugin_context`, `merge_plugin_findings`, `coerce_plugin_finding`) -- read-only; the new test mirrors this shape, no changes here.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py` -- `compose()` (rungs -> winning `(Status, StatusDriver)`) -- read-only.
- `src/shared/packages/pyforge-warden/tests/unit/test_hooks.py` -- existing hook-book test precedent (`_ScanPlugin`, `PluginRegistry`, `invoke_pr_gate`) -- style/pattern reference.
- `src/shared/packages/pyforge-warden/tests/unit/test_default_warden_without_checkmarx.py` -- Story 9.3's "no-competing-verdict" / green-without-a-named-plugin test -- precedent for how this story's invariant test should read.
- `src/shared/packages/pyforge-warden/tests/unit/test_advisory_lenses.py` (NEW) -- the Story 11.1 hook-book test the Surface line requires.
- `.claude/skills/bmad-agent-warden/SKILL.md` -- "Utility skill routing (suite:AD-2)" section (steward 46.2 landed a generic one-line pointer here); refine to map each lens to its specific role.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` § 2 -- already names warden sole wielder for both skills (verify only).
- `AGENTS.md` (~line 41) -- already carries the one pointer line to the register (verify only).
- `CLAUDE.md` -- verify untouched.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` -- flip `11-1-bmad-os-review-pr-and-findings-triage-are-warden-wielded-advisory-lenses` from `blocked` to `done` once implementation lands (steward 46.2, the blocking dependency, is confirmed landed on this branch).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-warden/tests/unit/test_advisory_lenses.py` -- add a hook-book test proving the two advisory-lens plugins can contribute an advisory note without ever reaching `plugin_findings`/`compose()`, and cannot publish the PR-gate verdict -- satisfies the story's "one hook-book test asserting the lens cannot alter the composed status" surface requirement.
- `.claude/skills/bmad-agent-warden/SKILL.md` -- refine the "Utility skill routing (suite:AD-2)" line to explicitly map `bmad-os-review-pr` to PR-review depth and `bmad-os-findings-triage` to finding consolidation -- matches the story's Given/When/Then wording precisely.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` -- flip the story's row from `blocked` to `done`.

**Acceptance Criteria:**
- Given the two skills installed (`bmad-os-review-pr`, `bmad-os-findings-triage` present under `.claude/skills/`), when the warden persona routes PR-review depth to `bmad-os-review-pr` and finding consolidation to `bmad-os-findings-triage`, then their outputs surface as non-`Finding` advisory notes with no schema bump to the frozen five families.
- Given a `PluginRegistry` with an advisory-lens stub plugin registered on `PR_GATE_SCAN`, when `tests/unit/test_advisory_lenses.py` runs, then it proves `compose()` produces identical output with and without the plugin registered -- `compose()` never observes advisory content.
- Given a plugin claiming an advisory-lens owner name, when it attempts to publish on `PR_GATE_VERDICT`, then `SecondVerdictError` is raised.
- Given `adoption-register.md` § 2 and `bmad-agent-warden/SKILL.md`, when inspected, then warden is named sole wielder of both skills and `CLAUDE.md` carries no per-skill routing line.
- Given the full warden test suite, when `pixi run -e pyforge-warden pyforge-warden-test` runs, then it stays green.

## Spec Change Log

## Review Triage Log

### 2026-09-07 -- Review pass
- verdicts: 12 findings -- high 0, medium 1, low 5, false 6, maybe-false 0
- findings:
  - `[medium]` `[patch]` Tier-3 `sprint-status.yaml` feed still read `blocked` for 11-1 while the tracked ledger twin was hand-flipped to `done`, which would make `sprint-ledger-sync`'s per-key monotonic guard refuse promotion for the whole pyforge-warden project -- flipped the Tier-3 feed's `11-1-...` row to `done` to match.
  - `[false]` `[reject]` "new verdict-theft test duplicates existing `SecondVerdictError` coverage" -- refuted: `_AdvisoryLensVerdictClaim.owner = "bmad-os-findings-triage"` is specific to this story's named lens, unlike the pre-existing generic `checkmarx`-owned tests; it binds the general guarantee to the two named advisory lenses the Surface line requires.
  - `[low]` `[patch]` `_rungs_fed_from`'s docstring claimed production feeds `compose()` "one rung per plugin-contributed Finding," but `cli.py` never converts a plugin finding into a rung at all (`rungs` is built by `DefaultPolicy.evaluate()` before the plugin-findings merge, and that merge never touches `rungs`) -- reworded the comment to state the correct (stronger) invariant.
  - `[low]` `[patch]` `_BASE_RUNGS` used `StatusDriver(axis="security", ...)`, not one of the real axis constants (`AXIS_HYGIENE`/`AXIS_VULNERABILITY`/`AXIS_INGESTION`/`AXIS_LICENSE`/`AXIS_CURRENCY`) -- replaced with `AXIS_VULNERABILITY` from `pyforge.warden.models`.
  - `[low]` `[patch]` `_AdvisoryLensPlugin.is_default: bool = False` was vestigial (only `select_scanner_plugins`/`scanner_plugin_registry()` read `is_default`, neither of which the tests call) -- removed.
  - `[low]` `[reject]` "no test registers both lenses concurrently" -- a coverage-completeness suggestion, not a demonstrated defect; `PluginRegistry` uniqueness keys on `(type, hook_spec, owner)` and the two stand-ins differ only by `owner`, so no collision was shown; the fix is a net-new test (an addition), and neither skill is a real registered plugin in production.
  - `[low]` `[reject]` "SKILL.md's routing prose uses hook-book internals vocabulary (`plugin_findings`, `rungs`, `compose()`) the same file's Forbidden-actions section tells the persona not to touch" -- refuted: the Forbidden section itself already uses this exact vocabulary purely to state boundaries ("Do not call `compose` or `exit_code_for`"), never as an instruction to invoke them; the new routing prose does the same, consistent with the file's existing style.
  - `[false]` `[reject]` "diff never touches `adoption-register.md` despite Surface naming it in-scope" -- refuted: per suite:AD-2, routing detail lives solely in the persona skill and is never restated in the register (confirmed by `AGENTS.md`'s own pointer text); the register already carries the correct row from the planning-authoring commit, so leaving it untouched is the correct, suite:AD-2-compliant behavior, not an omission.
  - `[false]` `[reject]` "before/after hook points are unexercised in `_AdvisoryLensPlugin.call()`" -- refuted: this mirrors `EngineScanPlugin`/`OptionalScanPlugin`'s identical pre-existing pattern (only `"around"` is handled); the edge-case-hunter layer independently traced this exact point and confirmed it is handled, not a gap.
  - `[false]` `[reject]` "neither `bmad-os-review-pr` nor `bmad-os-findings-triage` exists anywhere in the repository" -- refuted: both directories exist under `.claude/skills/`, committed at the current revision (steward's Story 46.2 commit), confirmed via a direct filesystem check plus a clean version-control status for those paths.
  - `[false]` `[reject]` "steward's ledger shows `46-2-...: backlog`, so the cross-station dependency is not landed" -- refuted: `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` line 170 reads `done` at the current revision with a clean working tree, verified independently and corroborated by the verification-gap layer's own check of the same line.
  - `[false]` `[reject]` "the adoption register's authority precedes the code that's supposed to make it true, so register and implementation are not shown to be in lockstep" -- refuted: this is the designed Dream-to-code order (planning declares intent, implementation fulfills it), not a defect; same substance as the adoption-register finding above, settled the same way by suite:AD-2.

## Design Notes

No new hook-book plugin ships in production code. `bmad-os-review-pr` and
`bmad-os-findings-triage` operate at the persona/skill layer -- consulted by
an agent embodying the `bmad-agent-warden` persona during PR review -- never
as `PluginRegistry` members. The new test builds a test-local stand-in plugin
(mirroring `scanner_plugins.OptionalScanPlugin`'s shape) purely to give the
"cannot alter composed status" claim a concrete, executable proof against the
same infrastructure any future code-level integration would have to use --
this is the structural boundary test the story's Surface line calls for, not
an integration of the skills' own content.

## Verification

**Commands:**
- `pixi run -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including the new `test_advisory_lenses.py`.


## Auto Run Result

**Summary:** Warden now names each of its two steward-46.2-provisioned advisory
lenses to its specific role (`bmad-os-review-pr` -> PR-review depth,
`bmad-os-findings-triage` -> finding consolidation) in the one durable routing
home (`bmad-agent-warden/SKILL.md`, suite:AD-2), and a new hook-book test proves --
against the real `pyforge.core.hooks` `PluginRegistry` / `compose()`
infrastructure -- that an advisory-lens plugin's notes never reach
`plugin_findings`, never influence `compose()`'s composed status, and can
never publish the PR-gate verdict. No new hook-book plugin class ships;
`hooks.py`/`scanner_plugins.py`/`verdict.py`/`CLAUDE.md`/`AGENTS.md` are
unchanged, and `adoption-register.md` already named warden sole wielder from
the planning-authoring pass.

**Files changed:**
- `.claude/skills/bmad-agent-warden/SKILL.md` -- refined the "Utility skill routing (suite:AD-2)" section to map each of the two lenses to its specific role and state the non-`Finding`/never-`compose()`/never-verdict boundary explicitly.
- `src/shared/packages/pyforge-warden/tests/unit/test_advisory_lenses.py` (new) -- three hook-book tests: an advisory note never becomes a `Finding`; `compose()` is identical with and without the lens registered; an advisory-lens-owned plugin cannot publish `PR_GATE_VERDICT`.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` -- flipped `11-1-...` from `blocked` to `done`.
- `_bmad-output/projects/pyforge-warden/implementation-artifacts/sprint-status.yaml` (Tier-3, gitignored) -- flipped the same row to `done` so the tracked twin and its source feed agree (review-pass patch).

**Review findings breakdown** (full evidence in `## Review Triage Log` above):
- Patched (4): Tier-3/tracked-ledger drift (medium); a misleading "one rung per Finding" comment (low); an invented `"security"` axis in the test's stand-in rung (low); a vestigial unused `is_default` attribute (low).
- Rejected as false (6): "the two skills don't exist anywhere in the repo" (they do, committed in steward 46.2); "steward's 46.2 ledger row is still `backlog`" (it reads `done`); "the new verdict-theft test is pure duplication" (it names the story's specific lens as owner, unlike the generic pre-existing coverage); "the diff should have touched `adoption-register.md`" (suite:AD-2 forbids restating routing there); "the register precedes the code" (the designed spec-then-code order, not a defect); "before/after hook points are unexercised" (identical to the pre-existing `EngineScanPlugin` pattern, confirmed handled by the edge-case-hunter layer).
- Rejected as low (2, not worth the added complexity): no test registers both lenses concurrently; SKILL.md's boundary language uses hook-book vocabulary (consistent with the file's pre-existing Forbidden-actions style).

**Follow-up review recommendation:** `false`. This pass patched one `medium` and three `low` entries -- one `medium` alone does not cross the two-or-more-`medium` threshold, and no `high` was patched, so the work has converged.

**Verification performed:**
- `pixi run -e pyforge-warden pyforge-warden-test` -- 2078 passed, 11 deselected (run both before and after the patch round).
- `pixi run -e pyforge-warden python -m pytest src/shared/packages/pyforge-warden/tests/unit/test_advisory_lenses.py -v` -- all 3 tests pass in isolation.
- Matrix test audit: both I/O & Edge-Case Matrix rows are covered by passing tests in `test_advisory_lenses.py`.
- Confirmed via direct filesystem/version-control checks: `hooks.py`, `scanner_plugins.py`, `verdict.py`, `CLAUDE.md`, `AGENTS.md` carry zero diff; both utility skills exist under `.claude/skills/`; `adoption-register.md` already names warden sole wielder; steward's own ledger reads `46-2-...: done`.

**Residual risks:** None identified. The two vendored `bmad-os-review-pr`/`bmad-os-findings-triage` skills' own upstream content was out of scope for this story (steward 46.2 already logged nine content-level findings against them separately).
