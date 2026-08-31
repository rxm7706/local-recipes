---
title: 'marshal land renders a detectable merge subject'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: ['oversized']
difficulty: 'easy'
baseline_revision: 'b151a6b02cf17d0f645be76ec7415e013afd88d8'
final_revision: 'e503e2d070578ead7e944c2cb525296797ccbeac'
---

<intent-contract>

## Intent

**Problem:** `marshal land` (`cli/land.py::run_land`) merges via `forge.merge_pr` -> `gh pr merge`, letting GitHub auto-generate the merge commit subject -- a shape byte-identical to a human's plain PR merge. `core.promotion.marshal_native_merged_keys` (Story 5.9) already classifies `deploy land-story`'s templated subject and bmad-loop's own native form as Marshal-driven, but every `marshal land` landing is invisible to it, so downstream consumers (fleet-picture, `marshal status`, `dashboard-drift-check`, Story 5.9's `reconcile-completions`) mislabel most of them `not-loop-native`.

**Approach:** thread an optional `subject` parameter through `ForgePort.merge_pr` down to `gh pr merge --subject`, and have `run_land` render it via the SAME already-shipped `identity.render_merge_subject(key, template)` (AD-24) `deploy land-story` already uses -- never a separate pre-merge PR-title-edit call.

## Boundaries & Constraints

**Always:**
- For a full merge (the `forge.merge_pr` call site in `run_land` -- never the already-landed shortcut, which never calls `merge_pr`), render `subject = identity.render_merge_subject(wave_keys[0], template)` and pass it to `forge.merge_pr`'s new `subject` keyword. `wave_keys` is already `sorted(...)` at construction, so `wave_keys[0]` is the wave's deterministic primary (lowest) key -- see Design Notes for why a single key, not all wave keys.
- `ForgePort.merge_pr` gains `subject: ForgeRef | None = None` -- optional, defaults to `None`, wrapped in the EXISTING `ForgeRef` value type (never a bare `str`/`str | None`), mirroring `strategy`/`expected_head_sha`'s own convention on this same method and satisfying `tests/meta/test_ad34_egress_registry_completeness.py` (flags any bare-`str`-typed parameter, including `str | None`, on an egress-classified port).
- `adapters/forge_gh.py::GhForge.merge_pr` appends `["--subject", subject.value]` to the `gh pr merge` argv only when `subject is not None` -- `gh pr merge -t/--subject` applies uniformly across `--merge`/`--squash`/`--rebase`.
- `run_land`'s envelope (`data["subject"]`, both `--format json` and text) is set whenever a subject was rendered -- mirrors `cli/deploy.py::_render_text_land_story`'s own existing `data["subject"]` precedent exactly.
- `cli/land.py`'s ONLY new import is `identity` added to its existing `from ..core import deferred_work, policy, promotion` line (module-style, matching `cli/deploy.py`'s own `identity.render_merge_subject(...)` call convention) -- `render_merge_subject` itself is reused verbatim, never modified.

**Block If:** none -- the mechanism (existing `render_merge_subject`, existing `ForgeRef` convention, existing `gh pr merge --subject` flag) is fully determined by already-shipped primitives; nothing here requires human adjudication.

