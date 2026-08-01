<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Story 1.10: Render the harness policy from the canonical EffectivePolicy'
type: 'feature'
created: '2026-07-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '99ba90ea4e1546f43ceef512253ed4d8eaa3be96'
final_revision: 'c45e135bbd7b9b11e963e90e7af166aae14c89c0'
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `.bmad-loop/policy.toml` is the ONLY path the harness (`bmad-loop 0.9.0`, hard-coded `POLICY_FILE`, no policy-path flag) reads for orchestration config, yet it is git-tracked and hand-edited per loop home -- the live F-1 cross-project bleed (a `loop-pyforge-herald` edit riding `git push origin HEAD:main` onto every project). Story 1.3's `EffectivePolicy` composes Marshal's own 9-key policy but has no path to the harness at all.

**Approach:** Add `render_policy_toml()`/`write_policy_toml()` to `adapters/harness_bmadloop.py` (the one module AD-3 permits to touch harness concerns): render the harness's full ~14-section `policy.toml` from a project-agnostic vendored template, substituting only the keys `EffectivePolicy` actually owns, always writing the file whole and atomically. Then gitignore the file and untrack it (last step, after rendering is proven).

## Boundaries & Constraints

**Always:**
- `render_policy_toml(effective: EffectivePolicy, *, difficulty: str | None = None) -> str` is a PURE string builder (no I/O) -- parses a module-level `_POLICY_TEMPLATE` string via `tomlkit` (already a dependency; no new package needed), overrides only the mapped keys below, and returns `tomlkit.dumps(...)`. Identical `(effective, difficulty)` -> byte-identical output (AD-12/AD-35 "derived artifact" discipline).
- Exactly 6 of Marshal's 9 fields have a real harness destination, mapped 1:1:
  - `gate_mode` (seed) -> `[gates].mode` (same 3-value enum both sides: `none`/`per-epic`/`per-story-spec-approval`)
  - `max_dev_attempts`, `max_review_cycles`, `max_followup_reviews` (seed) -> `[limits].max_dev_attempts` / `.max_review_cycles` / `.max_followup_reviews` (confirmed real keys in the installed `bmad_loop` 0.9.0 `LimitsPolicy`)
  - `verify_commands` (static) -> `[verify].commands`
  - `worktree_seed_paths` (static) -> `[scm].worktree_seed`
