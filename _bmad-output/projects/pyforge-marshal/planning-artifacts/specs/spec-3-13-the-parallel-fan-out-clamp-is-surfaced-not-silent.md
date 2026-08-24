---
title: 'The parallel-fan-out clamp is surfaced, not silent'
type: 'feature'
created: '2026-08-12'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: '888173a802a9ca27b5c8c463aff91f83dc14f3e6'
---

<intent-contract>

## Intent

**Problem:** The vendored `bmad_loop==0.9.0` engine silently clamps `scm.max_parallel` to `1` with zero diagnostic (confirmed direct read: `policy.py:448-451` states Phase 5 fan-out "is not built yet"; `policy.py:815-817,841-842` clamp any requested value via `min(requested_parallel, 1)`, discarding the real request without logging, returning, or attaching it to any warning). Marshal's own rendered `.bmad-loop/policy.toml` hard-codes the identical `max_parallel = 1` (`adapters/harness_bmadloop.py:320`) with no explanation, and the gap is untracked — Story 6.8's `upstream-register.json` tracks 8 other `bmad_loop` gaps but not this one.

**Approach:** Add `max_parallel` as a schema-blessed policy seed key (mirrors `max_dev_attempts`/`idle_threshold_minutes`'s existing numeric-ceiling shape) so a project requesting `max_parallel > 1` composes cleanly instead of tripping the generic "unknown key" finding, and raise a new registered WARN advisory naming the clamp and its upstream cause whenever the resolved value exceeds 1. Register the gap as a 9th `upstream-register.json` entry, and record a standalone written readiness assessment of Marshal's own N-stories-in-flight machinery (worktree isolation, journal, supervisor, landing) as a scoped starting point for whenever an upstream scheduler ships.

## Boundaries & Constraints

**Always:** the advisory is WARN-severity and never changes an OK envelope's exit code; `max_parallel` composes through the existing `defaults -> project -> flags` fold (AD-16) like every other seed key; the 9th `upstream-register.json` entry matches the exact `{id, gap, workaround, compensating_fr, upstream_status}` shape of the existing 8; the readiness assessment is a standalone, git-tracked planning artifact, not buried in this spec's own prose.

**Block If:** nothing identified — this story adds one seed key, one finding code, one register entry, and one written assessment, none of which requires a human decision mid-implementation.

**Never:** touch the vendored `bmad_loop` package; build or claim actual concurrent story dispatch; redesign `scm.isolation`/`branch_per` or the journal's multi-writer model (both are read for the assessment, not modified); write the operator's raw requested value into the rendered `.bmad-loop/policy.toml` — `bmad_loop`'s own `loads()` clamps to 1 regardless of what's on disk, so writing anything else there would misrepresent what actually governs behavior.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | no `max_parallel` key set anywhere | resolves to `1`, no advisory finding | No error expected |
| Requested >1 | `marshal-policy.toml` sets `max_parallel = 4` | resolves to `4` (value preserved, not silently floored by Marshal); a registered WARN finding names the clamp and `bmad_loop` 0.9.0's unbuilt Phase 5 scheduler as cause | No error — WARN only, verdict stays in the OK half of the lattice |
| Exactly 1 | `max_parallel = 1` explicitly | resolves to `1`, no advisory (matches the harness's own effective behavior) | No error expected |
| Malformed | `max_parallel = "four"`, `0`, or `true` (bool) | falls back to default `1` via the existing malformed-seed-value finding | Existing `MRS-POLICY-003` pattern; no new advisory fires |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` -- EDIT. Add `"max_parallel"` to `_SEED_KEYS` (~policy.py:185-206) and `DEFAULT_POLICY["max_parallel"] = 1` (~policy.py:269-356, matching `bmad_loop`'s own `ScmPolicy.max_parallel` default). New validator `_valid_parallel_count(value)` mirroring `_valid_attempt_count` (~policy.py:770-773) but requiring `int`, not `bool`, `>= 1` (mirrors `bmad_loop`'s own `PolicyError` floor at `policy.py:815-817` in the vendored package). Add the merge call to the `seed = {...}` dict in `compose()` (~policy.py:1338-1429), reusing finding code `"MRS-POLICY-003"` for malformed values like every other seed field. After the `seed` dict is built and before `EffectivePolicy(...)` is constructed (~policy.py:1429-1431), add a small helper `_max_parallel_clamp_finding(value) -> Finding`, mirroring `_project_slug_finding`'s shape (~policy.py:912-936), and call it — appending to `findings` — when the resolved `max_parallel` value is `> 1`. Message names both the value and the upstream cause, e.g. `f"max_parallel={value} requested, but bmad_loop 0.9.0's own Phase 5 parallel-fan-out scheduler is unbuilt and clamps every run to 1 -- the request has no effect"`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` -- EDIT. Register `"MRS-POLICY-007"` in `REGISTERED_CODES` (~findings.py:1207-1212, alongside the existing `MRS-POLICY-001..006` block).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py` -- EDIT. Classify `"MRS-POLICY-007": Verdict.WARN` in `_CLASSIFY_TABLE` (~verdict.py:721-726, alongside `MRS-POLICY-005`'s identical WARN precedent).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json` -- EDIT. Append a 9th entry, same shape as the existing 8: `id: "parallel-fan-out"`, `gap` quoting the `policy.py:448-451`/`815-817,841-842` clamp (see Intent), `workaround` naming this story's `MRS-POLICY-007` advisory and the fact Marshal's own rendered policy still writes the harness's stock `1`, `compensating_fr: "FR-184"`, `upstream_status: "open"`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/parallel-fan-out-readiness-assessment.md` -- NEW. Written readiness assessment (CAP-3), one subsection per: worktree isolation (Marshal's own worktree is per-project not per-story; per-story isolation is delegated to `bmad_loop`'s own `[scm] isolation=worktree, branch_per=story` config; whether the engine ever runs two such worktrees concurrently vs. strictly sequentially is unverified from Marshal's side), journal multi-writer design (the `(writer_id, counter)` append protocol and `O_APPEND` primitive are proven safe under concurrent writers by a real 9-thread test, but the design's own stated goal was "a supervisor plus one CLI session", not N independently-dispatched story sessions — no caller today mints N per-story `writer_id`s within one run), supervisor (one supervisor process watches exactly one `watched_pid`/`run_id` today; N concurrent sessions would need N separate supervisor processes, and nothing guards two `marshal factory spin` invocations against the same loop home running concurrently), landing path (`marshal land` already batches multiple gated stories into one wave/PR per invocation, but multiple *invocations* are not coordinated with each other beyond a WARN-only advisory lock on the deferred-work ledger and GitHub's own `--match-head-commit` merge atomicity — the land↔supervisor cross-process lock a code comment calls for does not exist). Concludes each area as either "holds" or "unverified/blocking", explicitly scoped as a starting point, not a readiness certification.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/tests/unit/test_policy.py` -- EDIT. Unit tests for the full I/O matrix above: default silent, `>1` fires `MRS-POLICY-007` naming the value, exactly-`1` stays silent, malformed value falls back via existing `MRS-POLICY-003` machinery with no `MRS-POLICY-007`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/tests/unit/test_upstream_cli.py` -- EDIT. One regression assertion that the real on-disk register's `parallel-fan-out` entry is present and round-trips through `marshal upstream` (mirrors `test_the_real_register_content_round_trips`'s existing subset-assertion shape, ~test_upstream_cli.py:81-120 -- no count-pinning).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- log any scope narrowed during implementation (none anticipated).

