---
title: '`marshal seed update` — two-phase'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      `_wholesale_regenerate_actions` never cross-checks `state.opted_out`/`state.skips`
      before regenerating, so it could silently override a previously opted-out hybrid
      region or a previously skipped whole-file artifact.
    evidence: |-
      Blind Hunter review finding. `build_plan` itself already respects `opted_out` for
      its own actions (`_pendency`/`_is_fully_opted_out`); the new wholesale-regenerate
      pass has no equivalent check. Not demonstrated as an active bug, and how `update`
      should treat a prior opt-out/skip on a subsequent update is a genuine, undecided
      product question the epics AC does not address — deserves dedicated design
      attention rather than an improvised same-pass fix.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py:_wholesale_regenerate_actions
    severity: medium
  - summary: >-
      The `--include-seeded` "offered now, applicable later" story is untested across
      separate `update` invocations.
    evidence: |-
      Blind Hunter review finding. Once a migration's `to_version` lands in
      `state.migrations_applied[]`, a later `chain()` call may not re-walk that
      migration, so whether the `copied-seeded` offer still resurfaces on a later
      `--include-seeded` run is unverified. No test in this diff exercises two
      sequential `run_update` calls against the same evolving state.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py:run_update
    severity: low
  - summary: >-
      `--force` combined with a hand-edited hybrid-managed-region (as opposed to a
      hand-edited whole-file artifact) is untested.
    evidence: |-
      Blind Hunter review finding. `test_force_bypasses_the_hand_edited_managed_content_precondition`
      only covers the whole-file case; whether `--force` correctly bypasses rung 6 and
      correctly substitutes over a hand-edited region span is unverified.
    location: >-
      src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_update.py
    severity: low
  - summary: >-
      The `projects-table` repo-computed region-body dispatch (Story 11.2) is never
      exercised through `update`'s own commit path — only through `adopt`'s.
    evidence: |-
      Verification Gap Reviewer observation. Every hybrid-region test in the new test
      files uses the static "tiers" fragment; `_region_body_for`'s
      `projects-index`/`projects-table` branch has no direct test via `update`.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py:_region_body_for
    severity: low
baseline_revision: '9596b24c7f9a84f5e42a18763dc4934bbc2f032c'
---

<intent-contract>

## Intent

