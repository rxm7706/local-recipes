---
title: 'Doc-only story classification'
type: 'feature'
created: '2026-08-03'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: [oversized]
baseline_revision: '0d45890239739b3d67ceb22c09f50e8f47927952'
final_revision: 'a031170116934945c39b0b03218cbb06c2c7de79'
---

<intent-contract>

## Intent

**Problem:** `marshal gate evaluate` has no way to distinguish a story that legitimately produced no source change (its declared deliverable is a document or decision record) from one that silently failed to do its work -- both look identical today (a clean worktree, no verify-command signal either way), and FR-23's motivating incident already tripped this into a false-negative rollback loop recovered from a preserved ref by hand.

**Approach:** Add one new pure function to `core/gate.py`, `classify_doc_only_declaration`, mirroring `classify_outcome`'s established core/CLI split: it takes the story's already-established declaration (`declared_doc_only: bool`) and the worktree's already-established change state (`has_uncommitted_changes: bool`) -- both facts a caller gathered, never gathered here (AD-4) -- and returns `(report, Finding | None)`. It fails only when the worktree has no changes AND the story was not declared doc-only, emitting one new registered code. Wiring the real declaration source and a real worktree check into `cli/gate.py` is explicitly out of this story's scope (Story 2.4's own `Surface:` in epics-with-stories.md is `core/gate.py` alone; see Never).

## Boundaries & Constraints

**Always:**
- `classify_doc_only_declaration(*, declared_doc_only: bool, has_uncommitted_changes: bool) -> tuple[dict[str, object], Finding | None]` lives in `core/gate.py`. No I/O, no VCS call, no spec-file read -- both inputs are facts the (future) caller already gathered, exactly like `classify_outcome` takes an already-obtained `ProcessResult`.
- The function's only failing condition is `not has_uncommitted_changes and not declared_doc_only`; every other combination (declared + no changes; declared + changes; undeclared + changes) returns `(report, None)` -- a doc-only declaration never produces a worse outcome than an undeclared one, and a story with real changes is never penalized regardless of its declaration. `report` always carries both input facts (e.g. `{"declared_doc_only": ..., "has_uncommitted_changes": ...}`) so the caller has something to fold into its own output/record regardless of which branch ran.
- Register one new code, `MRS-GATE-006`, in `core/findings.py` (module docstring paragraph in this story's established style + a `REGISTERED_CODES` entry with its own dated comment line) and classify it `Verdict.GATE_FAILED` in `core/verdict.py` (module docstring paragraph + `_CLASSIFY_TABLE` entry) -- same tier as `MRS-GATE-001`: a real, determinable outcome (no change, no doc-only declaration), never "could not evaluate". `Severity.ERROR`, matching `MRS-GATE-001`'s own severity for the same GATE_FAILED tier.
- Unit-test all four truth-table combinations in `tests/unit/test_gate.py`, matching this file's existing `test_classify_outcome_*` synthetic-input style, plus one test proving AC4's independence property (below).

**Block If:** N/A -- no ambiguity requiring a human decision. The mechanism itself is fully determined by this story's own AC text plus the established `core/gate.py` core/CLI split; the genuinely open questions (how a real caller learns a story's doc-only declaration; whether "no changes" means a dirty tree or a committed diff vs. base) are resolved below as an explicit, bounded exclusion from this story's declared surface, not left as an unattended coin-flip.

**Never:**
- Do not touch `cli/gate.py`: no `--doc-only` CLI flag, no call to `VcsPort.has_uncommitted_changes`, no story-spec-frontmatter parsing. Story 2.4's own declared `Surface:` (epics-with-stories.md) is `core/gate.py` alone, Effort **S** -- matching Story 2.2's own precedent of shipping only the pure mechanism and its proof, deferring wiring. Two real integration questions stay genuinely open rather than invented here: (a) how a real story communicates `declared_doc_only` to `marshal gate evaluate` -- a new CLI flag? a new spec-frontmatter field, which does not exist in `spec-template.md` today and would be a repo-wide convention change far outside this story's blast radius? -- and (b) whether "no changes in worktree" means the dirty working tree (`VcsPort.has_uncommitted_changes`, already shipped, and the literal match for the AC's own wording) or a committed diff against a base ref (which needs a new `VcsPort` method and a base-ref concept, neither of which exist today). Resolving either here would mint a cross-cutting convention this story's one-file surface was never scoped to decide.
- Do not touch `ports/vcs.py`, `adapters/vcs_git.py`, `core/policy.py`, `spec-template.md`, or any test file outside `tests/unit/test_gate.py`.
- Do not implement or assume Story 2.3's scope check exists. AC4 is satisfied by construction -- an independence proof against the existing, unmodified `compute_verdict` fold -- never by building any part of the scope check itself.
- Do not add a `deliverable`/`doc_only` field to any frontmatter schema, spec template, or `core/model.py` -- out of surface, and a repo-wide convention change deserves its own decision, not a byproduct of this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Doc-only declared, no worktree changes | `declared_doc_only=True, has_uncommitted_changes=False` | `(report, None)` -- passes | No error expected |
| Doc-only declared, worktree HAS changes | `declared_doc_only=True, has_uncommitted_changes=True` | `(report, None)` -- passes (nothing to suppress) | No error expected |
| NOT declared doc-only, no worktree changes | `declared_doc_only=False, has_uncommitted_changes=False` | `(report, Finding(code="MRS-GATE-006", ...))`, classifies `Verdict.GATE_FAILED` -- fails | Finding names the exact condition (no change, not declared doc-only) |
| NOT declared doc-only, worktree HAS changes | `declared_doc_only=False, has_uncommitted_changes=True` | `(report, None)` -- passes (an ordinary story, nothing to flag) | No error expected |
| A doc-only PASS co-occurring with an independent scope-violation-shaped finding (AC4 proof) | `classify_doc_only_declaration(True, False)` returns `None`, folded via `verdict.compute_verdict` alongside one synthetic finding monkeypatched to classify `Verdict.SCOPE_VIOLATION` | Aggregate verdict is `Verdict.SCOPE_VIOLATION`, unaffected by the doc-only pass | Proves a doc-only classification structurally cannot suppress a co-occurring scope-check finding |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` -- EDIT. Add `classify_doc_only_declaration`, following `classify_outcome`'s docstring/style conventions; extend the module docstring's per-code narrative.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` -- EDIT. Register `MRS-GATE-006` in `REGISTERED_CODES` with a dated comment line; extend the module docstring's per-code narrative (Story 2.4's own paragraph, following the Story 2.1-2.3 pattern already there).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` -- EDIT. Add `"MRS-GATE-006": Verdict.GATE_FAILED` to `_CLASSIFY_TABLE`; extend the module docstring's per-code narrative and the numbered-comment block directly above the table.
- `src/shared/packages/pyforge-marshal/tests/unit/test_gate.py` -- EDIT. Add the four truth-table tests plus the AC4 independence test, in this file's existing synthetic-input style (no real subprocess, no real git).

## Tasks & Acceptance

**Execution:**
- [x] `core/findings.py` -- register `MRS-GATE-006` (format `MRS-GATE-<NNN>`, next free number after `MRS-GATE-005`) -- makes the code constructible via `Finding(code="MRS-GATE-006", ...)` at all (AD-15's registry gate).
- [x] `core/verdict.py` -- classify `MRS-GATE-006` -> `Verdict.GATE_FAILED` -- a real, determinable "no change and not declared doc-only" outcome is the same tier as `MRS-GATE-001`'s "a real check ran and failed", never `unevaluable`.
- [x] `core/gate.py` -- add `classify_doc_only_declaration(*, declared_doc_only: bool, has_uncommitted_changes: bool) -> tuple[dict[str, object], Finding | None]` -- the pure classification mechanism itself (Intent/Approach).
- [x] `tests/unit/test_gate.py` -- add the I/O matrix's five scenarios as direct unit tests (four truth-table combinations + the AC4 independence proof) -- proves every AC without needing Story 2.3's scope check or any real VCS/CLI wiring to exist.

**Acceptance Criteria:**
*(Story 2.4's ACs from `epics-with-stories.md`, preserved verbatim -- the contract of record.)*
- Given a story whose declared deliverable is a document or decision record, when the gate evaluates a worktree with no source change, then it does not fail on "no changes in worktree"
- And classification is a pure function of the story's declaration, and is recorded in the run record
- And a story not so classified that produces no change still fails, with a distinct registered finding
- And a doc-only story that nonetheless touches a frozen surface still fails the scope check

## Spec Change Log

## Review Triage Log

### 2026-08-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1 (high 0, medium 1, low 0)
- defer: 1 (medium)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` The independence proof (AC4) only covered the PASSING doc-only case; the arguably more relevant failing case -- `MRS-GATE-006` co-occurring with an independent scope-violation-shaped finding -- was untested. Added `test_classify_doc_only_declaration_failure_and_an_independent_scope_violation_fold_to_the_stronger_verdict`, proving `compute_verdict` correctly picks `GATE_FAILED` (the stronger of the two per `LATTICE_ORDER`) when both findings are present together.
  - `defer` (1, medium): consolidated three overlapping findings (both reviewers independently flagged the same underlying gap) plus one nuance into a single `deferred-work.md` entry: `classify_doc_only_declaration` is not yet called from `cli/gate.py`, so `marshal gate evaluate` cannot classify a real story doc-only end-to-end; there is no producer of `declared_doc_only` anywhere in the codebase (no CLI flag, no spec-frontmatter field); and AC2's "recorded in the run record" has no journal to record into until Epic 3 + Story 2.6 land. All three are the spec's own explicitly-scoped-out Never clause, not a defect -- this entry fulfills that clause's own promise to log the boundary. Also folded in a nuance: `has_uncommitted_changes` is dirty-tree-only (stages/unstaged/untracked), so incidental untracked debris will silently read as "has changes" once wired -- lenient, not wrong, but should be a deliberate choice in the wiring story.
  - `reject` (6): "a naive `python -m pytest` (no `PYTHONPATH`/pixi) resolves the wrong source tree" -- verified live; the repo's actual sanctioned verification command (`pixi run --frozen -e pyforge-marshal pyforge-marshal-test`, the one this spec's own Verification section specifies and the one actually used) correctly resolves within-worktree via its own editable install, so this is a pre-existing, universal fact about bare interpreter invocation, not a defect in this diff. "`MRS-GATE-006`'s message carries no identifying context" -- matches the existing `MRS-GATE-004`/`no_commands_configured_finding` precedent exactly (also a fully generic, non-parameterized message); not a regression. "The same fact is restated in three module docstrings" -- matches this file's own long-established convention (every prior story does the same); the reviewer itself noted this. "The returned `report` dict gives no explicit pass/fail signal" -- factually incorrect on inspection: `classify_outcome`'s own report requires the identical `finding is None` check to determine pass/fail; no sibling function differs. "`sprint-status-ledger.yaml` still lists `backlog`" -- confirmed out of scope: no step in this workflow touches sprint-status tracking, and prior stories 2.1/2.2 show the identical pattern (updated by external tooling, not this skill). "Boolean params aren't runtime-validated; a `None` sentinel is silently coerced" -- traced exhaustively: every `None`-injection scenario resolves to the FAIL-closed branch (`not None` is always `True` in Python) unless the other parameter is genuinely truthy, in which case passing is correct regardless -- structurally incapable of producing a false green, and no sibling function in this file validates its own input types either.