## Tasks & Acceptance

**Execution:**
- [x] `core/policy.py` -- add `max_parallel` seed key: validator, `DEFAULT_POLICY` entry, `_SEED_KEYS` membership, `compose()` merge-fold wiring, and the post-merge `MRS-POLICY-007` clamp-advisory check.
- [x] `core/findings.py` -- register `MRS-POLICY-007`.
- [x] `core/verdict.py` -- classify `MRS-POLICY-007` as `Verdict.WARN`.
- [x] `upstream-register.json` -- append the 9th `parallel-fan-out` entry.
- [x] `parallel-fan-out-readiness-assessment.md` -- new written readiness assessment (worktree isolation, journal, supervisor, landing).
- [x] Unit tests for the `max_parallel` I/O matrix in `test_policy.py`.
- [x] Regression assertion for the new register entry in `test_upstream_cli.py`.
- [x] `deferred-work.md` -- log any narrowed scope. (Nothing deferred -- see Spec Change Log instead: two extra files needed touching to keep the suite green, both completed, not follow-up work.)

**Acceptance Criteria:**
*(Story 3.13's ACs from `epics.md`, preserved as the contract of record.)*
- Given a project policy that requests `max_parallel > 1`, when policy is composed, rendered, or preflight runs, then a registered finding/advisory names the clamp and its cause — `bmad_loop` 0.9.0's own unbuilt Phase 5 fan-out — rather than the request silently vanishing
- And `upstream-register.json` gains a new entry for this gap in the same shape as its existing 8 entries, surfaced by `marshal upstream`
- And a written readiness assessment names what Marshal-side machinery (worktree isolation, the journal's multi-writer design, the supervisor, the landing path) already holds for N-stories-in-flight and what remains unverified — a scoped starting point, not a promise that one ships from this story
- And nothing in this story modifies the vendored `bmad_loop` package or claims concurrent dispatch ships now
- And a regression test proves the advisory fires for a `max_parallel > 1` policy value and stays silent at the default of 1

## Spec Change Log

- **Test path correction.** The Code Map cites `.../pyforge-marshal/src/pyforge/marshal/tests/unit/test_policy.py` and `.../test_upstream_cli.py`. The real tree has no `tests/` nested under `src/pyforge/marshal/` -- the actual, and only, test directory is `src/shared/packages/pyforge-marshal/tests/unit/{test_policy.py,test_upstream_cli.py}`. Edited there; no functional change, the Code Map's own path was simply approximate.
- **Two files beyond the Code Map required edits to keep the suite green.** `cli/config.py` and `src/pyforge/marshal/schemas/policy.json` are not named in the Code Map, but `tests/unit/test_cli.py::test_field_order_matches_the_closed_policy_vocabulary` enforces a derive-don't-declare completeness check: `cli/config.py`'s `_FIELD_ORDER` tuple and `schemas/policy.json`'s `required`/`properties` keys must both equal `core.policy._ALL_KEYS` exactly, or `marshal config`/`materialize()`'s wire shape silently drops the new key while it is still hashed into `content_hash`. Added `max_parallel` to `_FIELD_ORDER` (render order, after the 4 budget ceilings), to `_UNSETTABLE_KEYS`/`_PROJECT_POLICY_ONLY_KEYS` (excluded from `--set`, the same "no AC asks for a CLI override surface" reason `idle_threshold_minutes` and the 4 budget ceilings already carry -- `marshal-policy.toml` is the only way to set it), and to `schemas/policy.json`'s `required`/`properties`. Four additional hardcoded-literal test assertions (`test_cli.py::test_config_prints_all_twenty_keys`, `test_findings.py::test_registered_codes_contains_the_real_codes`, `test_policy.py::test_seed_view_returns_all_ten_seed_fields` (renamed to `..._eleven_seed_fields`), `test_policy.py::test_seed_fields_are_not_reachable_as_public_attributes`, `test_policy.py::test_schema_file_declares_the_twenty_keys`) also needed `max_parallel` added to stay accurate -- none of this narrows the story's scope, it is exactly what "compose cleanly instead of tripping the generic unknown-key finding" (the Intent's own wording) requires end-to-end.
- **Verification repair (post-landing): one file beyond marshal's own tree, unrelated to this story's intent.** The repo-wide deterministic gate `pixi run --frozen -e pyforge-ci pyforge-deps-test` failed after this story's commit landed -- but the failure was in `pyforge-steward`, not `pyforge-marshal`: `dashboard/apps.py` and `dashboard/cache.py` (both pre-existing, from Story 9.1, untouched by this diff) import `django` unconditionally at module level, which `tests/packaging/test_dependency_completeness.py::test_every_hard_import_is_a_declared_dependency` flags as undeclared. Confirmed pre-existing and orthogonal by diffing against `baseline_revision`: this story's own diff never touches any `pyforge-steward` file, and `apps.py`/`cache.py` are byte-identical between `baseline_revision` and the failing commit. Declaring `django` in `pyforge-steward`'s `[project.dependencies]` was not an option -- AD-1/AD-13 requires the dashboard to ship ONLY behind its extra -- so the fix registers the two files as an accepted, rationale-carrying entry in `test_dependency_completeness.py`'s existing `BASELINE_UNDECLARED_IMPORTS` ratchet (the same mechanism already used there for `pyforge-steward`'s `_http` violation), which is the file's own sanctioned path for a pre-existing, by-design violation owned by a different package. No `pyforge-marshal` file, and nothing inside `<intent-contract>`, was touched.

## Review Triage Log

### 2026-08-12 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel, blind)
- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 1, low 2)
- defer: 2 (low 2)
- reject: 7 (low 7)
- addressed_findings:
  - `[medium]` `[patch]` `tests/unit/test_policy.py::test_effective_policy_rejects_non_policy_field_seed_value`'s hand-built `_seed={...}` literal held only 10 of the now-11 required seed keys (missing `max_parallel`), so `EffectivePolicy.__post_init__`'s key-set check fired first and the test silently stopped exercising the per-value `isinstance(field, PolicyField)` branch its own docstring claims to test. Fixed: added a `"max_parallel": PolicyField(...)` entry and corrected the comment's "10" to "11".
  - `[low]` `[patch]` `cli/config.py::_policy_fields_payload`'s docstring still said "The flat 22-key document" while this diff's other three same-file "22-key"/"23-key" mentions were already bumped. Fixed: updated to "23-key".
  - `[low]` `[patch]` `_valid_parallel_count` was the only int-typed seed validator with no magnitude guard against an arbitrary-precision int reaching `_max_parallel_clamp_finding`'s f-string formatting and breaking `compose()`'s "never raises on malformed content" contract for a direct programmatic caller (reproduced live: `10**5000+7` raises `ValueError` inside `compose()`) -- its sibling `_valid_positive_number` already guards the identical hazard class. Not reachable via any real `marshal-policy.toml` (`tomllib`'s own parser hits the same digit limit first). Fixed: added the same `float(value)`/`OverflowError` magnitude probe `_valid_positive_number` uses, plus a regression test mirroring `test_budget_ceiling_rejects_an_arbitrary_precision_int_without_raising`.
  - `[low]` `[defer]` `cli/config.py`'s `_UNSETTABLE_KEYS` comment ("Naming any of these 9 keys...") and two test names (`test_config_prints_all_twenty_keys`, `test_schema_file_declares_the_twenty_keys`) hardcode a policy-vocabulary key count that was already stale before this story (the frozenset held well over 9 members, and the real count was already 22, not 20, prior to `max_parallel`). This diff's own docstring bumps inside those two tests (22->23) touched the count text but not the function names, unlike the sibling `test_seed_view_returns_all_ten_seed_fields` -> `..._eleven_seed_fields` rename in the same diff. Pre-existing drift this story sits adjacent to but did not cause. Logged as `DW-FU-3-13` to `deferred-work.md`.
  - `[low]` `[reject]` Story 3.13's `Surface:` line in `epics.md` names `adapters/harness_bmadloop.py`, but the shipped diff never touches it. Not a gap: the spec's own Design Notes explain why compose-time coverage (already threaded into `init`/`preflight`/`config`) satisfies the AC's "composed, rendered, or preflight runs" wording without a render-time change, and rendering the operator's raw value into `.bmad-loop/policy.toml` would misrepresent what `bmad_loop`'s own `loads()` actually does with it (always clamps to 1 regardless).
  - `[low]` `[reject]` The readiness-assessment doc attributes its own scope boundary to "this story's Never bullet" while the reviewer found no literal "Never" heading in `epics.md`. Not a gap: the citation is accurate against the actual governing artifact (this spec's own `<intent-contract>` **Never:** bullet, "touch the vendored `bmad_loop` package..."), which the reviewer did not have direct access to search.
  - `[low]` `[reject]` The readiness doc's "Overall verdict" section was read as overstating a clean two-of-four split. Not a gap: each per-area verdict already states its own nuance (the journal's "N-writer CALLER does not exist yet"; landing's "UNVERIFIED/blocking for cross-invocation") in the body directly above the summary line the reviewer quotes -- the summary is a compression of, not a contradiction of, the body.
  - `[low]` `[reject]` `_valid_parallel_count` imposes no upper bound, so an implausibly large value composes with the same undifferentiated WARN as a small one. By design: the spec's own I/O matrix and this validator's docstring state the floor is 1, not a ceiling, and no AC or constraint asks for a sanity ceiling.
  - `[low]` `[reject]` A project that declares `max_parallel > 1` carries the `MRS-POLICY-007` WARN on every subsequent invocation with no suppression. By design: WARN findings persist for as long as their triggering condition holds, identical to every other WARN-classified policy finding in this codebase -- not novel to this story, and the AC explicitly wants a persistent, non-silent advisory.
  - `[low]` `[reject]` The same core fact (the clamp and its cause) is restated near-verbatim across seven locations in the diff. Consistent with this codebase's established documentation-dense house style (every touched function/module in this diff already carries this density pre-story); not a defect.
  - `[low]` `[reject]` The new `test_the_real_register_content_includes_the_parallel_fan_out_entry` duplicates its setup block from the adjacent `test_the_real_register_content_round_trips` rather than factoring a shared fixture. A minor style nitpick against an established repo pattern of explicit, independently-readable tests; not worth the scope creep of refactoring a pre-existing sibling test to introduce a new abstraction.

## Design Notes

**Why compose-time, not render-time.** `compose()` is already the single point threaded into all three CLI entry points that touch policy (`cli/init.py::run_init` and `run_preflight`, `cli/config.py::run_config`) — a compose-time finding reaches "composed, rendered, or preflight runs" (the AC's own wording) with zero extra wiring, since `run_config`'s `--write-harness-policy` render branch only proceeds after `compose()` has already run and only gates on verdict, which WARN does not block. `render_policy_toml`'s own `[scm]` block stays untouched: it hardcodes `max_parallel = 1` today, and that is already the truthful effective value regardless of what an operator requests, since `bmad_loop`'s own `loads()` reads and clamps whatever is on disk to 1 unconditionally.

**Why a new seed key rather than leaving `max_parallel` unrecognized.** Without a schema-blessed vocabulary entry, an operator setting `max_parallel` in `marshal-policy.toml` today gets the generic "unknown policy key" `MRS-POLICY-001` — indistinguishable from a typo, and unable to carry a message naming the specific upstream cause the AC requires.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: all import-linter contracts hold.

**Manual checks (if no CLI):**
- `marshal upstream --format json` lists 9 entries including `parallel-fan-out`.
- A throwaway `marshal-policy.toml` with `max_parallel = 4`, run through `marshal config`, shows an `MRS-POLICY-007` WARN finding in the envelope and exits 0.

## Auto Run Result

Status: done

**Summary.** Implementation (commit `361290c8e5`) landed `max_parallel` as a schema-blessed policy seed key, the `MRS-POLICY-007` WARN advisory naming the clamp and its upstream cause, a 9th `upstream-register.json` entry, and the standalone N-stories-in-flight readiness assessment -- all per the intent contract, reviewed in pass 1 (3 patches applied, 2 deferred, 7 rejected as noise/by-design; see Review Triage Log). That commit's own deterministic verification (both spec-listed commands) was green.

This repair pass addressed a *separate*, repo-wide deterministic gate (`pixi run --frozen -e pyforge-ci pyforge-deps-test`) that failed after `361290c8e5` landed. Root cause was pre-existing and orthogonal to this story: `pyforge-steward`'s `dashboard/apps.py` + `dashboard/cache.py` (Story 9.1, untouched by this diff, byte-identical since before `baseline_revision`) import `django` unconditionally, which the repo-wide dependency-completeness scanner flags as undeclared. Fixed (commit `888173a802`) by registering both files in `test_dependency_completeness.py`'s existing `BASELINE_UNDECLARED_IMPORTS` ratchet -- the same accepted-violation mechanism already used there for `pyforge-steward`'s `_http` entry, and the same fix shape as the `20ad57a62f` precedent that closed an identical class of pre-existing `pyforge-deps-test` failure blocking a different story's land. No `pyforge-marshal` file, and nothing inside `<intent-contract>`, was touched by this repair.

**Files changed (this repair):**
- `tests/packaging/test_dependency_completeness.py` -- added a `django` entry to `BASELINE_UNDECLARED_IMPORTS["pyforge-steward"]`, with rationale.

**Review findings breakdown:** unchanged from pass 1 (see Review Triage Log) -- this repair introduced no new review-scope change; it is a deterministic-verification fix outside the story's own diff.

**Follow-up review recommendation:** `false` -- one small, precedented, rationale-carrying entry in an existing ratchet list; no marshal behavior changed.

**Verification performed (this repair):**
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- was failing (steward/django), now 67 passed.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3502 passed, 9 deselected (re-confirmed green, unaffected by this repair).
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- 3 contracts kept, 0 broken (re-confirmed).
- `marshal upstream --format json` -- 9 entries, `parallel-fan-out` present with the expected `gap`/`workaround`/`compensating_fr: FR-184`/`upstream_status: open` shape.
- Throwaway `marshal-policy.toml` with `max_parallel = 4` through `marshal config --project-policy ... --format json` -- resolves `max_parallel: 4` (layer=project), fires `MRS-POLICY-007` naming the value and the upstream cause, `verdict: warn`, `status: ok`.

**Residual risks:** none identified. The `BASELINE_UNDECLARED_IMPORTS` entry is a repo-wide ratchet, not marshal-owned; `pyforge-steward`'s own dashboard-containment tests (`test_invariants.py`) already independently guard that `django`/`channels` stay confined to `dashboard/`, so this entry does not weaken any existing safety net -- it only teaches the cross-package scanner about a violation that was already accepted by design.