**Problem:** `cli/seed.py::run_update` is still Story 7.1's stub ("not yet implemented"). A repo
that adopted Marshal's seed model has no way to take a later model version — `seed/migrate/
registry.py` (Story 11.3) can compute and compose migrations into a `Plan`, but nothing calls it,
and nothing regenerates a drifted `copied-managed`/`generated-derived`/`hybrid-managed-region`
artifact whose PACKAGED content has simply moved on since the repo's last update (a case
`detect.inventory.classify` cannot see at all, since it never compares against template content —
only `hybrid-managed-region` can ever reach `ArtifactState.PRESENT_DIVERGENT`; whole-file classes
are always `PRESENT_CONFORMANT` once present, confirmed in `detect/inventory.py::_classify_entry`
and `plan/build.py::_rationale`'s own comment).

**Approach:** Add `seed/verbs/update.py`: a two-phase verb (`resolve -> detect -> plan -> confirm
-> apply -> state-write`, mirroring `verbs/adopt.py`'s already-shipped shape) whose plan merges
THREE action sources into one `Plan` — migration-composed actions (`migrate.chain`/`compose`,
Story 11.3, unchanged), `build_plan`'s ordinary ABSENT-entry actions (a manifest addition not yet
materialized), and a NEW unconditional "wholesale regenerate" pass over every `state.managed[]`
record whose class is `copied-managed`/`generated-derived`/`hybrid-managed-region` (FR-98/FR-99 —
this is genuinely new logic; nothing today expresses "regenerate this file even though `classify()`
calls it conformant"). Wire `cli/seed.py::run_update` from stub to real, mirroring `run_adopt`'s
CLI-plumbing shape, and fix `DW-FU-11-3` (spec-11-3's own deferred finding): a migration-offered
`copied-seeded` skip must render as an offer, not a false "matched --skip" claim.

## Boundaries & Constraints

**Always:**
- The default invocation (`marshal seed update`, no flags) computes and writes `.marshal/
  plan.json` and changes nothing else (FR-94) — identical dry-run-by-default convention to
  `adopt`, but this verb's apply flag is named `--run`, matching the epics AC's literal wording
  (never `--apply`).
- The merged plan's action set = migration-composed actions (`migrate.compose`, `include_seeded=
  args.include_seeded`) + `build_plan`'s ABSENT-only actions (reuse unmodified, never re-derive
  its classification rule) + the new wholesale-regenerate pass over `state.managed[]` (skip any
  `copied-seeded` or `referenced` record — those two classes are never regenerated by `update`).
  Merge via the SAME collision-then-sort pattern `migrate.compose`'s own `_claim` and `verbs/
  adopt.py::_augment_plan_with_first_claims` already establish: raise `InternalError` naming any
  `artifact_id` produced by more than one source, else sort by `artifact_id`. One shared
  `RepoFingerprint`; every wholesale-regenerate action gets a matching `artifact_hashes` entry
  (current on-disk content), mirroring `_augment_plan_with_first_claims`'s identical requirement.
- Every wholesale-regenerate `Action` uses `current_state=target_state=ArtifactState.
  PRESENT_CONFORMANT` (the `_augment_plan_with_first_claims` shape) so `_default_commit`-style
  materialization treats it like any other action; a hybrid entry's `chosen_anchor` names every
  declared region paired with its manifest `anchor` (`_default_commit`'s hybrid branch only reads
  the region NAME positionally — the anchor half is unused there, confirmed in `verbs/adopt.py`'s
  own commit closure — so this needs no re-derivation of `build_plan`'s private pendency logic).
- `check_preconditions` (rung 6, `verbs/preconditions.py`) gates the run BEFORE any write, exactly
  as `adopt` already does — a hand-edited managed artifact refuses the run unless `--force`; the
  hash-guard check IS the "detect's hash guards pass" FR-98 requires.
- `--force` maps to `engine.copier.materialize(verb=MaterializeVerb.RECOPY, confirm=True)`
  (already implemented, `engine/copier.py:361-369`) and only takes effect together with `--run`
  (a `--force`-without-`--run` invocation still only plans — two-phase semantics are never
  bypassed by `--force` alone). Requires the SAME confirm seam `adopt` established (`confirm:
  Callable[[], bool]`, real `input()`-based prompt supplied by `cli/seed.py`, skippable with
  `--yes`) — consulted once, specifically for the force-recopy confirmation, never silently true.
- Applied migrations are recorded in `state.migrations_applied[]` (already-shipped field) only
  after a successful, non-empty apply — mirrors `adopt`'s own "state write gated on non-empty
  plan.actions" rule.
- `--include-seeded` is the flag name (matches `migrate.compose`'s own parameter, FR-97) — a
  migration's `copied-seeded` offer is skipped by default and only applied when this flag is
  passed; it never affects the wholesale-regenerate pass (which already excludes `copied-seeded`
  unconditionally).
- Fix `DW-FU-11-3`: `update`'s own plan renderer (new function in `cli/seed.py`, `_render_update_
  plan_text` or equivalent — never reuse `_render_plan_text` unmodified, that one is `adopt`-
  specific per its own docstring) must render a `SkippedArtifact` whose `pattern` equals
  `migrate.registry._SEEDED_OFFER_PATTERN` as an explicit migration offer (e.g. "offered by a
  migration; not applied without --include-seeded"), never as `matched --skip {pattern!r}`.
- Match house style: `from __future__ import annotations`, dense rationale docstrings, frozen
  dataclasses, exact-symbol imports, real `tmp_path` git-repo fixtures (no shared `conftest.py`).

**Block If:** none identified — every open question (plan-merge mechanism, flag names, the
DW-FU-11-3 fix target) is resolved above by direct evidence from shipped code, the epics AC, or
spec-11-3's own explicit deferral; no decision here requires a human call.

**Never:**
- Never modify `plan/build.py`, `detect/inventory.py`, or `seed/migrate/registry.py` — `build_plan`
  and `chain`/`compose` are reused exactly as Story 9.6/11.3 shipped them.
- Never route the regular (non-`--force`) regenerate path through Copier's own `run_update` —
  this package's established design (`engine/copier.py`'s module docstring) is that ordinary
  regeneration goes through the deterministic plan/apply/materialize(COPY) path, with hand-edit
  protection coming entirely from `check_preconditions` rung 6, not Copier's fuzzy diff-merge.
  `run_update`/`MaterializeVerb.UPDATE` stays unused by this story (only `COPY` for the regular
  path, `RECOPY` for `--force`).
- Never let the wholesale-regenerate pass touch a `copied-seeded` or `referenced` record.
- Never call `migrate.compose`/`build_plan` with a mismatched `Inventory`/`Manifest` pair.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No flags, repo current | `state.model_version == manifest.model_version`, no drift | Plan is empty (or contains only genuinely-absent-entry actions); `.marshal/plan.json` written; nothing else changes | No error expected |
| No flags, repo behind | `state.model_version < manifest.model_version`, a registered migration exists | Plan names the migration's actions plus every wholesale-regenerate action; nothing applied | No error expected |
| `--run`, plan non-empty | Prior plan written, `--yes` given | Plan applied via `run_apply`; `state.model_version`/`migrations_applied[]`/managed hashes updated | No error expected |
| `--run` without `--yes`, declined | Confirmation prompt returns `False` | Nothing applied; result reports declined | No error expected |
| `--force --run` | A hand-edited managed artifact present | `check_preconditions` would normally refuse; `--force` bypasses rung 6 and materializes via `MaterializeVerb.RECOPY` with `confirm=True` | Confirmation required first |
| `--force` without `--run` | any | Plan is written (dry-run only); force has no apply-time effect yet | No error expected |
| Migration targets `copied-seeded`, no flag | A registered migration's `Plan` includes a `copied-seeded` action | Routed to `Plan.skipped` with `_SEEDED_OFFER_PATTERN`; rendered as an explicit migration offer (DW-FU-11-3 fix), never `matched --skip` | No error expected |
| Migration targets `copied-seeded`, `--include-seeded` | Same | Action applied like any other | No error expected |
| Migration chain gap | No migration bridges `state.model_version` to bundled | `chain()` raises `InternalError` naming the gap; propagates unwrapped through `run_update`'s existing widened `except SeedError` | Exit 10, named |
| Never-write target | A wholesale-regenerate or migration action names a never-write path | Refused at plan time, never only at apply | Migration action: Exit 4 (`NeverWriteViolation` via `compose()`'s own `fs.check_never_write` guard). Wholesale-regenerate/absent-entry action: Exit 3 (`PreconditionFailure` via `check_preconditions` rung 4) — corrected from an earlier draft that stated Exit 4 uniformly; verified against the actual passing test |
| SC-01 end-to-end | Fixture repo at v1, a registered v1->v2 migration, `check` reports `model-behind` | `update` plans, `--run` applies, Dreams/PRDs/epics under the never-write set are byte-identical before/after, `check` reports green afterward | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py` -- NEW: `run_update(repo_root, manifest, *, run: bool = False, force: bool = False, include_seeded: bool = False, yes: bool = False, confirm: Callable[[], bool], template_path=None, commit=None) -> UpdateResult` (a frozen result dataclass mirroring `AdoptResult`: `plan`, `applied`, `declined`). Composes `migrate.chain`/`compose` (Story 11.3, `seed/migrate/registry.py:210-425`), `detect.inventory.classify`, `plan.build.build_plan` (ABSENT-only), a new `_wholesale_regenerate_actions(state, manifest, inventory)` helper, `verbs.preconditions.check_preconditions`, `apply.run.run_apply`, and `state.write_state`. Reuse `verbs/adopt.py`'s `_default_commit`-style materialize/write dispatch (whole-file via `engine.materialize(MaterializeVerb.COPY)`, hybrid regions via `_region_body_from_template`/`insert_region`) — duplicate the small dispatcher rather than importing `adopt.py`'s private one, matching this package's established "small deliberate duplication beats reaching into a sibling's private helper" convention (`verbs/adopt.py`'s own module docstring, `migrate/registry.py`'s own module docstring).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` -- CHANGED: replace the `run_update` stub (currently lines 451-453) with real CLI plumbing mirroring `run_adopt`'s try/except shape (widened `except SeedError`/`except Exception` backstop); add `--repo-root`, `--run`, `--force`, `--include-seeded`, `--yes` to `update_parser` (currently zero arguments, `add_seed_subparser` lines 601-606); add a new plan renderer for `update`'s plan that fixes `DW-FU-11-3` (a migration-offered `Plan.skipped` entry, identified by `pattern == migrate.registry._SEEDED_OFFER_PATTERN`, renders as an explicit offer, never `matched --skip {pattern!r}` — `_render_plan_text`, lines 262-293, stays untouched, `adopt`-only).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/migrate/registry.py` -- READ-ONLY reuse: `chain()`, `compose()`, `_SEEDED_OFFER_PATTERN` (import for the DW-FU-11-3 render check), `RepoView = Inventory` type alias.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/plan/types.py` -- READ-ONLY: `Action`, `Plan`, `SkippedArtifact`, `RepoFingerprint` shapes reused unmodified.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_update.py` -- NEW: covers the I/O matrix above, including a write-blocking dry-run fixture, the three-source merge (a synthetic registered migration + a synthetic ABSENT entry + a synthetic drifted managed entry, asserting all three appear correctly merged and sorted), the collision-refusal case (two sources naming the same `artifact_id`), and the SC-01 end-to-end proof (mirrors `test_seed_migrate_registry.py`'s own SC-07 fixture pattern).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_update.py` -- NEW: CLI-plumbing tests mirroring `test_seed_cli_seed_adopt.py`'s shape, plus a direct render test proving the DW-FU-11-3 fix (a migration-offer `SkippedArtifact` never renders `matched --skip`).