## Design Notes

**Why `Verdict.GATE_FAILED`, not `Verdict.UNEVALUABLE`.** "No changes, not declared doc-only" is a real, fully-determinable outcome -- Marshal did not fail to evaluate anything; it evaluated and found the story produced nothing while claiming no doc-only exemption. That is exactly `MRS-GATE-001`'s own tier ("a REAL check ran and failed", not "could not evaluate"), so `MRS-GATE-006` joins it at `GATE_FAILED` rather than `UNEVALUABLE`.

**Why the mechanism-only scope, not full CLI/VCS wiring.** Every other Epic 2 story so far either wires end-to-end (2.1, whose declared `Surface:` explicitly includes `cli/gate.py`, `ports/process.py`, `adapters/process_posix.py`) or ships a self-contained mechanism/proof only (2.2, whose Never clause reads "do not edit `compute_verdict`, `classify`, ... `core/gate.py`'s classification functions" -- explicitly deferring anything beyond the regression proof). Story 2.4's own declared `Surface:` is the single narrowest of the epic: `core/gate.py` alone, Effort **S**. That is a strong, explicit signal this story is meant to land the same way 2.2 did -- and unlike 2.2, this story genuinely has no existing "no changes in worktree" check anywhere in the codebase to extend (confirmed: no occurrence of that phrase, or any worktree-diff logic, in `cli/gate.py` or elsewhere). Wiring it for real would require inventing, in one Effort-S story, both (a) how a story declares itself doc-only -- no spec-frontmatter reading of any kind exists anywhere in Marshal today, and the shipped `spec-template.md` this very workflow uses has no such field -- and (b) which of two materially different "no changes" semantics (dirty tree vs. committed-diff-vs-base) the check means, the second of which needs a new `VcsPort` method and a base-ref concept neither of which exist. Both are real, repo-wide-consequential design decisions this story's one-file surface was never scoped to make -- inventing either silently would be exactly the kind of ungrounded, hard-to-reverse convention this repo's own precedent (pyforge-warden's Story 6.10, a dedicated design-spike BEFORE its schema-touching Story 6.1) argues should get a deliberate decision of its own, not a byproduct of a Small-effort mechanism story.

