---
title: "A low-risk story's review runs lighter, never absent"
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-risk-tiered-review-depth/SPEC.md']
warnings: [oversized]
baseline_revision: '257094dcc2cf99a95c8553b6c05ae3cc09fe876f'
final_revision: 'd43e25ccfaf0fa5a4f4642f2817550966ae3946f'
---

<intent-contract>

## Intent

**Problem:** `core/policy.py`'s `DEFAULT_POLICY` sets `max_review_cycles: 3` as one flat,
repo-wide ceiling -- a one-line doc fix and a cross-module rewrite pay the identical review
price. There is no mechanism anywhere that varies review cost by how mechanical a story's
change actually is.

**Approach:** add two new pure functions to `core/gate.py`, mirroring `classify_doc_only_
declaration`'s established core-module idiom (Story 2.4): `classify_review_tier` classifies a
story into a closed `{"low", "standard"}` vocabulary from two already-gathered facts (its own
`declared_low_risk` declaration and its observed `changed_files` diff shape); `resolve_review_
cycles` maps a tier plus the already-composed repo-wide ceiling to the cycle allowance that
tier gets. Neither function does I/O, calls a model, or touches `gate_mode` -- the independent
reviewer's occurrence is untouched; only the cycle allowance varies.

## Boundaries & Constraints

**Always:**
- `classify_review_tier(*, declared_low_risk: bool, changed_files: tuple[str, ...]) ->
  dict[str, object]` lives in `core/gate.py`. No I/O, no VCS call, no spec-file read -- both
  inputs are facts a (future) caller already gathered, exactly like `classify_doc_only_
  declaration` takes an already-established `has_uncommitted_changes`.
- Tier is `"low"` only when BOTH `declared_low_risk` is `True` AND `len(changed_files) <=
  3` -- an AND-gate, not doc-only's OR. A bare declaration on a wide diff is not evidence of
  low risk; a small diff with no declaration is not auto-tiered down either. Every other
  combination is `"standard"`. `changed_files` is type-checked exactly like `check_scope`'s
  own identically-shaped parameter (`TypeError` on a non-tuple-of-str).
- `resolve_review_cycles(tier: str, *, default_max_review_cycles: int) -> int` lives in
  `core/gate.py`. For `tier == "low"`, returns `min(default_max_review_cycles, 1)` floored at
  `1`; for `tier == "standard"` (which also stands in for "unclassified" -- see Design Notes),
  returns `default_max_review_cycles` unchanged, floored at `1`. The floor applies
  UNCONDITIONALLY to both branches -- it exists solely so AC2's "never skipped" guarantee holds
  even against a pathological `default_max_review_cycles <= 0` (`core/policy.py::
  _valid_attempt_count` permits `0`), never to grant `"low"` a SMALLER value than intended. An
  out-of-vocabulary `tier` raises `ValueError` naming the value -- mirrors `describe_gate_mode`'s
  own precedent (Story 2.5) for a closed-vocabulary input, never a `Finding`.
- Neither function emits a `Finding` or registers a new `MRS-GATE-*` code -- this is a pure
  SCHEDULING decision, not a pass/fail check, the same "not every function here registers a
  code" precedent `describe_gate_mode` already sets.
- The review lever this story adjusts is cycle count ONLY, never a cheaper review model or lens
  set -- the governing Spec's own Non-goals name model-tiering as a separate, already-scoped
  sibling thread this story must not duplicate or decide.
- `max_followup_reviews` is NEVER read, referenced, or varied by tier anywhere in this change --
  satisfied by construction, not by picking a clever cap value.
- Extend `core/gate.py`'s module docstring with this story's own paragraph, following the
  established per-story convention.