## Tasks & Acceptance

**Execution:**
- `seed/verbs/update.py` -- implement `run_update` and `_wholesale_regenerate_actions` per the Boundaries above
- `cli/seed.py` -- wire `run_update`, add the four new flags to `update_parser`, add the DW-FU-11-3-fixed plan renderer
- `tests/unit/test_seed_verbs_update.py` -- cover the I/O matrix, the three-source merge, collision refusal, SC-01 end-to-end
- `tests/unit/test_seed_cli_seed_update.py` -- CLI plumbing + DW-FU-11-3 render proof

**Acceptance Criteria:**
- Given a repo behind the bundled model version, when `marshal seed update` runs with no flags, then a plan is written naming every migration and every file action, and nothing else changes (FR-94)
- Given a written plan, when `--run` is passed, then the plan applies through the existing `apply/run.py::run_apply` path
- Given `copied-managed`/`generated-derived` entries already conformant per `classify()`, when update plans, then they still receive a wholesale-regenerate action (FR-98) once `check_preconditions` (hash guards) passes
- Given a `hybrid-managed-region` entry, when update plans and applies, then only its marked span is replaced, never the whole file (FR-99)
- Given a migration's action names a never-write path, when update plans, then it is a hard error at plan time (FR-100)
- Given `--force --run` and a hand-edited managed artifact, when update runs, then it materializes via Copier `run_recopy` semantics after explicit confirmation (FR-101)
- Given a migration offering a `copied-seeded` action, when update plans without `--include-seeded`, then it is skipped and rendered as an explicit migration offer, never a false `matched --skip` claim (DW-FU-11-3)
- Given the PRD J3 journey (a fixture repo, a registered migration), when `check` -> `update` -> `--run` -> `check` runs end to end, then Dreams/PRDs/epics under the never-write set are byte-identical before and after, and the final `check` is green (SC-01)
- Given the existing `pyforge-marshal` test suite and meta-tests, when run after this change, then they all still pass with no new violation