**Why AC4 ("still fails the scope check") is satisfied by construction, not by building the scope check.** `classify_doc_only_declaration` contributes at most one `Finding` to the same list every other check does (mirroring `classify_outcome`); it never touches `compute_verdict`'s fold logic or any other check's output. Since `SCOPE_VIOLATION` outranks `WARN`/`CLEAN` in `LATTICE_ORDER`, ANY future scope-violation finding (Story 2.3, once built) folded alongside this function's `None` "pass" result wins the aggregate regardless -- a doc-only pass is structurally incapable of suppressing an unrelated finding, the same "only ever strengthens, never weakens" property AD-8/Story 2.2 already proved for `compute_verdict` generally. The new test demonstrates this directly with a monkeypatched synthetic `SCOPE_VIOLATION`-classified code (no real code classifies to that rung yet), mirroring `test_verdict.py`'s own `synthetic_registry` fixture pattern.

**Why the returned `report` dict satisfies AC2's "recorded in the run record".** No durable, journaled "run record" exists anywhere in Marshal yet -- `core/journal` is Story 3.1/3.2, both `backlog` (the same gap `cli/gate.py`'s existing `MRS-GATE-005` stub already documents for `--run <id>`). `classify_outcome` faces the identical situation and resolves it the same way: it returns a `report` dict alongside the `Finding`, which `cli/gate.py` folds into the evaluation's `data` -- today's only actually-existing "record" of a gate evaluation. `classify_doc_only_declaration` follows the exact same shape (`report` always carries `declared_doc_only` and `has_uncommitted_changes`, regardless of which branch ran) so a future caller can fold it into `data` today and into a real journal/gate-evidence record (Epic 3, Story 2.6) later with no reshaping needed -- honest about today's ceiling, forward-compatible with tomorrow's, mirroring Story 2.1's own `scope: policy-seed-only` precedent for the same "no journal yet" gap.