- FR-51 tier-batching: when `difficulty` is given and is a key of `effective.model_tier_map.value`, for each of `dev`/`review`/`triage` present in `model_tier_map[difficulty]`, set `[adapter.<stage>].model` to that value. A stage absent from that difficulty's mapping keeps the template's baseline model (no override table written for it). `difficulty=None`, or a `difficulty` absent from `model_tier_map`, renders every stage at the template baseline -- never an error (resolving which difficulty applies to a real story/batch is Epic 3/4's surface, not this one's).
- The vendored `_POLICY_TEMPLATE` covers every OTHER harness key (the ~20 keys `EffectivePolicy` does not model) at bmad-loop's own stock defaults, with these named, evidence-based exceptions hardcoded as this story's "tracked canonical source" for repo-wide policy (AD-35's closing point 4 -- changing one of these means editing this constant, never the rendered file): `review.trigger = "always"` (AD-35's own named example -- the 2026-07-25/26 standing independent-review decision), `scm.isolation = "worktree"` and `scm.merge_strategy = "squash"` (the per-story-branch workflow every current loop home depends on operationally -- silently reverting to bmad-loop's stock `none`/`merge` would break the multi-home worktree model this factory runs on), `scm.rollback_on_failure = true`, `limits.session_timeout_min = 180`, baseline `[adapter].model = "sonnet"` / `[adapter.review].model = "fable"` (today's uniform cross-home convention, confirmed by inspecting all 9 live loop homes' `.bmad-loop/policy.toml`).
- `write_policy_toml(effective, loop_home: Path, *, difficulty: str | None = None) -> Path` is the I/O boundary: calls `render_policy_toml`, then writes `<loop_home>/.bmad-loop/policy.toml` WHOLE via write-to-temp-then-`os.replace` (same atomic pattern as `cli/config.py::materialize`) -- it never reads an existing file at that path first; every call fully replaces prior content, matching "written whole -- never patched, never merged" (AD-12).
- `.gitignore` gains a `.bmad-loop/policy.toml` entry near the existing `.bmad-loop/` rules.
- The LAST implementation step (after `render_policy_toml`/`write_policy_toml` are implemented and their tests pass) is `git rm --cached .bmad-loop/policy.toml` at the repo root -- untracking must not precede rendering (epics.md's own hard sequencing note), and `git rm --cached` leaves the working-tree file in place so no loop home's live config disappears.
- A meta-test asserts `git ls-files` no longer lists `.bmad-loop/policy.toml` and that `.gitignore` covers it.

**Block If:** None identified.

**Never:**
- Do not import `bmad_loop` or add it as a `pyproject.toml`/`pixi.toml` dependency. AD-3's docstring permits `adapters/harness_bmadloop.py` to do so, but nothing in this story's ACs requires runtime introspection of the harness package, and doing so would force a root `pixi.toml`/`pixi.lock` re-solve (a monorepo-wide, unrelated blast radius) for no behavioral gain over a vendored template. Declaring `bmad-loop` as a real dependency is Story 1.9's AC, not this one's.
- Do not wire a CLI subcommand (`cli/init.py`, `marshal init`, etc.) to call `write_policy_toml` -- this story's surface is `adapters/harness_bmadloop.py` plus tests plus `.gitignore` only; Story 1.4/1.7 are the callers.
- Do not render `frozen_surfaces` or `merge_subject_template` into the harness file -- neither has a real `bmad_loop` policy.toml counterpart (confirmed against the installed 0.9.0 schema: no `frozen` key anywhere; `scm.commit_message_template` governs the per-story dev-session commit message under `isolation=worktree`, not the landing merge subject, which `bmad_loop`'s `Engine._merge_message()` hardcodes unconditionally as `"Merge {branch} into {target} (bmad-loop)"` regardless of policy). Both fields stay Marshal-internal (consumed by `core/gate`/`core/identity` in later stories).
- Do not resolve which difficulty class applies to the current story/batch -- `difficulty` is caller-supplied; this story only renders given a resolved value.
- Do not add a new `MRS-*` finding code or touch `core/findings.py`/`core/verdict.py` -- no CLI caller exists yet to convert an I/O failure into a Finding; a plain exception is sufficient until a later story wires a caller.
- Do not read, merge with, or preserve any part of an existing `.bmad-loop/policy.toml` when writing -- every call is a full replace.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full composition | a composed `EffectivePolicy`, `difficulty=None` | all 6 mapped keys reflect `EffectivePolicy`'s values; every other key at template baseline (incl. the hardcoded repo-wide overrides) | none |
| Determinism | `render_policy_toml(effective, difficulty=d)` called twice, identical args | byte-identical string both times | none |
| Tier-batching, full stage set | `difficulty="hard"`, `model_tier_map={"hard": {"dev": "opus", "review": "fable", "triage": "sonnet"}}` | `[adapter.dev].model=="opus"`, `[adapter.review].model=="fable"`, `[adapter.triage].model=="sonnet"` | none |
| Tier-batching, partial stage set | `difficulty="hard"`, `model_tier_map={"hard": {"dev": "opus"}}` | `[adapter.dev].model=="opus"`; `[adapter.review]`/`[adapter.triage]` stay at template baseline | none |
| Unknown difficulty | `difficulty="nonexistent"`, `model_tier_map={}` | every adapter stage at template baseline | none (not an error) |
| Empty verify_commands | `verify_commands=()` | `[verify].commands == []` | none |
| Rendered text validity | any composed `EffectivePolicy` | `tomllib.loads()` parses the output without error | none |
| `write_policy_toml` overwrite | `<loop_home>/.bmad-loop/policy.toml` pre-exists with unrelated content | file is fully replaced; no trace of the prior content remains | none |

</intent-contract>

## Code Map

- `src/pyforge/marshal/adapters/harness_bmadloop.py` -- add `_POLICY_TEMPLATE` (vendored, project-agnostic harness policy template), `render_policy_toml()` (pure), `write_policy_toml()` (I/O, atomic whole-file write); module docstring already declares this the sole harness seam (Story 1.1)
- `tests/unit/test_harness_policy_render.py` -- NEW: every I/O-matrix scenario above, plus atomic-overwrite behavior
- `tests/meta/test_rendered_policy_untracked.py` -- NEW: `git ls-files` excludes `.bmad-loop/policy.toml`; `.gitignore` contains the entry
- `.gitignore` (repo root) -- add `.bmad-loop/policy.toml`
- `.bmad-loop/policy.toml` (repo root, tracked today) -- `git rm --cached` as the final step

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/marshal/adapters/harness_bmadloop.py` -- implement `_POLICY_TEMPLATE`, `render_policy_toml()`, `write_policy_toml()` per the Boundaries above
- [x] `tests/unit/test_harness_policy_render.py` -- NEW: cover the full I/O matrix
- [x] `.gitignore` -- add `.bmad-loop/policy.toml` near the existing `.bmad-loop/` entries
- [x] `tests/meta/test_rendered_policy_untracked.py` -- NEW: untracked + gitignore-covered assertions
- [x] Run the full test suite green, THEN `git rm --cached .bmad-loop/policy.toml` at the repo root as the final change

**Acceptance Criteria:**
- Given a materialized `EffectivePolicy` and a loop home, when the harness adapter renders, then `.bmad-loop/policy.toml` is written whole -- never patched, never merged -- and is byte-identical for identical input
- Given FR-51 tier-batching, when stories are batched by model tier, then each batch's render carries its own `[adapter.dev]`/`[adapter.review]`/`[adapter.triage]` `.model`
- Given the rendered file, when the repository is inspected, then `.bmad-loop/policy.toml` is untracked and a meta-test asserts `git ls-files` does not list it
- Given a repo-wide default (e.g. the standing independent-review trigger), when it changes, then it is expressed in `_POLICY_TEMPLATE` (the tracked canonical source), never by hand-editing a rendered file

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 4: (high 0, medium 2, low 2)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[low]` `[patch]` `harness_bmadloop.py`'s module docstring claimed the 6 hardcoded template overrides were "confirmed by diffing every live loop home's actual policy.toml against the stock defaults" in a way that could be read as covering the whole render, when the diffing only ever verified those 6 literal constants -- the dynamically-sourced seed fields (`gate_mode`, `max_followup_reviews`, etc.) have no such verification and depend entirely on the caller's `EffectivePolicy`. Docstring now scopes the claim to the 6 literals explicitly and states that establishing a real project-policy source is a later story's job.
  - `[low]` `[patch]` Neither `render_policy_toml` nor the module docstring explained why `frozen_surfaces`/`merge_subject_template` (2 of Marshal's 9 composed keys) are never rendered into the harness file -- a reader of just this file had no way to tell "deliberately out of scope" from "forgotten." Added a paragraph naming both fields and why (no real `bmad_loop` counterpart; consumed by `core/gate`/`core/identity` in later stories instead).
  - `[low]` `[patch]` `pyproject.toml`'s dependency-list comment still read "adapters/harness_bmadloop.py stays a docstring-only seam this story (no code resolves or invokes it yet)" -- now false, since this diff adds ~150 lines of real, tested rendering logic to that exact module. Updated to describe the actual state (vendored-template rendering, still no runtime `bmad_loop` dependency, Story 1.9 still owns declaring one).
  - `defer` (medium): no project-policy source anywhere in the repo currently supplies `pyforge-marshal`'s own tuned `gate_mode="none"`/`max_followup_reviews=2` -- the first real caller of `write_policy_toml` will render Marshal's bare `DEFAULT_POLICY` values instead, silently reintroducing a previously-incident-causing default (DW-AD23-3). Not this story's problem (Story 1.10 renders a given `EffectivePolicy`; supplying the project layer is Story 1.4/1.7's job), but recorded so that story doesn't ship the regression by omission.
  - `defer` (medium): `_POLICY_TEMPLATE` is a hand-vendored, unpinned-version snapshot of the installed `bmad_loop` 0.9.0 schema with no drift detector, and root `pixi.toml`'s `bmad-loop = ">=0.9.0"` has no upper bound -- a future harness upgrade with a renamed/changed-default key would go unnoticed. Deliberately out of this story's scope (vendoring was chosen specifically to avoid an `import bmad_loop` dependency and its pixi.lock blast radius); a lightweight version-aware drift check is a reasonable follow-up.
  - `defer` (low): `write_policy_toml`'s unconditional whole-file overwrite will discard harness-native state living in the same file outside Marshal's control (`bmad-loop mux set`'s `[mux].backend`, TUI-resized `[tui]` pane geometry) the moment this path runs against a live loop home more than once. This is a direct consequence of AD-12/AD-35's own "written whole -- never patched, never merged" invariant (epics.md's own Story 1.10 AC text, not a choice introduced by this spec) -- any fix needs an architecture-level carve-out, a product decision outside this story's authority.
  - `defer` (low): untracking only stops the F-1 bleed going forward; a loop-home branch that diverged before this fix landed (the motivating `loop-pyforge-herald` example, 17+/27− of herald-specific policy on the shared tracked file) still needs a manual rebase/re-merge per affected home. Operational rollout concern, not a code defect in this story's surface.
  - `reject` (low): `write_policy_toml`'s `mkdir(parents=True, exist_ok=True)` will create a typo'd/stale `loop_home`'s full directory tree with no complaint -- this exactly mirrors `cli/config.py::materialize()`'s own already-accepted convention (Story 1.3); a caller-side path bug is the caller's concern, not this function's.
  - `reject` (low): suggested pinning the 6 hardcoded template override values against this exact repo's own live `.bmad-loop/policy.toml` in a test -- that file is precisely what this story untracks/gitignores, so a test depending on its continued presence/content would be fragile in CI and a fresh clone, contradicting the story's own artifact-hygiene goal.
  - `reject` (low): an unknown/malformed stage name inside a `model_tier_map` difficulty's stage-model dict is silently dropped by `render_policy_toml`'s tier-batching loop with no diagnostic -- unreachable in practice, since `core/policy.py::compose()`'s `_valid_model_tier_map` already rejects any stage name outside `{dev, review, triage}` before an `EffectivePolicy` can ever be constructed through the canonical path.
  - `reject` (low): the O_EXCL-guarded temp file in `write_policy_toml` has "no pre-unlink," so a same-pid+thread-id leftover from a prior crash would permanently block writes until manual cleanup -- this is the exact, already-reviewed-and-accepted mechanism `cli/config.py::materialize()` uses (Story 1.3's third/fourth review passes settled this tradeoff explicitly); re-litigating it here is not new information.

### 2026-07-30 — Review pass (independent follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 1, low 4)
- defer: 3: (high 0, medium 2, low 1)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` A Marshal-valid composition with `max_dev_attempts=0` or `max_review_cycles=0` (legal per `core/policy.py::_valid_attempt_count`'s `>= 0` floor, composes with zero findings) rendered a policy.toml that bmad_loop 0.9.0 rejects wholesale at load (`PolicyError: limits.max_review_cycles and limits.max_dev_attempts must be >= 1`, its policy.py:697-698 — re-confirmed against the installed package during triage), bricking the loop home's next run; both independent reviewers reproduced it empirically. `render_policy_toml` now refuses at the projection boundary with a plain `ValueError` (per this spec's own no-`MRS-*`-code boundary), plus 3 new tests: both zero cases raise, and `max_followup_reviews=0` still renders (its floor is `>= 0` on both sides — the divergence is exactly those two keys).
  - `[low]` `[patch]` The module docstring and template header claimed `_POLICY_TEMPLATE` covers the 0.9.0 schema's "full key surface"/"every section/key" when it deliberately omits `gates.on_escalation`, the four `[tui]` pane-geometry keys, `[mux].backend`, adapter/stage `usage_grace_s`/`stop_without_result_nudges`/`extra_args`, and dynamic per-plugin sub-tables. Both claims now scoped to every SECTION with the omitted instance-local/reserved keys named (the repo's never-overstate-coverage rule; same class as the first pass's docstring patch).
  - `[low]` `[patch]` The meta-test asserted only the literal `.gitignore` line — a functionally equivalent variant fails it while a later negation pattern elsewhere in the ~750-line file would pass it despite un-ignoring the file. Added `test_git_check_ignore_covers_policy_toml` asserting effective behavior via `git check-ignore -q`; the literal-line test stays (this spec's Always mandates the entry itself). The reviewer's companion point (`_repo_root` raising outside any git checkout) was rejected — these meta-tests subprocess `git` and are meaningless outside a repo.
  - `[low]` `[patch]` `render_policy_toml`'s docstring did not state that seed fields carry the INITIAL composed values, so a mid-run re-render reproduces run-START state rather than the live journal-folded value (AD-26) — precisely the trap for `gate_mode`, the field an operator flips mid-run. One-sentence docstring addition.
  - `[low]` `[patch]` `write_policy_toml` lacked `cli/config.py::materialize`'s explicit caller contract, leaving ambiguous whether it gates error-class/defaults-only compositions itself; the docstring now pins "THE CALLER owns the persist gate" (mirroring materialize), which is also the honest answer to the reviewer's ask for an in-function findings/status gate — that gate belongs to the Story 1.4/1.7 callers per this spec's Never section.
  - `defer` (medium): between this merge and the story that wires a caller, a fresh loop home/clone (or a home whose unmodified tracked copy git deletes on pull) has NO policy.toml at all → bmad-loop stock defaults (`scm.isolation="none"`, `verify.commands=[]`, `trigger="recommended"`, 90-min timeout). A consequence of the epic's own mandated untrack-last sequencing, not of this diff — operational rollout concern; NEW ledger entry appended.
  - `defer` (medium): the untracked file's `max_followup_reviews = 2` was explicitly a REPO-WIDE decision (its own 2026-07-30 comment; five stories across three projects damped by the default of 1), so the existing ledger entry's marshal-project-layer remedy under-scopes the fix — the only viable homes are `DEFAULT_POLICY` or the global custom layer (a template hardcode is dead: render unconditionally overwrites that key). Resolution-shaping nuance recorded as a NEW entry; the existing entry was not modified or re-opened.
  - `defer` (low): the deleted tracked policy.toml's ~120 lines of curated operational commentary (the A4/A6 authoring conventions, the hard-story model-escalation batch procedure, the atlas-gates restore note, the `--frozen` verify rationale) now survive only in git history (`git show 99ba90ea4e:.bmad-loop/policy.toml`) and untracked per-home copies; relocation placement depends on the policy-source design owned by later stories. NEW ledger entry appended.
  - `reject` (low): whole-file overwrite clobbers harness-persisted `[mux].backend`/`[tui]` pane geometry — duplicate of this spec's first-pass ledger entry (the orchestrator owns existing entries; not re-filed).
  - `reject` (low): no drift detector / no round-trip test through `bmad_loop.policy.loads()` for the vendored template — duplicate of the first-pass drift-detector ledger entry; the suggested test would also import `bmad_loop`, which this spec's Never section forbids.
  - `reject` (low): a typo'd/unknown `difficulty` silently renders baseline with no diagnostic — this spec's Always mandates exactly that ("never an error"); settled decision, not new information.
  - `reject` (low): O_EXCL temp file has no pre-unlink and an unactionable collision message, cleanup paths untested — re-litigates the materialize-mirrored mechanism Story 1.3's reviews settled and this spec's first pass already rejected.
  - `reject` (low): no fsync around `os.replace` ("atomic overpromises durability") — parity with the accepted `materialize` pattern; a post-crash partial state is self-healing on the next render, and no caller exists yet.

## Design Notes

**Why a vendored template instead of importing `bmad_loop`.** AD-3's docstring permits `adapters/harness_bmadloop.py` to import the harness package, but this story's own ACs only need a fixed, documented key surface (14 sections, ~26 keys) rendered deterministically -- verified once against the installed `bmad_loop` 0.9.0 source (`policy.py`'s dataclasses + its own `POLICY_TEMPLATE` constant) rather than introspected at runtime. Importing it would make `pyforge-marshal` depend on a package not yet declared anywhere in its manifests, forcing a root `pixi.lock` re-solve whose blast radius (the whole monorepo workspace) is disproportionate to this story's scope. Story 1.9 owns declaring `bmad-loop` as Marshal's real packaged dependency; nothing here blocks that.

**Why `merge_subject_template` renders nowhere.** Investigation of the installed `bmad_loop` 0.9.0 confirmed `Engine._merge_message()` hardcodes the landing-merge subject (`"Merge {branch} into {target} (bmad-loop)"`) unconditionally under `isolation=worktree` -- the mode every current loop home runs. `scm.commit_message_template` only reaches the throwaway per-story squash commit inside the unit branch, never the commit that lands on the target branch. Since Marshal's own merge-subject rendering (Story 1.2's `core/identity.py`) exists to recognize/produce Marshal's own convention independent of the harness, wiring `merge_subject_template` into `commit_message_template` would be a false mapping between two same-shaped-but-different concepts; leaving it unrendered is the honest choice.

**The 6 hardcoded repo-wide template overrides are evidence-based, not guessed.** Confirmed by diffing all 9 live loop homes' actual `.bmad-loop/policy.toml` files against `bmad_loop.policy.POLICY_TEMPLATE`'s stock defaults: `isolation`/`merge_strategy`/`session_timeout_min`/`rollback_on_failure`/the two baseline adapter models are uniformly non-stock across every home today. Reverting any of them silently on first render would be an operational regression (the worktree-per-story workflow this whole factory runs on), not a neutral default choice.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: full suite passes, including the new render tests and the untracked meta-test
- `pixi run -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: `2 kept, 0 broken` (unchanged; no new import surface crosses either contract)
- `git ls-files .bmad-loop/policy.toml` (from repo root, after the final `git rm --cached` step) -- expected: empty output

## Auto Run Result

**Pass 2 (2026-07-30, independent follow-up review on a `done` spec — orchestrator-triggered).**

**Summary of implemented change:** This pass ran a fresh two-reviewer adversarial/edge-case review of the full Story 1.10 diff (baseline `99ba90ea4e` → `1c0b2cf3da`) and applied 5 patches on top, landing as `c45e135bbd`. The substantive fix: `render_policy_toml` now refuses (`ValueError`) a composition whose `max_dev_attempts` or `max_review_cycles` is 0 — legal in Marshal's own validator (`>= 0`) but rejected wholesale by bmad_loop 0.9.0's policy loader (`must be >= 1`, verified against the installed package's `policy.py:697-698`); without the guard, a Marshal-valid composition would render a file that bricks the loop home's next run. `max_followup_reviews=0` remains renderable (floor `>= 0` on both sides).

**Files changed this pass:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — attempt-count floor guard in `render_policy_toml` (+`Raises` doc); template-coverage claims scoped to what is actually vendored (omitted instance-local/reserved keys named); seed-view-vs-journal-fold re-render note; materialize-style caller-owns-the-persist-gate sentence on `write_policy_toml`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py` — 3 new tests for the floor guard (both zero cases raise; `max_followup_reviews=0` renders).
- `src/shared/packages/pyforge-marshal/tests/meta/test_rendered_policy_untracked.py` — new `git check-ignore -q` behavioral assertion beside the literal-line check.

**Review findings breakdown:** 13 deduplicated findings → 5 patched (1 medium, 4 low), 3 deferred as NEW ledger entries (2 medium: the no-policy-file transition window until Story 1.4/1.7 wires a caller; the repo-wide scope of `max_followup_reviews=2` making a marshal-only project-layer fix insufficient — 1 low: the deleted file's curated operational commentary now living only in git history), 5 rejected (2 as duplicates of this spec's first-pass ledger entries — mux/TUI clobber, template drift detector; 3 as re-litigations of spec-mandated or Story-1.3-settled decisions). No intent_gap, no bad_spec. Per the orchestrator's instruction, only NEW ledger entries were appended; no existing entry was modified, re-opened, or rewritten.

**Follow-up review recommendation:** false — the one behavioral patch is an ~10-line, fully-tested guard whose premise was verified three ways (both independent reviewers empirically, plus direct inspection of the installed bmad_loop source during triage); the other four patches are docstring/test hardenings.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 418 passed (414 pre-pass + 4 new). `lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` → 2 kept, 0 broken. `git ls-files .bmad-loop/policy.toml` → empty. Working tree clean after commit `c45e135bbd`.

**Residual risks:** the three deferred items (transition-window stock-defaults exposure until a caller is wired; where the repo-wide `max_followup_reviews=2` value gets a durable home; relocation of the deleted file's operational commentary) are real but owned by the orchestrator's ledger and later stories (1.4/1.7), per this spec's own scope boundaries. The already-ledgered mux/TUI whole-file-overwrite carve-out remains an architecture-level product decision.