## Design Notes

**Why a NEW wholesale-regenerate pass, not a `build_plan` change.** `build_plan`'s own contract
(Story 9.6, unmodified by this or the prior story) is that `PRESENT_CONFORMANT` never produces an
`Action`, for any class — that invariant is what makes `adopt`'s FR-84 idempotence (a second adopt
on an unchanged repo produces an empty plan) hold for free. `update` genuinely needs the opposite
behavior for already-adopted, already-conformant managed content (FR-98/FR-99 say "wholesale"/
"recomputes", unconditionally) — widening `build_plan` itself would silently change `adopt`'s and
`check`'s behavior too. A dedicated pass, scoped to `update` alone and driven by `state.managed[]`
(the record of what THIS repo has actually adopted), keeps the invariant intact for every other
caller while giving `update` the unconditional refresh FR-98/FR-99 require.

**Why the three sources can never legitimately collide.** `build_plan`'s ABSENT-only actions cover
entries with NO `state.managed[]` record; the wholesale pass covers entries that DO have one;
a well-formed migration should not re-target an artifact already covered by either (a migration
exists to absorb a BREAKING change — a renamed artifact, a reclassified entry — not to duplicate
ordinary regeneration). A collision is therefore a genuine authoring bug in a future migration,
and the `InternalError` this story adds (mirroring `migrate.compose`'s own `_claim` pattern) is
what surfaces it loudly rather than letting `run_apply` silently pick one Action's write over
another's.

## Review Triage Log

### 2026-08-22 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 1, medium 3, low 5)
- defer: 4 (medium 1, low 3)
- reject: 6 (low 6)
- addressed_findings:
  - `[high]` `[patch]` **Blocking bug** (Verification Gap Reviewer, confirmed by reading `verbs/preconditions.py::_region_divergences` directly): a hybrid-managed-region entry with more than one declared region (the packaged manifest's own `AGENTS.md`/`CLAUDE.md`, both `applies_to: both`) makes `marshal seed update` raise `PreconditionFailure` on EVERY invocation, including a plain dry-run, because `ManagedArtifact` can record only ONE region per entry (a pre-existing `state/store.py` schema limit shared with `adopt.py`) while rung 6 flags every OTHER declared-but-unrecorded region as `"present in the file but was never recorded in state."` Fixed by having `update`'s own managed-record construction represent every declared region on a hybrid entry — the genuinely-tracked one with its recorded sha, every other declared region with its CURRENT on-disk hash computed fresh — so rung 6's real hand-edit protection for the tracked region is unchanged while the false "never recorded" flag for regions the schema was never able to track stops firing. Scoped entirely inside `update.py`; `preconditions.py`/`adopt.py` untouched. Added a dedicated multi-region regression test.
  - `[medium]` `[patch]` `_wholesale_regenerate_actions`'s `region.anchor[0]` indexing (Edge Case Hunter) could raise `IndexError` on an empty anchor tuple — guarded.
  - `[medium]` `[patch]` Bare `entries_by_id[action.artifact_id]` dict indexing in `commit()` and its post-apply callers (Edge Case Hunter + Blind Hunter, same finding from two reviewers) replaced with guarded `.get()` + `InternalError` with remedy, matching this module's own established convention for the sibling `region is None` check.
  - `[medium]` `[reject, revised from an initial patch classification]` `cli/seed.py::run_update`'s call to `_render_update_plan_text(result.plan)` sits outside the function's own try/except (Edge Case Hunter). Initially triaged as patch and sent to the implementer, who pushed back with evidence, verified directly: `run_check`/`run_adopt`/`run_init` — every existing verb in this same file — ALSO print their post-verb rendering outside their own try/except; it is this file's established, unanimous four-verb pattern, not a `run_update`-specific deviation. Making only `run_update` deviate from it would be a worse, inconsistent outcome for a near-impossible failure mode (the renderer is a pure string-builder with no I/O). Left as-is; not applied.
  - `[medium]` `[patch]` The `GENERATED_DERIVED`/`ADAPTER_COMPOSITION` commit branch (`cursor-rules`/`gemini-md`/`copilot-instructions` wholesale regen) had zero test coverage — flagged independently by both Blind Hunter and Verification Gap Reviewer. Added a direct test.
  - `[low]` `[patch]` `commit()` not materializing a target before `_managed_artifact_after_apply` reads it back (Edge Case Hunter) could raise an unguarded `FileNotFoundError`/`UnicodeDecodeError` — now a clear `InternalError`.
  - `[low]` `[patch]` `_build_state_after_apply`'s `ModelVersion.parse` sort over `state.migrations_applied` (Edge Case Hunter) had no guard against a pre-existing unparseable entry — guarded.
  - `[low]` `[patch]` The wholesale-regenerate rationale string cited "FR-98/FR-99" even for non-hybrid whole-file classes where FR-99 (region-span replacement) does not apply (Blind Hunter) — split the message by class.
  - `[low]` `[patch]` `run_update`'s own docstring listed its raise sources but omitted `_merge_plan_sources`'s own `InternalError` (Blind Hunter) — docstring corrected.
  - `[low]` `[patch]` Spec I/O matrix's "Never-write target" row stated a uniform Exit 4; the Intent Alignment Auditor found (and the diff's own passing test confirms) the wholesale-regenerate/absent-entry path actually raises `PreconditionFailure` (Exit 3) via `check_preconditions` rung 4, not `NeverWriteViolation` (Exit 4) — the CODE was already correct and needed no change; only this spec's own I/O matrix text was wrong, corrected above without a bad_spec revert (no code was at fault).
  - `[medium]` `[defer]` `_wholesale_regenerate_actions` doesn't consult `state.opted_out`/`state.skips` — real but undecided product question (Blind Hunter), not demonstrated as an active bug; deferred (frontmatter `deferred[]`).
  - `[low]` `[defer]` `--include-seeded` offer-resurfacing across separate `update` runs is untested (Blind Hunter) — deferred.
  - `[low]` `[defer]` `--force` + hand-edited hybrid region (as opposed to whole-file) is untested (Blind Hunter) — deferred.
  - `[low]` `[defer]` `projects-table` dynamic region dispatch never exercised through `update`'s own commit path (Verification Gap Reviewer) — deferred.
  - `[low]` `[reject]` `_render_update_plan_text` reaching into `migrate_registry._SEEDED_OFFER_PATTERN` (a private symbol) across a module boundary (Blind Hunter) — this is exactly what this spec's own Code Map directed, to guarantee the CLI recognizes the identical sentinel value the registry module produces rather than duplicating the literal string and risking drift.
  - `[low]` `[reject]` No `--skip` flag for `update` (Blind Hunter) — out of scope; neither the epics AC nor this spec's own Boundaries calls for one.
  - `[low]` `[reject]` No `--json` output mode for `update` (Blind Hunter) — out of scope; matches `adopt`'s own established precedent that a written `plan.json` already is the machine-readable artifact.
  - `[low]` `[reject]` Duplicated helper functions from `adopt.py` have no parity-drift test (Blind Hunter) — matches this package's own established, explicitly-blessed "small deliberate duplication" convention; adding a parity test would be a package-wide convention change, not this story's scope.
  - `[low]` `[reject]` Hypothetical future risk if some future `Plan.actions` consumer treats `current_state == target_state` as "no-op, skip me" (Blind Hunter) — speculative; nothing in the current codebase does this.

**Verification after this pass:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci pyforge-deps-test` re-run green; new regression tests added for the multi-region fix and the `ADAPTER_COMPOSITION` branch.

## Auto Run Result

**Summary:** Wired `marshal seed update` from Story 7.1's stub to a real two-phase verb (`resolve
-> detect -> plan -> confirm -> apply -> state-write`). Added `seed/verbs/update.py`: a plan
merging three action sources into one `Plan` — `migrate.chain`/`compose` (Story 11.3, unmodified),
`build_plan`'s ABSENT-only actions, and a new unconditional wholesale-regenerate pass over
`state.managed[]` for `copied-managed`/`generated-derived`/`hybrid-managed-region` records
(FR-98/FR-99). Wired `cli/seed.py::run_update` with `--repo-root`/`--run`/`--force`/
`--include-seeded`/`--yes`, and added `_render_update_plan_text` fixing `DW-FU-11-3` (a
migration-offered `copied-seeded` skip now renders as an explicit offer instead of a false
`matched --skip` claim). One review pass found and fixed a HIGH-severity blocking bug (a
multi-region hybrid entry, e.g. the packaged manifest's own `AGENTS.md`/`CLAUDE.md`, made every
`update` invocation — including a plain dry-run — raise `PreconditionFailure`, because
`ManagedArtifact`'s pre-existing one-region-per-entry schema limit left every other declared
region looking "never recorded" to rung 6) plus 8 smaller robustness/coverage patches; one
proposed patch (moving a render call inside a try/except) was reverted after the implementer
demonstrated it would make `run_update` the one inconsistent verb among four that share the
identical existing pattern.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py` -- new module (995 lines pre-patch; grew with the review-pass fixes).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py` -- `run_update` wired from stub to real, `update_parser` gained 5 flags, new `_render_update_plan_text` renderer.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_update.py` -- new, 24 tests (verb-level: I/O matrix, three-source merge, collision refusal, SC-01 end-to-end, the multi-region regression, the adapter-composition commit-branch test).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_update.py` -- new, 18 tests (CLI plumbing, exit codes, the DW-FU-11-3 render proof).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_scaffold.py` -- `update` removed from the stub-verb parametrize; added its own no-longer-a-stub smoke test, mirroring the existing `adopt`/`check`/`init` convention.

**Review findings breakdown:** 9 patched (1 high, 3 medium, 5 low), 4 deferred (1 medium, 3 low,
recorded in frontmatter `deferred[]`), 6 rejected (all low — 5 out-of-scope/working-as-designed,
plus 1 reclassified from an initial patch triage after the implementer's evidence-based pushback
showed it would introduce a codebase inconsistency rather than fix a real gap).

**Follow-up review recommendation:** `true` — the patched-findings set included one `high`
severity item (the multi-region blocking bug), which alone crosses the threshold regardless of
the medium/low tally (3 medium + 5 low = `3*3 + 1*5 = 14`, also over threshold independently).

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 5264 passed, 9 deselected (independently re-run after the review-pass patches, not just trusted from the implementer's report).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 84 passed (independently re-run).
- `ruff check` on every touched file -- clean (independently re-run).
- The two most critical new tests (`test_multi_region_hybrid_entry_does_not_refuse_a_plain_dry_run`, `test_default_commit_wholesale_regenerates_an_adapter_composition_entry`) run in isolation and confirmed passing; the fix's code (`_region_shas_for_record`) read in full and confirmed to preserve real hand-edit protection for the one genuinely-tracked region per hybrid entry while only trusting current on-disk content for regions the state schema was never able to track — an explicitly documented, accepted bound, not a new weakness.
- Every I/O & Edge-Case Matrix row has a passing named test (Matrix Test Audit satisfied).

**Residual risks:** The four deferred findings (frontmatter `deferred[]`) are real but narrower:
whether `update`'s wholesale-regenerate pass should respect `state.opted_out`/`state.skips` is an
undecided product question outside this story's epics AC; `--include-seeded` offer-resurfacing
across separate `update` invocations, `--force` against a hand-edited hybrid region specifically,
and the `projects-table` dynamic dispatch through `update`'s own commit path are all real test-
coverage gaps on narrower paths, not demonstrated active bugs. SC-01's "Dreams/PRDs/epics
byte-identical" clause is exercised indirectly (never-write enforcement is tested independently;
the SC-01 fixture itself has no never-write-protected files in its synthetic repo).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green, including new `test_seed_verbs_update.py` and `test_seed_cli_seed_update.py`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green, no new disallowed import
</content>