**Never:**
- Never modify `core/identity.py`, `core/promotion.py`, `core/policy.py`, or `cli/deploy.py`'s `run_land_story`/`marshal_native_merged_keys` -- this story's Surface is `cli/land.py`, `ports/forge.py`, `adapters/forge_gh.py` only (epics.md Story 5.10's own Surface line).
- Never add new error handling for a malformed `merge_subject_template` (missing/duplicate `{key}` placeholder): `identity.render_merge_subject`'s `ValueError` on a malformed template is pre-existing, uncaught behavior `deploy land-story` already exhibits (`cli/deploy.py`, no try/except around its own `render_merge_subject` call) -- this story mirrors that precedent exactly rather than giving `land` new handling `land-story` lacks.
- Never change any other step of `run_land` -- hygiene, required-check evaluation, acknowledgement gating, liveness/branch-retirement, resync, or deferred-work promotion. Only the value passed to `forge.merge_pr`'s new `subject` parameter, and its surfacing in `data`, are new.
- Never retroactively relabel any ledger row already marked `done`/`not-loop-native` before this ships, and never touch `bmad-quick-dev` or Story 5.9's own `reconcile-completions` code.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full merge, single-key wave | `wave_keys == [K]` | `forge.merge_pr(..., subject=ForgeRef(render_merge_subject(K, template)))`; `data["subject"]` set; `marshal_native_merged_keys` given that real subject classifies `K` as native | No error expected |
| Full merge, multi-key wave | `wave_keys == [K0, K1, ...]` (sorted) | Subject rendered from `K0` only (`wave_keys[0]`); `data["subject"]` set to that rendering | No error expected |
| Already-landed shortcut | wave fully in `already_landed_keys` | `forge.merge_pr` not called; no subject rendered; `data` carries no `"subject"` key -- byte-identical to before this story | No error expected |
| `gh pr merge` fails after a subject was rendered | `ForgeCommandError` from `forge.merge_pr` | Existing `MRS-LAND-007` ERROR finding, unchanged; `data["subject"]` still reflects the attempted (rejected) rendering | Reported, existing behavior |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/forge.py` -- EDIT. `ForgePort.merge_pr` gains `subject: ForgeRef | None = None`; docstring updated to describe the new parameter and its `gh pr merge --subject` mapping.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py` -- EDIT. `GhForge.merge_pr` accepts `subject: ForgeRef | None = None`; appends `--subject <value>` to argv when not `None`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` -- EDIT. `run_land`: add `identity` to the existing `from ..core import deferred_work, policy, promotion` import; immediately before the `_LAND_MERGE_PR_KIND` intent write, compute `subject = identity.render_merge_subject(wave_keys[0], template)` and set `data["subject"] = subject`; pass `subject=ForgeRef(subject)` into the `forge.merge_pr(...)` call. `_render_text_land`: add a `subject: {data['subject']!r}` line gated on `"subject" in data`, placed after the `merged:` line, mirroring `cli/deploy.py::_render_text_land_story`'s own precedent.
- `tests/unit/test_forge_gh.py` -- EDIT. Existing `merge_pr` argv tests keep asserting no `--subject` appears when omitted (default `None`); one new test passes `subject=ForgeRef(...)` and asserts `--subject <value>` appears in argv.
- `tests/unit/test_land.py` -- EDIT. `_FakeForge.merge_pr` signature gains `subject=None`, captured in `merge_calls`. New assertions: a single-key wave's full merge asserts the captured subject equals `identity.render_merge_subject` of that one key and `payload["data"]["subject"]` matches; a multi-key wave (two bmad-loop-native wave subjects, mirroring `test_promote_deferred_work_multiple_stories_in_one_wave`'s own fixture shape) asserts the captured subject uses `wave_keys[0]` only; the already-landed shortcut test asserts `merge_calls == []` and no `"subject"` key in `data`.
- `tests/unit/test_promotion.py` -- EDIT. One new assertion: `marshal_native_merged_keys((rendered_subject,), template, slug)` classifies the rendered key as native -- proves the AC's "classifies the key as native" claim as an executable assertion, not just a code read.

## Tasks & Acceptance

**Execution:**
- [x] `ports/forge.py` -- add optional `subject: ForgeRef | None = None` to `ForgePort.merge_pr`.
- [x] `adapters/forge_gh.py` -- thread `subject` to `gh pr merge --subject <value>` when provided.
- [x] `cli/land.py` -- render the subject from the wave's primary key via `identity.render_merge_subject`, pass it to `forge.merge_pr`, surface it in `data`/text output.
- [x] `tests/unit/test_forge_gh.py` -- cover omitted-subject (unchanged argv) and provided-subject (`--subject` present) cases.
- [x] `tests/unit/test_land.py` -- cover single-key and multi-key wave subject rendering, and confirm the already-landed shortcut is unaffected.
- [x] `tests/unit/test_promotion.py` -- assert `marshal_native_merged_keys` classifies a `land`-rendered subject as native.

**Acceptance Criteria:** *(epics.md Story 5.10, adapted for the wave's primary-key resolution -- see Design Notes)*
- Given a `marshal land` full merge (not the already-landed shortcut) of a wave whose primary (lowest-sorted) key is `K`, when it merges, then the merge commit's subject equals `identity.render_merge_subject(K, template)` (AD-24), applied via the optional `subject` parameter on `ForgePort.merge_pr` threaded to `gh pr merge -t` -- never a separate, pre-merge PR-title-edit call.
- And `core.promotion.marshal_native_merged_keys`, given that real subject, classifies `K` as native -- the same outcome it already produces for a `deploy land-story` merge.
- Given `marshal land`'s existing default `landing_merge_strategy`, its gates, and every other step of `run_land`, when this story ships, then none of them change -- only the merge commit's subject line (and its surfacing in `data`/text output) changes.
- Given the already-landed shortcut path, when it runs, then `forge.merge_pr` is still never called and no subject is rendered -- byte-identical to before this story.
- This story does not retroactively relabel any ledger row already marked `done`/`not-loop-native` before it ships, and does not change `deploy land-story`, `bmad-quick-dev`, or Story 5.9's own `reconcile-completions` code.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 0, medium 0, low 3)
- defer: 3 (high 0, medium 2, low 1)
- reject: 6 (high 0, medium 0, low 6)
- addressed_findings:
  - `[low]` `[patch]` **No end-to-end adapter test paired `subject` with `delete_branch=True`** -- the real call site in `cli/land.py` always passes both together. Found by Blind Hunter. Fixed: added `test_merge_pr_subject_and_delete_branch_both_present` to `tests/unit/test_forge_gh.py`.
  - `[low]` `[patch]` **The merge-failure error message omitted the `--subject` flag/value**, hiding a subject-caused failure's true cause. Found by Edge Case Hunter. Fixed: `adapters/forge_gh.py::GhForge.merge_pr`'s `ForgeCommandError` message now names `--subject <value>` when provided; added `test_merge_pr_failure_message_names_the_subject_when_provided`.
  - `[low]` `[patch]` **`ports/forge.py`'s new docstring claimed `gh pr merge --subject` "applies uniformly across `--merge`/`--squash`/`--rebase`"** -- verified via live `gh api graphql` introspection of `MergePullRequestInput` (`commitHeadline`: "Commit headline to use for the merge commit") plus `gh`'s own CLI source that a rebase merge creates no merge commit at all, so the flag is accepted but has nothing to apply to under `"rebase"` -- a silent no-op, not the claimed uniform effect. Found independently by both reviewers (Blind Hunter: claim unverified; Edge Case Hunter: unconditional pass-through with no method gate). Fixed: corrected the docstring wording (code, not `<intent-contract>`) to describe the rebase case accurately; added a matching Design Notes clarification.
- deferred (appended to `deferred-work.md` as NEW entries):
  - `[medium]` `DW-FU-5-10`: a malformed `merge_subject_template` (missing/duplicate `{key}` placeholder) crashes `run_land` with an uncaught `ValueError` -- `core/policy.py::_valid_merge_subject_template` never validates the placeholder shape. Found independently by both reviewers. Pre-existing gap (`deploy.py::run_land_story` already has the identical unguarded call site); this story adds a second, higher-traffic call site rather than introducing the underlying gap. Fixing it means touching `core/policy.py` or `deploy.py::run_land_story`, both outside this story's Surface -- deliberately mirrors `land-story`'s existing precedent per this story's own Boundaries.
  - `[low]` `DW-FU-5-10-2`: a multi-key wave under `landing_merge_strategy: squash` renders its subject from `wave_keys[0]` only, so the wave's non-primary keys stay exactly as undetectable as before this story (never worse, not fully fixed). Found by Blind Hunter. Not a regression -- explicitly out of this story's bounded (Effort: S) scope per its own Design Notes; `squash`/`rebase` are non-default `landing_merge_strategy` values and multi-key waves are rare per Story 5.9's own measured history.
  - `[medium]` `DW-FU-5-10-3`: under `landing_merge_strategy: rebase`, the rendered `subject` is a verified no-op (no merge commit exists to title), so `data["subject"]` reports a value never actually applied anywhere. Found independently by both reviewers, verified live via `gh api graphql` schema introspection during this pass. Actual detectability is unaffected (the wave's original commits stay independently detectable via the pre-existing bmad-loop-native pattern for `rebase`), so this is a misleading-envelope-value risk, not a functional defect; deciding whether `land` should skip passing `subject` for `rebase` is a small behavior change this pass declined to make unilaterally.
- rejected:
  - **`data["subject"]` remains populated in the envelope even when `forge.merge_pr` subsequently raises `ForgeCommandError`, describing a subject never actually applied.** Judged: matches `deploy.py::_render_text_land_story`'s own existing precedent exactly (the same juxtaposition already exists there, unchanged by this story); `data["merged"]` stays `False` and the accompanying `MRS-LAND-007` finding names the failure, so a reader is not misled without also seeing the failure reported alongside it.
  - **A squashed multi-key wave's already-landed shortcut can't recognize all wave keys on a re-run, since `main`'s history only shows the primary key.** Judged: not a new regression -- verified that before this story, a squash-strategy wave's already-landed shortcut already could not recognize ANY wave key via `main`'s squashed history (GitHub's own squash-commit subject conforms to none of the three recognized patterns), so this story's primary-key coverage is a strict improvement (fewer missing keys), never a new failure mode.
  - **The `ForgeRef` (not `Redacted`) classification for `subject` is "asserted, not demonstrated."** Judged: already explicitly justified in this spec's own Design Notes ("Why `ForgeRef`, not `Redacted`, for `subject`") with the same reasoning `strategy`/`expected_head_sha` already follow on this identical method -- a reassurance request, not a defect.
  - **The journal intent/outcome payloads for `_LAND_MERGE_PR_KIND` don't record the rendered `subject`.** Judged: matches `deploy.py::run_land_story`'s own existing journal payload shape verbatim, per this story's own explicit Boundaries ("mirrors `deploy land-story`'s own precedent exactly") -- a deliberate consistency choice, not an omission.
  - **The new multi-key test (`test_promote_deferred_work_multiple_stories_in_one_wave`) proves the call arguments but not a full git-history round-trip (a subsequent run re-parsing the real merge commit).** Judged: `tests/unit/test_promotion.py::test_marshal_native_merged_keys_recognizes_a_land_rendered_subject` already closes this gap at the correct unit boundary (render -> classify); a full git-history simulation would be a heavier integration-style test with no precedent anywhere else in this file, which uses fakes throughout.
  - **No validation that a rendered subject is single-line (an embedded newline in `merge_subject_template` could produce a malformed multi-line subject).** Judged: duplicate root cause of `DW-FU-5-10` (`core/policy.py::_valid_merge_subject_template`'s permissive validation) -- a project's own policy template is trusted, operator-authored input, not adversarial; already covered by that deferred entry.

## Design Notes

**Why the wave's primary (lowest-sorted) key, not all wave keys.** `identity.render_merge_subject`/`parse_merge_subject` are AD-24's fixed single-`{key}`-placeholder pair (`core/identity.py::_split_template`); this story's own Surface excludes `core/identity.py` and `core/promotion.py`, so neither gains a multi-key form here. `run_land`'s wave (`wave_keys: list[StoryKey]`) can carry more than one story -- already tested (`test_promote_deferred_work_multiple_stories_in_one_wave`) -- so one rendered subject cannot literally name every wave key. `wave_keys` is already `sorted(...)` at construction, so `wave_keys[0]` is a deterministic, well-defined "primary" key. Using it is a strict improvement over today (zero wave keys are ever native-classified via this commit's own subject currently) and costs nothing: Story 5.9's own measured history shows `marshal land` waves are overwhelmingly single-key, so this fully closes the gap for the dominant case; for a genuine multi-key wave under the default `"merge"` strategy, the non-primary keys' own already-existing bmad-loop-native commit subjects (the same ones `wave_keys` was itself discovered from) remain ancestors of `main` after the merge and are independently classified regardless of this commit's own subject. **Under `"squash"`, this coverage does NOT extend to the non-primary keys** -- `_resync_home_branch`'s own docstring already documents that squash/rebase never make the wave's individual commits ancestors of `origin/<base>` "BY CONSTRUCTION" -- so a squashed multi-key wave's non-primary keys stay exactly as undetectable as they were before this story (never worse, never fully fixed either); tracked as `DW-FU-5-10-2` rather than solved here, since a full fix needs either a multi-key subject form (out of this story's Surface) or a different detection mechanism entirely.

**Why `ForgeRef`, not `Redacted`, for `subject`.** `title`/`body` on this same port are `Redacted` because they carry free-form, potentially commit-derived text a caller must redact before the port boundary (`_batch_pr_redact`). This `subject` is fully determined by a policy-declared `template` plus a structured `StoryKey` -- no free user text -- the same shape `strategy`/`expected_head_sha` already have on this identical method, so it follows their existing `ForgeRef` convention rather than introducing a second payload-typing rule for one new parameter.

**`subject` is a no-op, not an error, under `landing_merge_strategy: rebase`.** Verified via `gh api graphql` introspection of `MergePullRequestInput`: `commitHeadline`'s own schema description reads "Commit headline to use for **the merge commit**"; a rebase merge creates no such commit at all (each original commit replays onto base with its own preserved subject), and `gh`'s own source sends `commitSubject` unconditionally regardless of merge method, so the API silently accepts and ignores it for `rebase` rather than rejecting it. This means the story's core detectability claim genuinely holds only for `"merge"`/`"squash"` (both produce one real new commit) -- for `"rebase"`, `data["subject"]` reports a value that was never applied anywhere, though the wave's original commits stay independently detectable via the pre-existing bmad-loop-native pattern regardless, so the actual detectability *outcome* is unaffected. Tracked as `DW-FU-5-10-3` (whether `land` should skip passing `subject` for `rebase` to avoid the misleading envelope value) rather than resolved here -- `landing_merge_strategy: rebase` is a non-default value with no confirmed live use in this fleet today.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** Threaded an optional `subject: ForgeRef | None = None` through `ForgePort.merge_pr` (`ports/forge.py`) and its sole `GhForge` implementation (`adapters/forge_gh.py`) down to `gh pr merge --subject`. `run_land` (`cli/land.py`) renders the subject via the already-shipped `identity.render_merge_subject(wave_keys[0], template)` (AD-24) -- the wave's primary, lowest-sorted key -- immediately before the merge intent-write, surfaces it in `data["subject"]` (JSON and text output), and passes it to `forge.merge_pr`. The already-landed shortcut path is untouched (never calls `merge_pr`, never renders a subject). No other step of `run_land` changed.

**Files changed** (2 commits, `4880dddef1` feature + `e503e2d070` spec-surface reconcile):
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/forge.py` -- `ForgePort.merge_pr` gains `subject`; docstring documents the `gh pr merge --subject` mapping including the verified rebase no-op behavior (added during review).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py` -- `GhForge.merge_pr` threads `subject` to argv; the raised `ForgeCommandError` message now names the subject when provided (added during review).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` -- `run_land` renders and passes the subject; `_render_text_land` gained a matching text-output line.
- `tests/unit/test_forge_gh.py`, `tests/unit/test_land.py`, `tests/unit/test_promotion.py` -- full I/O-matrix coverage plus two review-driven additions (subject+delete_branch combo; failure-message content).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` + `scripts/.spec-surface-baseline.json` -- surface-reconcile bookkeeping (S-13.7), scoped to this one spec.

**Review findings breakdown (single pass, Blind Hunter + Edge Case Hunter, parallel, no prior context):** 11 unique findings after dedup. patch 3 (all low, all applied: a missing `subject`+`delete_branch=True` adapter test, a failure message that omitted the subject value, and a docstring claim about `--rebase` corrected after live verification) / defer 3 (`DW-FU-5-10` medium -- pre-existing malformed-template crash risk, root cause outside this story's Surface; `DW-FU-5-10-2` low -- a squashed multi-key wave's non-primary keys stay undetectable, never a regression; `DW-FU-5-10-3` medium -- `subject` verified as a harmless no-op under `landing_merge_strategy: rebase`, confirmed live via `gh api graphql` schema introspection) / reject 6 (all matched an existing precedent, were already justified in the spec's own Design Notes, or were not actually new regressions once verified against pre-story behavior). intent_gap 0, bad_spec 0 -- no loopback triggered. `followup_review_recommended: false` -- every applied patch was low-severity, localized, with no behavior/API/security/data-shape impact (a new test, an error-message string, and a docstring wording correction).

**Verification performed:** `pyforge-marshal-test` 3597 passed (9 slow deselected, +2 over this story's own pre-review 3595); `lint-imports --config .../pyforge-marshal/pyproject.toml --no-cache` 3 contracts kept, 0 broken; `python scripts/spec_surface_reconcile.py` -- OK, no drift. All commands re-run independently by the orchestrating session after each round of changes, not just trusted from the implementation subagent's own report.

**Residual risks:** the three deferred findings (`DW-FU-5-10`/`-2`/`-3`) are all real but bounded: the malformed-template crash requires an operator-authored policy misconfiguration (pre-existing, not introduced here); the squash-strategy multi-key gap is a non-regression, non-default-strategy edge case; the rebase no-op is harmless (actual detectability is unaffected, since rebase-landed commits stay independently detectable via the pre-existing bmad-loop-native pattern). PRD Q-16 and Story 5.9's own `reconcile-completions` code are unchanged, per this story's own Never bullet.