- Unit-test the full truth table in `tests/unit/test_gate.py`, matching this file's existing
  synthetic-input/banner-comment style. Add a regression test to `tests/unit/test_deferred_work.py`
  reproducing the `review-budget-followup` Tier-3 block shape (the `DW-AD23-3` incident shape,
  per `_CLEAN_BLOCK`'s own fixture shape) for a story at EACH defined tier, proving
  `parse_followup_deferrals`/`deferrals_to_promote` capture it identically regardless of tier
  (AC4) -- a defense-in-depth proof for the by-construction guarantee above.
- Log a `deferred-work.md` entry naming the same three wiring gaps Story 2.4's own follow-up
  named for its sibling mechanism (declaration source, CLI/journal wiring, envelope folding),
  scoped to this story's own functions.

**Block If:** N/A -- no ambiguity requiring a human decision. The signal choice, tier vocabulary,
and review lever are this story's own design decisions per the governing Spec's Non-goals
("left to the downstream story's design"), resolved below rather than left open.

**Never:**
- Do not touch `cli/gate.py`, `core/policy.py`, `core/journal.py`, `core/findings.py`, or
  `core/verdict.py` -- matching Story 2.4's own established precedent for a `core/gate.py`-only
  mechanism story (the governing Spec's own `surface:` field names only `core/gate.py`). No CLI
  flag, no spec-frontmatter field for `declared_low_risk`, no `VcsPort` call for `changed_files`
  -- both stay caller-supplied facts, exactly like `declared_doc_only`/`has_uncommitted_changes`
  remain undelivered inputs after Story 2.4.
- Do not touch `pyforge-doctor`'s `deferred_work_check`/`chain.py` sources, or
  `_bmad-output/policy-defaults.toml`'s `max_followup_reviews` value.
- Do not add a third tier, a numeric risk score, or any signal beyond `declared_low_risk` +
  `changed_files`.
- Do not implement or assume a real "cheaper review pass" (alternate model, reduced lens set) --
  cycle count is the only lever this story ships.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Declared low-risk, small diff | `declared_low_risk=True`, `len(changed_files)=2` | `tier == "low"` | No error |
| Declared low-risk, wide diff | `declared_low_risk=True`, `len(changed_files)=10` | `tier == "standard"` -- declaration alone is not enough | No error |
| Undeclared, small diff | `declared_low_risk=False`, `len(changed_files)=1` | `tier == "standard"` -- an accidental small diff is not auto-tiered down | No error |
| Undeclared, wide diff | `declared_low_risk=False`, `len(changed_files)=10` | `tier == "standard"` | No error |
| `resolve_review_cycles("low", default_max_review_cycles=3)` | tier="low" | Returns `1` | No error |
| `resolve_review_cycles("standard", default_max_review_cycles=3)` | tier="standard" | Returns `3`, unchanged (AC3) | No error |
| `resolve_review_cycles` floor property | `default_max_review_cycles <= 0`, any tier | Always returns `>= 1` (AC2's unconditional floor) | No error, never 0 |
| `resolve_review_cycles` out-of-vocabulary tier | `tier="bogus"` | Raises `ValueError` naming the value | `ValueError`, never a `Finding` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` -- EDIT. Add
  `classify_review_tier`, `resolve_review_cycles`, and the `_LOW_RISK_MAX_CHANGED_FILES`/
  `_LOW_TIER_MAX_REVIEW_CYCLES` module constants. Extend the module docstring.
- `src/shared/packages/pyforge-marshal/tests/unit/test_gate.py` -- EDIT. Add the full I/O
  matrix as direct unit tests for both new functions, in a new `# --- Story 2.8 ...` banner
  section matching the file's existing convention.
- `src/shared/packages/pyforge-marshal/tests/unit/test_deferred_work.py` -- EDIT. Add the AC4
  regression test(s) reproducing the `review-budget-followup` shape at each defined tier.
- `_bmad-output/projects/pyforge-marshal/implementation-artifacts/deferred-work.md` -- EDIT.
  Log the wiring follow-up (declaration source, CLI/journal wiring, envelope folding).

## Tasks & Acceptance

**Execution:**
- [x] `core/gate.py` -- add `classify_review_tier(*, declared_low_risk: bool, changed_files:
  tuple[str, ...]) -> dict[str, object]`, pure, AND-gated tier classification.
- [x] `core/gate.py` -- add `resolve_review_cycles(tier: str, *, default_max_review_cycles:
  int) -> int`, pure, unconditional `>= 1` floor on both branches.
- [x] `core/gate.py` -- extend the module docstring with this story's own paragraph, following
  the established per-story convention (no new registered code, and why).
- [x] `tests/unit/test_gate.py` -- unit-test the full I/O matrix above (8 scenarios) in this
  file's existing synthetic-input style, in a new `# --- Story 2.8 ...` banner section.
- [x] `tests/unit/test_deferred_work.py` -- add the AC4 regression test(s): a `review-budget-
  followup` Tier-3 block reproducing the `DW-AD23-3` incident shape, captured via
  `parse_followup_deferrals`/`deferrals_to_promote` identically for a story at the `"low"` tier
  and a story at the `"standard"` tier.
- [x] `deferred-work.md` -- log the follow-up wiring gap (mirrors Story 2.4's own entry: no
  producer of `declared_low_risk`/`changed_files` anywhere yet; `cli/gate.py` does not call
  either new function; "recorded in the run record" is satisfied today only via the returned
  report dict, not a journal write).

**Acceptance Criteria:**
*(Story 2.8's ACs from `epics.md`, preserved as the contract of record.)*
- [x] Given a story's own declaration and its observed diff shape, when the story is classified
  before review runs, then classification is a pure function of already-gathered facts -- no
  I/O, no model call, no hidden state -- mirroring `classify_doc_only_declaration`'s own shape
- [x] And the classification is recorded in the run record, never a silent choice
- [x] Given any classified story, regardless of tier, when review runs, then the independent
  reviewer runs unconditionally -- the `gate_mode = "none"` human approval-only boundary is
  unchanged, and no tier ever causes review to be skipped
- [x] Given a story classified into a lower-risk tier, when its review cycles are bounded, then
  it may run fewer cycles or a cheaper review pass than the repo-wide default, and a
  higher-risk or unclassified story is never granted a smaller allowance than today's flat
  ceiling
- [x] Given a reviewer-recommended follow-up on a story at ANY tier, including the lowest, when
  `deferred-work-check` runs, then the follow-up is captured with the same completeness
  guarantee every tier already gets -- a test reproduces the `DW-AD23-3` shape and proves it
  is captured, never silently dropped, for every defined tier
- [x] And `max_followup_reviews` (or an equivalent cap) is never lowered, for any tier, below
  what `deferred-work-check` can still fully capture

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (low 3, medium 0, high 0)
- defer: 1 (low 1, medium 0, high 0)
- reject: 11 (low 11, medium 0, high 0)
- addressed_findings:
  - `[low]` `[patch]` `test_review_budget_followup_capture_is_identical_regardless_of_review_tier` asserted two facts side by side (a tier classification, and a hardcoded fixture block's parse result) without a real causal link between them -- rewrote so the block's `reason:` text is built FROM `classify_review_tier`'s own returned report, making the tier value genuinely drive what gets parsed.
  - `[low]` `[patch]` `classify_review_tier`'s `<= 3` boundary had no test one past it (only the `== 3` inclusive case existed) -- added `test_classify_review_tier_boundary_at_four_changed_files_is_standard` to guard the exact threshold against an off-by-one mutation.
  - `[low]` `[patch]` No test exercised `changed_files=()`, the natural doc-only-style low-risk shape this story's own motivation cites -- added `test_classify_review_tier_declared_and_empty_diff_is_low`.

Findings rejected as noise (11): AC1/AC3/Success-signal "not delivered" (three framings of one already-deliberate, spec-documented scope decision -- this story's own Never clause forbids `cli/gate.py`/`core/policy.py`/`core/journal.py` wiring, and the Design Notes explicitly justify shipping the mechanism only, mirroring Story 2.4/2.5/2.6's identical established precedent in this exact file); `declared_low_risk` not type-checked and `default_max_review_cycles` not type/NaN/float-guarded (both reviewers) -- consistent with this module's own established idiom of validating only tuple-shaped structural params (`_valid_glob_tuple`-style), never scalar bool/int params, and the real production value is always policy-composed via `core/policy.py::_valid_attempt_count`, which already guarantees a non-negative int; `_REVIEW_TIERS` unused for dispatch -- the spec's own Never clause forbids a third tier, so the desync scenario cited cannot occur; hardcoded constants with no policy-override path -- explicitly justified in this spec's own Design Notes and forbidden from `core/policy.py` wiring by the Never clause; `"standard"` conflating "evaluated standard" with "unclassified" -- an explicitly reasoned Design Notes resolution mirroring Story 2.4's own identical precedent; no dead-code meta-test -- speculative tooling advice unrelated to a concrete defect in this diff.

Finding deferred (1): `epics.md`'s Story 2.8 entry omits the `**Surface:**` line every sibling Epic-2 story (2.1-2.7) carries, even though the governing `SPEC.md` already unambiguously scopes `surface: [core/gate.py]` -- a pre-existing, low-impact planning-artifact gap outside this story's own scope (`epics.md` is not in the Code Map), logged to `deferred-work.md`.

## Design Notes

**This spec supersedes an orphaned prior attempt.** `spec-2-8-a-low-risk-storys-review-runs-
lighter-never-absent.md` (no `-2` suffix, created 2026-08-11 by bmad-loop run
`20260811-190409-5c73`) claims `status: in-review` with every task checked, and
`deferred-work.md` carries a detailed, evidence-backed entry describing this same mechanism as
already shipped. Neither claim holds: `git diff` against that spec's own `baseline_revision`
shows ZERO changes to `core/gate.py`/`test_gate.py`/`test_deferred_work.py`, no occurrence of
`classify_review_tier`/`resolve_review_cycles` exists anywhere in the tree, `sprint-status.yaml`
lists this story as `backlog`, and this run's own `state.json` starts fresh (`phase:
dev-running`, `spec_file: null`, `baseline_commit` at today's HEAD). Forensics (dangling-object
search across the shared checkout) found no recoverable commit -- the prior run's code changes
were written and evidenced live in the working tree but never `git add`ed, then a working-tree
reset wiped them while leaving the gitignored `implementation-artifacts/` spec and ledger
untouched (that directory sits outside git's purview entirely, per this repo's Tier-3
convention), orphaning both to describe code that no longer exists. Per this workflow's own
Route rule (step-01 §5: only a `draft`-status existing spec resumes; anything else mints a new
slug), this is treated as a fresh attempt, not a resumption. Both orphaned artifacts are left
untouched (never modify existing `deferred-work.md` entries; the old spec file is left as
historical wreckage) -- this note exists so a future reader hitting the same slug collision
understands why two `spec-2-8-*` files exist.

**Why an AND-gate, not doc-only's OR-gate.** `classify_doc_only_declaration` passes on
`declared OR has-changes` because its risk is "wrongly failing a legitimate no-diff story" --
being lenient costs nothing but a green result on nothing to check. Review-tier classification's
risk is the opposite: being lenient grants LESS scrutiny to something that might deserve more.
Trusting either signal alone would let a story get cheaper review it never earned. Requiring
both to agree is the conservative choice a cost-reduction mechanism owes the safety property
`DW-AD23-3` is explicit about protecting.

**Why `"standard"` doubles as "unclassified".** This story ships no CLI/journal wiring (see
below), so no real caller invokes `classify_review_tier` yet at all. A story nobody classifies
never has its `default_max_review_cycles` touched by either new function, so it silently keeps
today's flat ceiling -- the governing Spec's CAP-2's "unclassified" case holds by simple
non-invocation, the same resolution Story 2.4's own "unclassified" story already relies on.

**Why no new `MRS-GATE-*` code.** `classify_review_tier` cannot fail -- every input combination
produces a valid tier, never an error condition -- and `resolve_review_cycles` only raises for a
programmer bug (an out-of-vocabulary tier), never a `Finding`-worthy runtime state.
`describe_gate_mode` (Story 2.5) already established that not every function in this file needs
a registered code.

**Why the unconditional `>= 1` floor applies to `"standard"` too.** AC2 reads "no tier ever
causes review to be skipped" -- an absolute guarantee, not one scoped to the low tier alone.
`core/policy.py::_valid_attempt_count` permits `max_review_cycles == 0`; flooring both branches
protects the guarantee unconditionally rather than trusting an upstream validator this module
has no import path to (AD-4 forbids depending on `core/policy.py`'s own validators here).

**Why `_LOW_RISK_MAX_CHANGED_FILES = 3` and `_LOW_TIER_MAX_REVIEW_CYCLES = 1` are judgment
calls, not discovered constants.** No existing threshold in this codebase measures "how many
changed files count as a small, plausibly-mechanical diff" -- the governing Spec explicitly
leaves this open. `3` admits a single-file change or a small, tightly-coupled production+test
pair/trio while excluding anything wider. `1` is the cheapest non-zero cycle count -- the
minimum that still satisfies AC2's floor -- since AC3 only requires "fewer cycles," not a
specific number.

**Why CLI/journal wiring is out of scope.** The governing Spec's own `surface:` field names only
`core/gate.py`. Story 2.4 resolved the identical "recorded in the run record" AC wording via its
own returned `report` dict; this story follows the same resolution. Unlike 2.4, a real journal
now exists (Story 3.1+) -- flagged explicitly in the `deferred-work.md` entry as a materially
different residual risk than 2.4's own equivalent note.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all green, new tests
  included, zero regressions.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green, or only the same
  pre-existing unrelated failures already logged in `deferred-work.md` (no dependency added by
  this diff).

**Manual checks (if no CLI):**
- Confirm `grep -rn "MRS-GATE-01[2-9]\|MRS-GATE-0[2-9][0-9]"` (or similar) is empty -- this story
  registers no new finding code, so no new number should appear anywhere in `core/findings.py`
  or `core/verdict.py`.

## Auto Run Result

Status: done

**Summary of this pass.** The dev + review work for this story was already complete (commit
`eba785c2d4`, Review Triage Log entry dated 2026-08-13 already recorded) when this pass began,
but the story's own landing had failed bmad-loop's S-13.7 `spec_surface_reconcile.py` verify
gate: `core/gate.py`, `tests/unit/test_gate.py` and `tests/unit/test_deferred_work.py` had
drifted under `spec-pyforge-marshal` (and `core/gate.py` alone under the narrower
`spec-risk-tiered-review-depth`) without either owning spec's `.memlog.md` naming the changed
paths first. This pass repaired exactly that gate -- no code, test, or `<intent-contract>`
content was touched.

**Files changed this pass** (commit `d43e25ccfa`):
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  -- appended a Surface reconcile entry naming all three drifted paths.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-risk-tiered-review-depth/.memlog.md`
  -- appended a Surface reconcile entry naming `core/gate.py` (this spec's whole surface).
- `scripts/.spec-surface-baseline.json` -- re-stamped for both specs via the mutation-only
  `python scripts/spec_surface_check.py --write-baseline --spec ...`, matching the established
  precedent (e.g. commit `77bb757a42`, story 5-9's own reconciliation) so future drift is
  compared against a clean checkpoint rather than a baseline permanently stale since 2026-08-13.

**Review findings breakdown:** none -- this pass performed no code review; the story's own
review already completed in a prior pass (patch: 3, defer: 1, reject: 11; see the existing
Review Triage Log entry above).

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- OK: every tracked file governed or allowlisted;
  no drift (was: 4 gating FAIL findings).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3589 passed, 9 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 74 passed.
- `grep -rn "MRS-GATE-01[2-9]\|MRS-GATE-0[2-9][0-9]"` -- empty, confirming no new finding code.

**Residual risks:** none introduced by this pass. The pre-existing deferred item from the
story's own review (the `epics.md` Story 2.8 `**Surface:**` line gap) is unaffected and remains
logged in `deferred-work.md`.