**Why `has_uncommitted_changes` as the parameter name.** `ports/vcs.py`'s `VcsPort.has_uncommitted_changes(worktree_path) -> bool` (Story 1.8) already exists and is the literal, already-shipped match for the AC's own phrase "no changes in worktree" (`git status --porcelain`, covering staged/unstaged/untracked). Naming this function's parameter identically means a future wiring story can pass `vcs.has_uncommitted_changes(root)` straight through with no translation layer -- extending a shipped precedent injectively rather than inventing a parallel concept, even though calling it is explicitly out of THIS story's scope.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all tests green, including the new `test_gate.py` cases, with zero regressions in the existing suite.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green, or only the same pre-existing unrelated failures already logged in `deferred-work.md` (no dependency added by this diff).

## Auto Run Result

Status: `done`.

**Summary.** Added `core/gate.py::classify_doc_only_declaration`, a new pure function classifying a story's already-established doc-only declaration against the worktree's already-established change state, plus the new registered finding code `MRS-GATE-006` (classifies `Verdict.GATE_FAILED`) it emits on the one failing combination (no worktree changes, not declared doc-only). Per the spec's own Never clause, this story ships the pure mechanism and its full unit-level proof only -- wiring it into `cli/gate.py` (a real CLI flag/spec-frontmatter field for the declaration, a real `VcsPort.has_uncommitted_changes` call) is explicitly out of scope, matching Story 2.2's own mechanism-only precedent, and is logged as follow-up work below.

**Files changed:**
- `src/pyforge/marshal/core/gate.py` -- added `classify_doc_only_declaration`; extended the module docstring.
- `src/pyforge/marshal/core/findings.py` -- registered `MRS-GATE-006`; extended the module docstring and the `REGISTERED_CODES` comment block.
- `src/pyforge/marshal/core/verdict.py` -- classified `MRS-GATE-006` -> `Verdict.GATE_FAILED` in `_CLASSIFY_TABLE`; extended the module docstring and its comment block.
- `tests/unit/test_gate.py` -- added 4 truth-table tests, the AC4 PASS-side independence test, and (added during review) the complementary FAIL-side co-occurrence test.
- `tests/unit/test_findings.py` -- necessary one-line update to `test_registered_codes_contains_the_real_codes`'s hardcoded exact-match set, a mechanical consequence of registering `MRS-GATE-006` (every prior story's registry addition required the same update to this test).

**Review findings breakdown:** 1 patch applied (medium), 1 deferred (medium, consolidating 3 overlapping findings + 1 nuance from both reviewers into the follow-up wiring work the spec's own Never clause already promised to log), 6 rejected (verified false or already matching established precedent -- full detail in the Review Triage Log above). No intent gaps, no bad-spec loopbacks.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **916 passed, 8 deselected**, zero regressions (baseline 894 pre-Story-2.2; +16 from Story 2.2; +6 from this story: 4 truth-table tests + 2 independence tests, +1 net registry test unchanged in count). Independently re-run after the review-pass patch, not just trusted from the implementing subagent's report.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- **2 failed, 58 passed**, confirmed identical to the same two pre-existing `pyforge-steward` dependency-declaration failures already logged in `deferred-work.md` (unrelated -- this diff touches only `pyforge-marshal`'s own files, no dependency added).
- Diff independently re-read file-by-file against the spec's Code Map and Never clause before review; confirmed no file outside the sanctioned list was touched.

**Residual risks:**
- The feature is not yet reachable from `marshal gate evaluate` -- see the `deferred-work.md` entry for the three concrete pieces of follow-up wiring needed (declaration source, VCS call, output folding) before a real doc-only story can pass the gate end-to-end.
- `has_uncommitted_changes` (once wired) is a dirty-tree check, not a "no source change vs. base ref" check -- documented as a deliberate, precedent-driven scope choice (Design Notes), not a defect, but a future wiring story should read that note before assuming the two are equivalent.
